#!/usr/bin/env bash
# Verify the signed provenance and SBOM attestations of every zip of one release. Any failure exits non-zero, which blocks publishing.
# Checks: signature chain (Sigstore), this repository, the signer workflow, the source commit and ref, the GitHub OIDC issuer.
# Usage: verify_attestations.sh DIR PROVENANCE_BUNDLE SBOM_BUNDLE   (env: GH_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA, GITHUB_REF)
set -euo pipefail
dir=$1; prov=$2; bom=$3
: "${GITHUB_REPOSITORY:?}" "${GITHUB_SHA:?}" "${GITHUB_REF:?}"
n=0
for zip in "$dir"/*.zip; do
  for spec in "$prov|https://slsa.dev/provenance/v1" "$bom|https://cyclonedx.org/bom"; do
    gh attestation verify "$zip" --bundle "${spec%%|*}" --repo "$GITHUB_REPOSITORY" --predicate-type "${spec#*|}" \
      --signer-workflow "$GITHUB_REPOSITORY/.github/workflows/marketplace-release.yml" \
      --source-digest "$GITHUB_SHA" --source-ref "$GITHUB_REF" \
      --cert-oidc-issuer https://token.actions.githubusercontent.com > /dev/null
    echo "verified ${zip##*/} (${spec#*|})"
    n=$((n + 1))
  done
done
[ "$n" -gt 0 ] || { echo "no zips found in $dir" >&2; exit 1; }
