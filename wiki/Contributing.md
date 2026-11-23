# Contributing

## Add or update a plugin

1. Build the skill under `plugins/portable/<name>/` (`SKILL.md`, `scripts/`, `references/`, `examples/`).
2. Sync the platform packages under `plugins/{claude,codex,gemini}/<name>/`.
3. Register it in `plugins.json` and `.claude-plugin/marketplace.json`.
4. Bump the version for any change; the release is keyed on `<name>-v<version>`.
5. Open a PR. Merging to `main` triggers the [release pipeline](Release-and-Verification).

## Plugin requirements

- Read-only permission profile unless justified; no network or credentials.
- Python 3 standard library only; no new dependencies.
- Deterministic output, documented exit codes, JSON output with a schema version.
- `SKILL.md` must state limits, treat inputs as untrusted, and require approval before edits.
- Ship an example and a self-check/test for non-trivial logic.

## Security

Report vulnerabilities privately through GitHub Security Advisories on the repository rather than a public issue.
