# Contributing

Thanks for helping. By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Please read this before opening a PR. More detail: [wiki/Contributing.md](wiki/Contributing.md) and [wiki/Architecture.md](wiki/Architecture.md).

## Add or update a plugin

1. Build the skill in `plugins/portable/<name>/`: `SKILL.md`, `scripts/`, `references/`, `examples/`.
2. Sync the platform packages in `plugins/{claude,codex,gemini}/<name>/`.
3. Register it in `plugins.json` and `.claude-plugin/marketplace.json`.
4. Bump the version on every change. Releases are keyed on `<name>-v<version>`.
5. Open a PR. Merging to `main` triggers the signed release.

Do not hand-edit the generated plugin table in `README.md` (between the `plugins:table` markers).

## Requirements

- Read-only permission profile unless clearly justified: no network, no credentials.
- Python 3 standard library only; no new dependencies.
- Deterministic output, documented exit codes, JSON output with a `schema_version`.
- `SKILL.md` states the limits, treats analyzed input as untrusted, and requires user approval before any edit.
- Include an example and a small test or self-check for non-trivial logic.
- Never claim a result is "safe"; report what was checked.

## Pull requests

- Keep PRs focused: one plugin or one concern.
- Describe what changed and how you checked it.
- Security issues: do not use a PR or issue; follow [SECURITY.md](SECURITY.md).

## License

Contributions are licensed under the [MIT License](LICENSE).
