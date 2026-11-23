#!/usr/bin/env python3
"""Static auditor for GitHub Actions cache keys. Read-only, stdlib only."""
import argparse
import difflib
import json
import re
import sys
from itertools import islice
from pathlib import Path

SCHEMA_VERSION = "1"
MAX_FILE = 1 << 20
MAX_FILES = 200
SEV = {"possible": 0, "warning": 1, "error": 2}
EXPR = re.compile(r"\$\{\{(.*?)\}\}")
CTRL = re.compile(r"[\x00-\x1f\x7f]")
BROAD = {"**", "*", "**/*", "**/**", "*/**"}
LOCKS = [  # (path hints, candidate lock files)
    (("~/.npm", "node_modules", ".npm"), ("package-lock.json",)),
    (("~/.cargo", "target"), ("Cargo.lock",)),
    (("pip",), ("requirements.txt",)),
    (("go/pkg/mod",), ("go.sum",)),
    (("~/.m2",), ("pom.xml",)),
]
SKIPPED = [
    {"rule": "CK005", "reason": "live cache/quota checks not implemented in this version"},
    {"rule": "CK007", "reason": "live cache usage checks not implemented in this version"},
    {"rule": "ESTIMATE", "reason": "wasted-minutes estimate not implemented in this version"},
]


def clean(s, n=200):
    return CTRL.sub(" ", str(s))[:n]


def indent(line):
    return len(line) - len(line.lstrip(" "))


def parse_scalar(val):
    val = val.strip()
    if val[:1] in ("'", '"'):
        end = val.rfind(val[0])
        if end > 0:
            return val[1:end], val[0]
    return re.split(r"\s+#", val)[0].strip(), None


def parse_with(lines, a, b):
    w = None
    for i in range(a, b):
        if re.match(r"^\s*with:\s*$", lines[i]):
            w = i
            break
    if w is None:
        return {}
    wi = indent(lines[w])
    fields, ci, i = {}, None, w + 1
    while i < b:
        l = lines[i]
        if not l.strip() or l.lstrip().startswith("#"):
            i += 1
            continue
        ind = indent(l)
        if ind <= wi:
            break
        if ci is None:
            ci = ind
        if ind == ci:
            m = re.match(r"^\s*([\w-]+):\s*(.*)$", l)
            if m:
                name, val = m.group(1), m.group(2).strip()
                if val and val[0] in "|>":
                    j, vals = i + 1, []
                    while j < b and (not lines[j].strip() or indent(lines[j]) > ci):
                        if lines[j].strip():
                            vals.append((j + 1, lines[j].strip(), None))
                        j += 1
                    fields[name] = {"line": i + 1, "values": vals, "block": True}
                    i = j
                    continue
                text, q = parse_scalar(val)
                fields[name] = {"line": i + 1, "values": [(i + 1, text, q)], "block": False}
        i += 1
    return fields


def find_cache_steps(lines):
    pat = re.compile(r"^(\s*)(-\s+)?uses:\s*actions/cache(?:/restore|/save)?@")
    for i, l in enumerate(lines):
        m = pat.match(l)
        if not m:
            continue
        if m.group(2):
            dash = i
        else:
            dash = None
            for j in range(i - 1, -1, -1):
                if re.match(r"^\s*-\s", lines[j]) and indent(lines[j]) < indent(l):
                    dash = j
                    break
            if dash is None:
                continue
        di = indent(lines[dash])
        end = dash + 1
        while end < len(lines) and (not lines[end].strip() or indent(lines[end]) > di):
            end += 1
        yield dash, end


def job_of(lines, idx):
    for j in range(idx, -1, -1):
        m = re.match(r"^  ([\w.-]+):\s*$", lines[j])
        if m:
            return m.group(1)
    return None


def step_name(lines, a, b):
    for i in range(a, b):
        m = re.match(r"^\s*(?:-\s+)?name:\s*(.*)$", lines[i])
        if m:
            return parse_scalar(m.group(1))[0]
    return None


def glob_matches(root, pat):
    """True/False, None if unknown, 'escape' if pattern leaves the repo."""
    pat = pat.strip()
    if not pat or pat.startswith("!"):
        return None
    if pat.startswith("/") or ".." in Path(pat).parts or re.match(r"^[A-Za-z]:", pat):
        return "escape"
    try:
        for p in islice(root.glob(pat), 10000):
            if not p.is_symlink() and p.is_file():
                return True
        return False
    except (ValueError, NotImplementedError, OSError):
        return None


def hash_args(expr_text):
    """Return list of literal glob lists, one per hashFiles call; None if non-literal."""
    calls = []
    for m in re.finditer(r"hashFiles\((.*?)\)", expr_text):
        inner = m.group(1)
        args = [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", inner)]
        rest = re.sub(r"'[^']*'|\"[^\"]*\"|[,\s]", "", inner)
        calls.append(args if not rest else None)
    return calls


def make_patch(rel, lines, key):
    line_no, text, q = key["values"][0]
    raw = lines[line_no - 1]
    return raw, line_no, q


def lock_for(root, path_text):
    low = path_text.lower()
    for hints, files in LOCKS:
        if any(h in low for h in hints):
            for f in files:
                if (root / f).is_file() and not (root / f).is_symlink():
                    return f
    return None


def finding(rule, sev, wf, job, step, span, expl, evidence, patch=None):
    d = {"rule_id": rule, "severity": sev, "workflow": wf, "job": clean(job) if job else None,
         "step": clean(step) if step else None, "lines": span,
         "evidence": [{k: clean(v) if isinstance(v, str) else v for k, v in e.items()} for e in evidence],
         "explanation": expl}
    if patch:
        d["patch"] = patch
    return d


def audit_text(root, rel, text, want_patches=False):
    out = []
    lines = text.splitlines()
    has_matrix = bool(re.search(r"^\s*matrix:", text, re.M))
    for a, b in find_cache_steps(lines):
        f = parse_with(lines, a, b)
        key = f.get("key")
        if not key or not key["values"]:
            continue
        job, name = job_of(lines, a), step_name(lines, a, b)
        span = [a + 1, b]
        ktext = " ".join(v[1] for v in key["values"])
        ev_key = {"kind": "key", "key": ktext, "line": key["line"]}
        exprs = EXPR.findall(ktext)
        has_hash = any("hashFiles" in e for e in exprs)
        has_gh = any("github." in e for e in exprs)
        path_text = " ".join(v[1] for v in f.get("path", {"values": []})["values"])
        # CK001
        if not has_hash and not has_gh:
            patch, expl = None, ("The key has no hashFiles() and no github.* value, so it is constant: "
                                 "once saved the cache is never refreshed.")
            lock = lock_for(root, path_text)
            if lock and want_patches and not key["block"]:
                raw, ln, q = make_patch(rel, lines, key)
                if " #" not in raw:
                    add = "-${{ hashFiles('%s') }}" % lock
                    new = raw.rstrip()[:-1] + add + q if q and raw.rstrip().endswith(q) else (
                        raw.rstrip() + add if not q else None)
                    if new:
                        # diff the whole file so the hunk header carries the real line number and context
                        edited = list(lines)
                        edited[ln - 1] = new
                        patch = "\n".join(difflib.unified_diff(
                            lines, edited, "a/" + rel, "b/" + rel, lineterm="", n=2))
            sev = "warning" if patch is not None or lock or not exprs else "warning"
            if not lock:
                expl += " No lock file could be matched to the cached path, so no patch is suggested."
            out.append(finding("CK001", sev, rel, job, name, span, expl,
                               [ev_key, {"kind": "path", "ref": path_text}], patch))
        # CK002 / CK004
        for call in hash_args(" ".join(exprs)):
            if call is None:
                continue
            for g in call:
                if g.strip() in BROAD:
                    out.append(finding("CK004", "possible", rel, job, name, span,
                                       "hashFiles() over a very broad glob: any file change alters the key.",
                                       [ev_key, {"kind": "glob", "ref": g}]))
                res = glob_matches(root, g)
                if res == "escape":
                    out.append(finding("CK002", "possible", rel, job, name, span,
                                       "hashFiles() glob points outside the repository; it was not evaluated.",
                                       [ev_key, {"kind": "glob", "ref": g}]))
                elif res is False:
                    out.append(finding("CK002", "error", rel, job, name, span,
                                       "hashFiles() glob matches no file in the repo, so the hash never changes.",
                                       [ev_key, {"kind": "glob", "ref": g, "matched": 0}]))
        # CK003
        if has_matrix and not any(("runner.os" in e or "matrix." in e) for e in exprs):
            out.append(finding("CK003", "possible", rel, job, name, span,
                               "Workflow uses a matrix but the key has no runner.os or matrix.* value; "
                               "matrix legs may collide.", [ev_key]))
        # CK006
        rk = f.get("restore-keys")
        if rk:
            lit_key = ktext.split("${{")[0]
            for _, v, _q in rk["values"]:
                lit = v.split("${{")[0]
                if not (lit_key.startswith(lit) or lit.startswith(lit_key)):
                    out.append(finding("CK006", "warning", rel, job, name, span,
                                       "restore-keys entry shares no prefix with the key, so it can never match.",
                                       [ev_key, {"kind": "restore-key", "ref": v}]))
    return out


def audit(root, want_patches=False):
    root = Path(root).resolve()
    wdir = root / ".github" / "workflows"
    if not wdir.is_dir():
        raise FileNotFoundError("no .github/workflows directory under %s" % clean(root))
    files = sorted(p for p in wdir.iterdir() if p.suffix in (".yml", ".yaml"))
    findings, skipped_files, scanned = [], [], 0
    for p in files[:MAX_FILES]:
        rel = ".github/workflows/" + p.name
        if p.is_symlink() or not p.is_file():
            skipped_files.append({"file": rel, "reason": "symlink or not a regular file"})
            continue
        if p.stat().st_size > MAX_FILE:
            skipped_files.append({"file": rel, "reason": "file larger than 1 MiB"})
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        scanned += 1
        findings.extend(audit_text(root, rel, text, want_patches))
    if len(files) > MAX_FILES:
        skipped_files.append({"file": "*", "reason": "more than %d workflow files" % MAX_FILES})
    findings.sort(key=lambda d: (d["workflow"], d["lines"][0], d["rule_id"]))
    return {"schema_version": SCHEMA_VERSION,
            "summary": {"workflows_scanned": scanned, "findings": len(findings),
                        "skipped_rules": SKIPPED, "skipped_files": skipped_files},
            "findings": findings}


def render_text(report):
    lines = []
    for f in report["findings"]:
        lines.append("[%s] %s %s:%d (%s / %s) %s" % (
            f["severity"], f["rule_id"], f["workflow"], f["lines"][0], f["job"], f["step"], f["explanation"]))
        for e in f["evidence"]:
            lines.append("    evidence: " + json.dumps(e))
        if f.get("patch"):
            lines.append("    suggested patch:")
            lines.extend("      " + x for x in f["patch"].splitlines())
    s = report["summary"]
    lines.append("%d finding(s) in %d workflow(s). Not checked: %s" % (
        s["findings"], s["workflows_scanned"], ", ".join(r["rule"] for r in s["skipped_rules"])))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit GitHub Actions cache keys (offline, read-only).")
    ap.add_argument("--path", default=".")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--patches", action="store_true")
    ap.add_argument("--fail-on", choices=list(SEV))
    args = ap.parse_args(argv)
    try:
        report = audit(args.path, args.patches)
    except (OSError, ValueError) as e:
        print("error: %s" % clean(e), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2) if args.format == "json" else render_text(report))
    if args.fail_on and any(SEV[f["severity"]] >= SEV[args.fail_on] for f in report["findings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
