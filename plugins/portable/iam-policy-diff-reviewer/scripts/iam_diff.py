#!/usr/bin/env python3
"""Conservative diff of two AWS IAM policy documents (old -> new).

Reports Allow grants in NEW that it cannot prove were already granted by OLD, and Deny statements that were removed
or weakened. Offline: reads two local files, no network, no AWS credentials, executes nothing.

Exit codes: 0 no added grants detected, 1 review required, 2 invalid input.
Limits (by design, it errs toward "review"): statement-level only. It does not evaluate SCPs, permission
boundaries, session policies, resource-based policy interplay, or Condition value semantics beyond exact match.
"""
import argparse
import json
import sys
from pathlib import Path

MAX_BYTES = 1_000_000
MAX_PAIRS = 50
# shortcut: small hand-picked list of privilege-escalation-prone actions; extend from a maintained source later.
SENSITIVE = {"iam:passrole", "iam:createaccesskey", "iam:attachuserpolicy", "iam:attachrolepolicy",
             "iam:putuserpolicy", "iam:putrolepolicy", "iam:createpolicyversion", "iam:updateassumerolepolicy",
             "sts:assumerole", "lambda:updatefunctioncode", "kms:decrypt"}


class PolicyError(ValueError):
    pass


def _list(v):
    return v if isinstance(v, list) else [v]


def _read_json(path: str):
    p = Path(path)
    if p.stat().st_size > MAX_BYTES:
        raise PolicyError(f"{path}: larger than {MAX_BYTES} bytes")
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise PolicyError(f"{path}: invalid JSON: {e}") from e


def load(path: str) -> list[dict]:
    return parse(_read_json(path), path)


def parse(doc, path: str) -> list[dict]:
    stmts = doc.get("Statement") if isinstance(doc, dict) else None
    if stmts is None:
        raise PolicyError(f"{path}: no Statement element")
    out = []
    for i, s in enumerate(_list(stmts)):
        if not isinstance(s, dict) or s.get("Effect") not in ("Allow", "Deny"):
            raise PolicyError(f"{path}: statement {i} needs Effect Allow or Deny")
        if not any(k in s for k in ("Action", "NotAction")):
            raise PolicyError(f"{path}: statement {i} has no Action/NotAction")
        out.append({"i": i, "effect": s["Effect"], "raw": s,
                    "action": [str(x) for x in _list(s["Action"])] if "Action" in s else None,
                    "resource": [str(x) for x in _list(s["Resource"])] if "Resource" in s else None,
                    "principal": _principals(s.get("Principal")),
                    "cond": _cond(s.get("Condition")),
                    "negated": [k for k in ("NotAction", "NotResource", "NotPrincipal") if k in s]})
    return out


def _principals(p):
    if p is None:
        return None
    if p == "*":
        return ["*"]
    if isinstance(p, dict):
        return sorted(f"{k}:{v}" for k, vs in p.items() for v in _list(vs))
    raise PolicyError(f"unsupported Principal: {p!r}")


def _cond(c):
    if not c:
        return {}
    return {(op, key): frozenset(map(str, _list(v))) for op, kv in c.items() for key, v in kv.items()}


def _wild(s: str) -> bool:
    return "*" in s or "?" in s


def covers(broad: str, narrow: str, ci: bool) -> bool:
    """True only if every string matched by `narrow` is provably matched by `broad` (IAM * and ? wildcards)."""
    if ci:
        broad, narrow = broad.lower(), narrow.lower()
    if broad == "*" or broad == narrow:
        return True
    if not _wild(narrow):
        return _match(broad, narrow)
    # narrow has wildcards: provable only for a single trailing-* prefix in broad, e.g. s3:* covers s3:Get*
    return broad.endswith("*") and not _wild(broad[:-1]) and narrow.startswith(broad[:-1])


def _match(pat: str, s: str) -> bool:
    if not pat:
        return not s
    if pat[0] == "*":
        return any(_match(pat[1:], s[k:]) for k in range(len(s) + 1))
    return bool(s) and (pat[0] == "?" or pat[0] == s[0]) and _match(pat[1:], s[1:])


def _all_covered(new: list[str] | None, old: list[str] | None, ci: bool) -> bool:
    if new is None or old is None:
        return new == old
    return all(any(covers(b, n, ci) for b in old) for n in new)


def _cond_not_broader(old_c: dict, new_c: dict) -> bool:
    """New is at least as restrictive when it keeps every old condition with identical values (extra ones only narrow)."""
    return all(new_c.get(k) == v for k, v in old_c.items())


def _pair_covered(new: dict, action: str, resource, olds: list[dict]) -> bool:
    for o in olds:
        if o["effect"] != "Allow" or o["negated"]:
            continue
        if (_all_covered([action], o["action"], True) and _all_covered(None if resource is None else [resource], o["resource"], False)
                and _all_covered(new["principal"], o["principal"], False) and _cond_not_broader(o["cond"], new["cond"])):
            return True
    return False


def _uncovered(new: dict, olds: list[dict]) -> list[dict]:
    """(action, resource) pairs of a new Allow that no single old Allow provably covers. Negated forms: unprovable."""
    if new["negated"]:
        return [{"action": "NotAction/NotResource/NotPrincipal statement", "resource": None}]
    pairs = [(a, r) for a in new["action"] for r in (new["resource"] or [None])]
    return [{"action": a, "resource": r} for a, r in pairs if not _pair_covered(new, a, r, olds)]


def _deny_still_present(old: dict, news: list[dict]) -> bool:
    """An old Deny is preserved if some new Deny is at least as broad and no less conditional."""
    if old["negated"]:
        return any(n["raw"] == old["raw"] for n in news if n["effect"] == "Deny")
    for n in news:
        if n["effect"] != "Deny" or n["negated"]:
            continue
        if (_all_covered(old["action"], n["action"], True) and _all_covered(old["resource"], n["resource"], False)
                and _all_covered(old["principal"], n["principal"], False) and _cond_not_broader(n["cond"], old["cond"])):
            return True
    return False


def diff(old: list[dict], new: list[dict]) -> list[dict]:
    findings = []
    for s in new:
        if s["effect"] != "Allow":
            continue
        missing = _uncovered(s, old)
        if not missing:
            continue
        actions = [m["action"].lower() for m in missing]
        sensitive = any(a in SENSITIVE or a in ("*", "*:*", "iam:*") for a in actions)
        reason = ("uses NotAction/NotResource/NotPrincipal, which this tool cannot reason about" if s["negated"]
                  else "grants access (see `uncovered`) not provably covered by an Allow in the old policy")
        findings.append({"severity": "high" if sensitive or s["negated"] else "medium", "type": "new_or_broader_allow",
                         "statement_index": s["i"], "detail": reason, "uncovered": missing[:MAX_PAIRS],
                         "uncovered_total": len(missing), "statement": s["raw"]})
    for s in old:
        if s["effect"] == "Deny" and not _deny_still_present(s, new):
            findings.append({"severity": "high", "type": "deny_removed_or_weakened", "statement_index": s["i"],
                             "detail": "a Deny in the old policy has no equal-or-broader Deny in the new policy",
                             "statement": s["raw"]})
    return findings


# shortcut: only these resource types (they all carry the policy JSON in `policy`); managed-policy attachments and
# aws_iam_policy_document data sources are covered because Terraform renders them into these resources.
PLAN_TYPES = {"aws_iam_policy", "aws_iam_role_policy", "aws_iam_user_policy", "aws_iam_group_policy"}


def plan_review(path: str) -> list[dict]:
    """Per-resource review of IAM policy changes in `terraform show -json <planfile>` output."""
    plan = _read_json(path)
    if not isinstance(plan, dict) or "resource_changes" not in plan:
        raise PolicyError(f"{path}: not a terraform plan JSON (no resource_changes)")
    out = []
    for rc in plan["resource_changes"]:
        ch = rc.get("change") or {}
        acts = ch.get("actions") or []
        if rc.get("type") not in PLAN_TYPES or acts in (["no-op"], ["read"]):
            continue
        addr = rc.get("address", rc.get("type"))
        try:
            old = parse(json.loads(ch["before"]["policy"]), addr) if (ch.get("before") or {}).get("policy") else []
            if (ch.get("after_unknown") or {}).get("policy"):
                found = [{"severity": "high", "type": "policy_unknown_until_apply", "statement_index": None,
                          "detail": "the new policy is computed at apply time, so it cannot be reviewed from the plan"}]
            elif acts == ["delete"] or ch.get("after") is None:
                found = diff(old, [])  # deleting a policy removes Allows (fine) and any Denies (flagged)
            else:
                found = diff(old, parse(json.loads(ch["after"]["policy"]), addr))
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise PolicyError(f"{addr}: unreadable policy in plan: {e}") from e
        out.append({"address": addr, "actions": acts, "findings": found})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("old", nargs="?")
    ap.add_argument("new", nargs="?")
    ap.add_argument("--terraform-plan", metavar="PLAN_JSON", help="review IAM policy changes in `terraform show -json` output")
    a = ap.parse_args(argv)
    scope = ("statement-level comparison only; SCPs, permission boundaries, session policies and "
             "cross-policy effects are NOT evaluated")
    try:
        if a.terraform_plan:
            if a.old or a.new:
                ap.error("use either OLD NEW or --terraform-plan, not both")
            resources = plan_review(a.terraform_plan)
            bad = any(r["findings"] for r in resources)
            report = {"verdict": "REVIEW_REQUIRED" if bad else "NO_ADDED_GRANTS_DETECTED", "resources": resources,
                      "iam_policy_resources_in_plan": len(resources), "scope": scope}
        else:
            if not (a.old and a.new):
                ap.error("provide OLD NEW, or --terraform-plan PLAN_JSON")
            findings = diff(load(a.old), load(a.new))
            bad = bool(findings)
            report = {"verdict": "REVIEW_REQUIRED" if bad else "NO_ADDED_GRANTS_DETECTED", "findings": findings, "scope": scope}
    except (PolicyError, OSError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
