#!/usr/bin/env python3
"""Merge the 1xVnOffice translation layer (l10n/<lang>/**.po) into the LibreOffice translations tree before a build.

Each overlay file mirrors a path under translations/source/<lang>/ (for example l10n/vi/sw/messages.po ->
translations/source/vi/sw/messages.po). An overlay entry replaces the msgstr of the entry with the same msgctxt and
msgid and clears its fuzzy flag. Overlay entries that match nothing are reported (the English source changed) and make
the run fail with --strict.

Usage: scripts/l10n-merge.py --src <libreoffice source dir> [--lang vi] [--strict] [--dry-run]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import po  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--lang", default="vi")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    overlay_root = ROOT / "l10n" / args.lang
    target_root = Path(args.src) / "translations" / "source" / args.lang
    if not target_root.is_dir():
        sys.exit(f"không thấy {target_root}")

    applied = unchanged = stale = 0
    for overlay in sorted(overlay_root.rglob("*.po")):
        rel = overlay.relative_to(overlay_root)
        target = target_root / rel
        if not target.is_file():
            print(f"BỎ QUA {rel}: không có file đích")
            stale += 1
            continue
        entries = po.load(target)
        index = {e.key: e for e in entries if e.fields.get("msgid")}
        changed = False
        for o in po.load(overlay):
            if not o.fields.get("msgid"):
                continue
            t = index.get(o.key)
            if t is None:
                print(f"LỖI THỜI {rel}: {o.key[0].splitlines()[1] if chr(10) in o.key[0] else o.key[0]} / {o.key[1]!r}")
                stale += 1
                continue
            if t.fields.get("msgstr") == o.fields["msgstr"] and not t.fuzzy:
                unchanged += 1
                continue
            t.set_translation(o.fields["msgstr"])
            applied += 1
            changed = True
        if changed and not args.dry_run:
            po.save(target, entries)
    print(f"Lớp dịch {args.lang}: áp {applied}, đã khớp sẵn {unchanged}, lỗi thời {stale}.")
    sys.exit(1 if (args.strict and stale) else 0)


if __name__ == "__main__":
    main()
