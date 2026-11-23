# Getting Started

Replace `<plugin>` with a name from the [Plugin Catalog](Plugin-Catalog).

| Platform | Install |
|---|---|
| Claude Code | `/plugin marketplace add mohana-gutta/skillcrate` then `/plugin install <plugin>@skillcrate` |
| Gemini CLI | `gemini extensions link plugins/gemini/<plugin>` (from a clone) |
| Codex | `mkdir -p ~/.agents/skills && cp -r plugins/codex/<plugin>/.agents/skills/<plugin> ~/.agents/skills/` (use `.agents/skills/` inside a repo for repo-only scope) |
| Any other agent | Copy `plugins/portable/<plugin>` into its skills directory |

Clone first for everything except Claude Code:

```bash
git clone https://github.com/mohana-gutta/skillcrate.git && cd skillcrate
```

## Run without an agent

Every plugin ships its script in `plugins/portable/<plugin>/scripts/`. Python 3 and the standard library are the only requirements.

```bash
python plugins/portable/iam-policy-diff-reviewer/scripts/iam_diff.py old.json new.json
python3 plugins/portable/actions-cache-key-auditor/scripts/cache_audit.py --path . --fail-on warning
```

Both support CI use through exit codes (see [Plugin Catalog](Plugin-Catalog)).

## Install from a release

Prefer pinned, verified artifacts? Download the per-platform zip from [Releases](https://github.com/mohana-gutta/skillcrate/releases) and [verify it](Release-and-Verification) first.
