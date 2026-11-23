# iam-policy-diff-reviewer (codex)

Offline, credential-free review of AWS IAM policy changes, from two policy JSONs or directly from a terraform plan, reporting newly granted access for human review.

## Install

Copy `.agents/skills/iam-policy-diff-reviewer` into your repo's `.agents/skills/` or into `~/.agents/skills/`.
Codex only discovers skills there, not from this package folder unless you start Codex inside it.

