# Architecture

```
            plugins/portable/<name>/   <- source of truth
              SKILL.md  scripts/  references/  examples/
                              |
        +---------------------+---------------------+
        v                     v                     v
plugins/claude/<name>  plugins/codex/<name>  plugins/gemini/<name>
 skills/ + README       .agents/skills/       skills/ + GEMINI.md
 (marketplace source)   (copy to ~/.agents)   + gemini-extension.json
        |
.claude-plugin/marketplace.json   plugins.json (release index)
```

## Layout

| Path | Role |
|---|---|
| `plugins/portable/` | Platform-neutral skill: `SKILL.md` + script + docs |
| `plugins/{claude,codex,gemini}/` | Generated per-platform packages |
| `.claude-plugin/marketplace.json` | Claude Code marketplace manifest |
| `plugins.json` | Plugin index: name, version, platforms, permission profile |
| `scripts/` | Release tooling (`pending_releases.py`, `build_release_assets.py`, `verify_attestations.sh`) |
| `.github/workflows/marketplace-release.yml` | Sign and publish pipeline |

## Conventions

- One plugin = one skill = one script, Python 3 standard library only.
- Scripts are deterministic, offline and never write files; exit codes are the CI contract.
- `SKILL.md` instructs the agent to treat analyzed input as data, report exact evidence, and gate edits on user approval.
- The README plugin table is generated between `plugins:table` markers; do not edit it by hand.
