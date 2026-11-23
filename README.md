# skillcrate

Agent plugins for Claude Code, OpenAI Codex and Gemini CLI. Each plugin is one reusable skill packaged for every platform.

## Plugins

<!-- plugins:table:start -->
| Plugin | Version | Platforms | Permissions |
|---|---|---|---|
| [`iam-policy-diff-reviewer`](#iam-policy-diff-reviewer) | 0.2.0 | Claude Code, Codex, Gemini CLI, portable | read-only |
<!-- plugins:table:end -->

## Install

Each plugin below lists its install steps. For everything except Claude Code from GitHub, clone the repo first:

```bash
git clone https://github.com/mohana-gutta/skillcrate.git && cd skillcrate
```

<!-- plugin:iam-policy-diff-reviewer:start -->
## iam-policy-diff-reviewer

Offline, credential-free review of AWS IAM policy changes, from two policy JSONs or directly from a terraform plan, reporting newly granted access for human review.

### Install

**Claude Code**
```
/plugin marketplace add mohana-gutta/skillcrate
/plugin install iam-policy-diff-reviewer@skillcrate
```

**Gemini CLI** (from a clone of this repo)
```bash
gemini extensions link plugins/gemini/iam-policy-diff-reviewer
```

**Codex** (from a clone; use `.agents/skills/` in a repo instead of `~/` for one repo only)
```bash
mkdir -p ~/.agents/skills && cp -r plugins/codex/iam-policy-diff-reviewer/.agents/skills/iam-policy-diff-reviewer ~/.agents/skills/
```

**Any other agent**: copy `plugins/portable/iam-policy-diff-reviewer` into its skills directory.

### Usage

#### Two ways to use it

1. **Two policy documents.** Ask your agent: *"Use iam-policy-diff-reviewer to compare old-policy.json and new-policy.json."*
2. **A Terraform plan.** Export the plan, then ask: *"Use iam-policy-diff-reviewer to review the IAM changes in plan.json."*
   ```bash
   terraform plan -out=tfplan && terraform show -json tfplan > plan.json
   ```
   It reviews every changed `aws_iam_policy`, `aws_iam_role_policy`, `aws_iam_user_policy` and `aws_iam_group_policy`
   and reports findings per resource. Unlike AWS `check-no-new-access`, it needs no AWS access and no second document.

#### Without an agent

Run the script directly (Python 3, standard library only):

```bash
python plugins/portable/iam-policy-diff-reviewer/scripts/iam_diff.py old.json new.json
python plugins/portable/iam-policy-diff-reviewer/scripts/iam_diff.py --terraform-plan plan.json
```

Exit code `0` = no added grants detected, `1` = review required, `2` = invalid input. Try it on the bundled examples in
`plugins/portable/iam-policy-diff-reviewer/examples/`.

#### Limits

It compares policy statements only. It does not evaluate SCPs, permission boundaries, session policies or
resource policies, and it errs toward flagging, so treat `NO_ADDED_GRANTS_DETECTED` as "nothing found by this check", never
as proof a change is safe. For an authoritative result, also use IAM Access Analyzer `check-no-new-access`.
<!-- plugin:iam-policy-diff-reviewer:end -->

## Downloads

Each release on the [Releases page](https://github.com/mohana-gutta/skillcrate/releases) attaches one zip per platform,
`SHA256SUMS`, a CycloneDX SBOM and Sigstore attestation bundles, and is signed. Verify a download with the GitHub CLI:

```bash
gh attestation verify <plugin>-<version>-claude.zip -R mohana-gutta/skillcrate
sha256sum -c SHA256SUMS
```

A valid attestation shows which workflow, repository and commit built the file. It does not mean the plugin is safe. Then follow the install steps above using the unzipped folder.

Licensed under the [MIT License](LICENSE).
