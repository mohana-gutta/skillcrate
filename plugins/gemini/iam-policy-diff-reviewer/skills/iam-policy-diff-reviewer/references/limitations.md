# What the script does and does not prove

Compared per statement: Effect, Action (case-insensitive), Resource, Principal, Condition.

Each (action, resource) pair of a new Allow is "covered" only if ONE old Allow covers that action and resource, and
the whole principal list, by its patterns and keeps all of its Condition entries with identical values (extra conditions in the new statement only narrow it).
Pattern coverage: `*` covers everything; a literal is matched against the old pattern using IAM `*`/`?` wildcards;
a wildcard pattern is covered only by `*`, an identical pattern, or a single trailing-`*` prefix of it.

Always flagged (cannot be reasoned about): NotAction, NotResource, NotPrincipal in a new Allow.
Deny: an old Deny must still be matched by an equal-or-broader new Deny with equal-or-fewer conditions.

Findings list the exact uncovered (action, resource) pairs in `uncovered` (first 50; `uncovered_total` is the count).
Known false positives: a single pair that only several old statements together cover (e.g. two overlapping wildcards).
Known false negatives (NOT evaluated): SCPs, permission boundaries, session policies, resource-based policies,
Condition operator semantics beyond exact match, policy variables, service-linked behavior.

Terraform plan mode (novel vs. AWS `check-no-new-access`, which needs two policy documents and AWS API access):
reads `resource_changes` of `terraform show -json`, compares `change.before.policy` with `change.after.policy` for
`aws_iam_policy`, `aws_iam_role_policy`, `aws_iam_user_policy` and `aws_iam_group_policy`. A create is compared to an
empty policy; a delete only reports lost Denies; computed policies are flagged. Not covered: managed policy attachments,
CloudFormation, `aws_iam_role.assume_role_policy`, policies in modules that the plan does not expand (plan JSON
already expands modules), and any resource type not listed.

Sensitive-action list is a short hand-picked set, not exhaustive.
