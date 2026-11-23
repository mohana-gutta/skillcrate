# skillcrate

Agent plugins for Claude Code, OpenAI Codex and Gemini CLI. Each plugin is one reusable skill packaged for every platform.

Docs: see the [wiki pages](wiki/Home.md) for the catalog, architecture, release verification and contributing guide.

## Plugins

<!-- plugins:table:start -->
| Plugin | Version | Platforms | Permissions |
|---|---|---|---|
| [`iam-policy-diff-reviewer`](#iam-policy-diff-reviewer) | 0.2.0 | Claude Code, Codex, Gemini CLI, portable | read-only |
| [`actions-cache-key-auditor`](#actions-cache-key-auditor) | 0.1.1 | Claude Code, Codex, Gemini CLI, portable | read-only |
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

<!-- plugin:actions-cache-key-auditor:start -->
## actions-cache-key-auditor

Statically audits GitHub Actions workflows for actions/cache keys that never refresh or never hit, with cited evidence and minimal line-level patch suggestions.

### Install

**Claude Code**
```
/plugin marketplace add mohana-gutta/skillcrate
/plugin install actions-cache-key-auditor@skillcrate
```

**Gemini CLI** (from a clone of this repo)
```bash
gemini extensions link plugins/gemini/actions-cache-key-auditor
```

**Codex** (from a clone; use `.agents/skills/` in a repo instead of `~/` for one repo only)
```bash
mkdir -p ~/.agents/skills && cp -r plugins/codex/actions-cache-key-auditor/.agents/skills/actions-cache-key-auditor ~/.agents/skills/
```

**Any other agent**: copy `plugins/portable/actions-cache-key-auditor` into its skills directory.

### Usage

# Usage

## With an agent

Example prompts:

- "My GitHub Actions cache never hits. Audit this repo's workflows."
- "Run the cache key auditor and show me patches for the errors."

The agent runs the script, explains the findings with evidence, and applies a patch only after you approve.

## Direct commands

```
python3 scripts/cache_audit.py --path . 
python3 scripts/cache_audit.py --path . --format json --patches
python3 scripts/cache_audit.py --path . --fail-on warning   # for CI, exit 1 on warning or error
```

Try the bundled example:

```
python3 scripts/cache_audit.py --path examples/repo --patches
```

## Options

| Flag | Meaning |
|---|---|
| `--path DIR` | Repository root (default `.`) |
| `--format text\|json` | Output format (default text). JSON has `schema_version: "1"` |
| `--patches` | Include suggested unified diffs where one can be determined safely |
| `--fail-on possible\|warning\|error` | Exit 1 when a finding at or above that severity exists |

## Limits

- Static and offline only. Needs Python 3.9+ and no packages. It uses no network and never writes files.
- Workflows are read with a line-based scanner, not a full YAML or expression evaluator. Unusual layouts (anchors, flow-style `with: {...}`, keys built entirely from expressions) are skipped or reported as `possible`. Expect some misses.
- Patches are only produced for CK001 when the ecosystem is recognised from `path` and a matching lock file exists in the repo root.
- Limits: workflow files over 1 MiB are skipped, at most 200 workflow files are read, and symlinks are not followed.
- Not implemented: live GitHub API checks (cache quota, stale entries) and wasted-minutes estimates.
<!-- plugin:actions-cache-key-auditor:end -->

## Persona skills library (SDLC roles with industry overlays)

A separate set of role skills for AI agents: product manager, solution architect, data engineer, SRE, security engineer, controller, revenue accountant, sales operations and 27 more, each producing named deliverables
(PRD, architecture decisions, threat model, test plan, SLOs, ...). Retail Media, Healthcare and Insurance have 11 sector overlays each, E-commerce and Banking 10, Manufacturing 9 and SaaS 12, 30 sector profiles, 11 niche technology and domain specialty skills (Snowflake, Kafka, dbt, ASC 606, FHIR, ISO 20022, ...), month-end close and revenue-to-cash workflows, with domain-specific steps and checks
(for example ad-event deduplication and ROAS reconciliation, or HL7/FHIR interfaces and PHI audit trails). It lives under `skills/` in a clone of this repo and is not part of the plugin table above.

```bash
python scripts/recommend_skills.py --sector healthcare --team "Product Manager,Solution Architect,QA Engineer" --install .claude/skills
```

`--install .agents/skills` is the Codex equivalent. The command prints the skills it chose, an ordered plan (parallel where inputs allow) and the approvals a human must give.
See [skills/README.md](skills/README.md) and [docs/skills/SELECTION.md](docs/skills/SELECTION.md). All skills are drafts that have not been reviewed by domain experts.

## Downloads

Each release on the [Releases page](https://github.com/mohana-gutta/skillcrate/releases) attaches one zip per platform,
`SHA256SUMS`, a CycloneDX SBOM and Sigstore attestation bundles, and is signed. Verify a download with the GitHub CLI:

```bash
gh attestation verify <plugin>-<version>-claude.zip -R mohana-gutta/skillcrate
sha256sum -c SHA256SUMS
```

A valid attestation shows which workflow, repository and commit built the file. It does not mean the plugin is safe. Then follow the install steps above using the unzipped folder.

Licensed under the [MIT License](LICENSE).
