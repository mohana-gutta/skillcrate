# skillcrate

Agent plugins for **Claude Code**, **OpenAI Codex** and **Gemini CLI**. Each plugin is one reusable skill, packaged once per platform, with signed and verifiable releases.

| | |
|---|---|
| [Getting Started](Getting-Started) | Install a plugin on your platform |
| [Plugin Catalog](Plugin-Catalog) | What each plugin does, its rules and limits |
| [Architecture](Architecture) | Repository layout and how one skill becomes four packages |
| [Release and Verification](Release-and-Verification) | Signing, SBOM, attestations, how to verify a download |
| [Contributing](Contributing) | Add or update a plugin |

## Design principles

- **Read-only by default.** Both current plugins have the `read-only` permission profile: no network, no credentials, no writes.
- **Deterministic core.** The analysis is a standard-library Python script; the agent explains results, it does not compute them.
- **Honest verdicts.** Plugins say what was checked and never claim "safe".
- **Verifiable supply chain.** Reproducible zips, CycloneDX SBOM, SHA256SUMS, Sigstore attestations.

## Current plugins

| Plugin | Version | Purpose |
|---|---|---|
| `iam-policy-diff-reviewer` | 0.2.0 | Review AWS IAM policy changes (JSON or Terraform plan) for newly granted access |
| `actions-cache-key-auditor` | 0.1.0 | Find GitHub Actions cache keys that never refresh or never hit |
