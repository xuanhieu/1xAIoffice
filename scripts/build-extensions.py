#!/usr/bin/env python3
"""Package every extension under extensions/<name>/ (folders with a description.xml) into dist/<name>.oxt.

Development-only content is left out: tests/, tools/, data/sources/, __pycache__, *.pyc.
Usage: scripts/build-extensions.py [--out dist]
"""
import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"tests", "tools", "__pycache__"}


def wanted(rel):
    parts = rel.parts
    if any(p in SKIP_DIRS for p in parts) or rel.suffix == ".pyc" or rel.name == ".DS_Store":
        return False
    return parts[:2] != ("data", "sources")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for ext in sorted(p.parent for p in (ROOT / "extensions").glob("*/description.xml")):
        target = out / f"{ext.name}.oxt"
        files = sorted(f for f in ext.rglob("*") if f.is_file() and wanted(f.relative_to(ext)))
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.relative_to(ext).as_posix())
        print(f"{target}: {len(files)} file")


if __name__ == "__main__":
    main()
