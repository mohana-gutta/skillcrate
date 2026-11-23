"""List plugins in the index that have no git tag `<slug>-v<version>`.

Usage: pending_releases.py [--json] [--include SLUG]
  --json         print [{"slug":..., "version":...}] instead of `<slug> <version>` lines (for a workflow matrix)
  --include SLUG treat that published plugin as pending even if tagged (test runs only; the release job refuses to publish them)
"""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent


def pending(published: list[dict], tags: set[str], include: str = "") -> list[tuple[str, str]]:
    return [(e["name"], e["version"]) for e in published if f"{e['name']}-v{e['version']}" not in tags or e["name"] == include]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--include", default="")
    a = ap.parse_args()
    tags = set(subprocess.run(["git", "tag", "-l"], capture_output=True, text=True, check=True, cwd=ROOT).stdout.split())
    index = None
    if index is None:
        index = json.loads((ROOT / "plugins.json").read_text())
    rows = pending(index, tags, a.include)
    if a.json:
        print(json.dumps([{"slug": s, "version": v} for s, v in rows]))
    else:
        for s, v in rows:
            print(s, v)
