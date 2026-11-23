# Release and Verification

Pushing to `main` releases every plugin in `plugins.json` that lacks a `<name>-v<version>` tag.

```
push main -> assets job -> attest job -> release job
             zips, SBOM,   Sigstore       re-verify, tag,
             SHA256SUMS    provenance+SBOM GitHub Release
                           (verified)
```

- **Reproducible zips:** fixed timestamps, same input gives the same checksum.
- **No plugin code executed** during the build.
- **Attestations:** GitHub artifact attestations (Sigstore keyless, no stored keys) for provenance and SBOM; a verification failure stops the release.
- **Kill switch:** set repository variable `PUBLISHING_DISABLED=true`.
- **Dry run:** run the workflow manually on a non-main ref with `include=<plugin>`; it builds and verifies but never publishes.
- Actions are pinned by commit SHA.

## Verify a download

```bash
gh attestation verify <plugin>-<version>-claude.zip -R mohana-gutta/skillcrate
sha256sum -c SHA256SUMS
```

A valid attestation shows which workflow, repository and commit built the file. It does **not** mean the plugin is safe; review the source.

Release assets: per-platform zips, `SHA256SUMS`, `release-manifest.json`, CycloneDX SBOM, provenance and SBOM Sigstore bundles.
