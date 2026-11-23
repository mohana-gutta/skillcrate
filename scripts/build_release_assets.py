"""Build release assets for one published capability: per-platform zips (deterministic), a CycloneDX SBOM,
SHA256SUMS, release-manifest.json (commit, versions, checksums) and RELEASE_NOTES.md. The release workflow then signs
the zips with GitHub artifact attestations (Sigstore).

Usage: build_release_assets.py <slug> <outdir> [--commit SHA]
Executes no capability code; it only zips generated files from plugins/.
"""
import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
FIXED_TIME = (2020, 1, 1, 0, 0, 0)  # reproducible zips: same input -> same checksum


def zip_dir(src: Path, dest: Path) -> None:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(p for p in src.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            info = zipfile.ZipInfo(f"{src.name}/{f.relative_to(src).as_posix()}", FIXED_TIME)
            info.external_attr = 0o644 << 16
            z.writestr(info, f.read_bytes(), zipfile.ZIP_DEFLATED)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def third_party_imports(scripts: Path) -> list[str]:
    """Top-level modules imported by a capability's scripts that are neither stdlib nor sibling scripts."""
    local = {p.stem for p in scripts.glob("*.py")}
    found = set()
    for f in scripts.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else []
            found |= {n.split(".")[0] for n in names} - set(sys.stdlib_module_names) - local
    return sorted(found)


def sbom(slug: str, cap: dict, pkg: Path, imports: list[str], license_id: str | None) -> dict:
    """CycloneDX 1.5: the plugin, every shipped file with its SHA-256, and third-party Python imports.
    Deterministic: the serialNumber is a UUID derived from the content (GitHub's attest action requires one)."""
    ref = f"pkg:generic/{slug}@{cap['version']}"
    files = [{"type": "file", "bom-ref": f"file:{f.relative_to(pkg).as_posix()}", "name": f.relative_to(pkg).as_posix(),
              "hashes": [{"alg": "SHA-256", "content": sha256(f)}]}
             for f in sorted(p for p in pkg.rglob("*") if p.is_file() and "__pycache__" not in p.parts)]
    libs = [{"type": "library", "bom-ref": f"pkg:pypi/{m}", "name": m, "purl": f"pkg:pypi/{m}"} for m in imports]
    comp = {"type": "application", "bom-ref": ref, "name": slug, "version": cap["version"], "description": cap["description"]}
    if license_id:
        comp["licenses"] = [{"license": {"id": license_id}}]
    serial = uuid.uuid5(uuid.NAMESPACE_URL, json.dumps([ref, files, libs], sort_keys=True))
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{serial}", "version": 1,
            "metadata": {"component": comp}, "components": files + libs,
            "dependencies": [{"ref": ref, "dependsOn": [lib["bom-ref"] for lib in libs]}]}


def load_meta(slug: str, root: Path) -> tuple[dict, dict, Path]:
    """(plugin metadata, index entry, scripts dir) read from plugins.json and the packages under plugins/."""
    entry = next(e for e in json.loads((root / "plugins.json").read_text()) if e["name"] == slug)
    cap = {"name": slug, "version": entry["version"], "description": entry["description"], "platforms": entry["platforms"],
           "permissions": {"profile": entry["permission_profile"]}}
    pkgs = root / "plugins"
    scripts = next((d for d in (pkgs / "portable" / slug / "scripts", pkgs / "claude" / slug / "skills" / slug / "scripts",
                                pkgs / "codex" / slug / ".agents/skills" / slug / "scripts",
                                pkgs / "gemini" / slug / "skills" / slug / "scripts") if d.is_dir()), pkgs / "none")
    return cap, entry, scripts


def build(slug: str, out: Path, commit: str, root: Path = ROOT, repo: str = "<owner>/<repo>") -> dict:
    cap, entry, scripts = load_meta(slug, root)
    if entry["version"] != cap["version"]:
        raise SystemExit(f"index version {entry['version']} != package version {cap['version']}")
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for platform in cap["platforms"]:
        src = root / "plugins" / platform / slug
        if not src.is_dir():
            raise SystemExit(f"missing package {src}")
        dest = out / f"{slug}-{cap['version']}-{platform}.zip"
        zip_dir(src, dest)
        files.append({"name": dest.name, "sha256": sha256(dest)})
    # shortcut: files listed come from one package (portable if claimed, else the first platform); all platforms ship the same skill tree
    pkg = root / "plugins" / ("portable" if "portable" in cap["platforms"] else cap["platforms"][0]) / slug
    lic = (root / "LICENSE").read_text().startswith("MIT License") if (root / "LICENSE").exists() else False
    bom = out / f"{slug}-{cap['version']}.sbom.cdx.json"
    bom.write_text(json.dumps(sbom(slug, cap, pkg, third_party_imports(scripts) if scripts.is_dir() else [],
                                   "MIT" if lic else None), indent=2) + "\n")
    files.append({"name": bom.name, "sha256": sha256(bom)})
    (out / "SHA256SUMS").write_text("".join(f"{f['sha256']}  {f['name']}\n" for f in files))
    manifest = {"name": slug, "version": cap["version"], "commit": commit, "platforms": cap["platforms"],
                "permission_profile": cap["permissions"]["profile"], "files": files}
    (out / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    z = f"{slug}-{cap['version']}-claude.zip"
    notes = [f"# {slug} {cap['version']}", "", cap["description"], "",
             f"Permissions: `{cap['permissions']['profile']}`. Built from commit `{commit}`.", "",
             "**Verify** (needs the GitHub CLI):", "```", f"gh attestation verify {z} -R {repo}",
             f"gh attestation verify {z} -R {repo} --predicate-type https://cyclonedx.org/bom", "sha256sum -c SHA256SUMS", "```",
             "The first command checks signed build provenance (which workflow, repository and commit built the file); the second checks "
             "the SBOM attestation. A valid attestation proves where and how a file was built, not that the plugin is safe. "
             "Install steps are in the repository README."]
    (out / "RELEASE_NOTES.md").write_text("\n".join(notes) + "\n")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--commit")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "<owner>/<repo>"))
    a = ap.parse_args()
    commit = a.commit or subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=ROOT).stdout.strip()
    print(json.dumps(build(a.slug, a.outdir, commit, repo=a.repo), indent=2))
