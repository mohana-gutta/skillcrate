---
name: iam-policy-diff-reviewer
description: Diff two AWS IAM policy JSON documents offline and report newly granted access or removed Deny statements for human review. Use when reviewing an IAM policy change before merge or apply.
---

# IAM Policy Diff Reviewer

Compares an OLD and a NEW IAM policy document and lists what the change adds. It runs a local script: no AWS
credentials, no network, nothing is executed against your account.

## When invoked

1. Get the change as either two JSON policy documents (old, new), or a Terraform plan: `terraform plan -out=tfplan`
   then `terraform show -json tfplan > plan.json`. For other formats (CloudFormation, a text diff) extract each
   side's policy JSON first; do not guess missing statements.
2. Run `python <skill_dir>/scripts/iam_diff.py OLD.json NEW.json`, or for a plan
   `python <skill_dir>/scripts/iam_diff.py --terraform-plan plan.json` (`<skill_dir>` is this skill's folder).
   Plan mode reviews every IAM policy resource that changes (`aws_iam_policy`, `aws_iam_role_policy`,
   `aws_iam_user_policy`, `aws_iam_group_policy`) and reports findings per resource address. A
   `policy_unknown_until_apply` finding means the policy is computed at apply time: say it cannot be reviewed yet.
3. Read the JSON result:
   - exit 0 / `NO_ADDED_GRANTS_DETECTED`: no Allow in NEW lacks a covering Allow in OLD, and no Deny was lost.
   - exit 1 / `REVIEW_REQUIRED`: each finding is a statement the tool could not prove already granted
     (`new_or_broader_allow`) or a Deny that was removed or weakened (`deny_removed_or_weakened`).
   - exit 2: invalid input; report the error, do not guess.
4. Explain each finding in plain language (in plan mode, name the Terraform resource address). Use the finding's `uncovered` list for exactly which action/resource
   pairs are new (do not call other actions in the same statement new); say why it matters, and what
   narrower statement would achieve the same goal. `severity: high` marks privilege-escalation-prone actions
   (e.g. `iam:PassRole`), wildcard `Action`, and NotAction/NotResource/NotPrincipal statements.

## Rules

- Never say a policy "is safe" or "has no new access". Say what was checked: the verdict covers statement-level
  comparison only. SCPs, permission boundaries, session policies, resource policies and policy interactions are NOT evaluated.
- The tool errs toward `REVIEW_REQUIRED`: a new statement split across several old ones, or an unprovable wildcard,
  is flagged. Say so; do not dismiss a finding because it looks like a false positive without explaining why.
- Never run anything against AWS, and never ask for credentials. Do not modify the policy files.
- If the user wants authoritative results, point to AWS IAM Access Analyzer `check-no-new-access` as the complement.

See `references/limitations.md` and `examples/`.
