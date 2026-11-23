# Security Policy

## Reporting a vulnerability

Report privately through [GitHub Security Advisories](https://github.com/mohana-gutta/skillcrate/security/advisories/new). Do not open a public issue for a vulnerability.

Include the affected plugin and version, reproduction steps, and the impact. Expect an initial response within a few days; fixes ship as a new plugin version through the normal release pipeline.

## Scope

In scope: the plugin scripts and skill instructions (`plugins/`), the release tooling (`scripts/`, `.github/workflows/`), and the published release artifacts.

Examples: a crafted input that makes a script execute code or write files, a `SKILL.md` that can be steered by analyzed content, or a release artifact that does not match its attestation.

Out of scope: missed findings (false negatives) in a documented limitation, such as SCPs not being evaluated by `iam-policy-diff-reviewer`. Open a normal issue for those.

## Security model

- Plugins are read-only: offline, no credentials, no network, no file writes.
- Analyzed content (policies, workflows, plans) is treated as untrusted data; instructions inside it are never followed.
- No edit or patch is applied without explicit user approval.
- Scripts use the Python 3 standard library only.

## Verifying releases

Releases carry SHA256SUMS, a CycloneDX SBOM and Sigstore attestations. See [Release and Verification](wiki/Release-and-Verification.md).

```bash
gh attestation verify <plugin>-<version>-claude.zip -R mohana-gutta/skillcrate
```

## Supported versions

Only the latest released version of each plugin receives fixes.
