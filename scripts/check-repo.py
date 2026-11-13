#!/usr/bin/env python3
"""Repository checks that run in CI on every push: lock file, patch series and headers, build config, scripts."""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []


def err(msg):
    errors.append(msg)


def check_lock():
    lock = json.loads((ROOT / "upstream/source-lock.json").read_text())
    version = lock.get("version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        err(f"lock: version '{version}' is not a four-part upstream version")
    for key in ("gitTag", "gitCommit", "baseUrl", "signingKey", "tarballs"):
        if key not in lock:
            err(f"lock: missing '{key}'")
    if not re.fullmatch(r"[0-9a-f]{40}", lock.get("gitCommit", "")):
        err("lock: gitCommit must be a 40-character SHA-1")
    if not re.fullmatch(r"[0-9A-F]{40}", lock.get("signingKey", {}).get("fingerprint", "")):
        err("lock: signingKey.fingerprint must be 40 uppercase hex characters")
    if not lock.get("baseUrl", "").startswith("https://download.documentfoundation.org/"):
        err("lock: baseUrl must be on download.documentfoundation.org over HTTPS")
    names = set()
    for t in lock.get("tarballs", []):
        name = t.get("name", "")
        if version not in name or not name.endswith(".tar.xz"):
            err(f"lock: tarball '{name}' does not match version {version}")
        if not re.fullmatch(r"[0-9a-f]{64}", t.get("sha256", "")):
            err(f"lock: tarball '{name}' has an invalid sha256")
        if not isinstance(t.get("size"), int) or t["size"] <= 0:
            err(f"lock: tarball '{name}' has an invalid size")
        if name in names:
            err(f"lock: tarball '{name}' listed twice")
        names.add(name)
    if f"libreoffice-{version}.tar.xz" not in names:
        err("lock: the main source tarball is missing")


def check_patches():
    folder = ROOT / "patches/source"
    listed = []
    for line in (folder / "series").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            listed.append(line)
    for name in listed:
        path = folder / name
        if not path.is_file():
            err(f"patches: '{name}' is in series but the file is missing")
            continue
        head = path.read_text(errors="replace")[:4000]
        for field in ("Subject:", "Why:", "Upstream:", "Test:"):
            if field not in head:
                err(f"patches: '{name}' header lacks '{field}'")
    for path in folder.glob("*.patch"):
        if path.name not in listed:
            err(f"patches: '{path.name}' exists but is not listed in series")


def check_build_config():
    seen = set()
    for line in (ROOT / "build-config/macos.conf").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("--"):
            err(f"build-config: '{line}' is not a configure option")
        key = line.split("=", 1)[0]
        if key in seen:
            err(f"build-config: option '{key}' appears twice")
        seen.add(key)


def check_config():
    import xml.etree.ElementTree as ET
    for path in (ROOT / "config").glob("*.xcd"):
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            err(f"config: '{path.name}' is not well-formed XML: {exc}")


def check_scripts():
    for path in (ROOT / "scripts").glob("*.sh"):
        if path.name != "env.sh" and not os.access(path, os.X_OK):
            err(f"scripts: '{path.name}' is not executable")


for check in (check_lock, check_patches, check_build_config, check_config, check_scripts):
    check()

if errors:
    print("\n".join(f"FAIL {e}" for e in errors))
    sys.exit(1)
print("OK: lock, patches, build config, config layers and scripts pass")
