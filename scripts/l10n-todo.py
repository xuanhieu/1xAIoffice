#!/usr/bin/env python3
"""List the strings of a LibreOffice translation file that still need a 1xVnOffice translation, and apply finished
translations back into the l10n layer.

  export: scripts/l10n-todo.py export --src <lo src> --po sw/messages.po --out <dir> [--batch 250]
          Writes <dir>/<module>-NNN.tsv with: id, msgctxt, English. Entries already translated upstream (not fuzzy)
          or already in l10n/vi are skipped.
  apply:  scripts/l10n-todo.py apply --src <lo src> --po sw/messages.po --tsv <file>...
          Reads id<TAB>Vietnamese lines, checks each against its English source (placeholders, mnemonic, line
          breaks) and adds the good ones to l10n/vi/<po>. Problems are printed and the entry is skipped.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import po  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# %1 %2, %s %d, $(ARG1), %PRODUCTNAME, %{name}, $1, ${name}, lowercase markup tags (<b>, <a href=...>).
# Display text in angle brackets such as "<None>" is translatable and not a placeholder.
PLACEHOLDER = re.compile(r'%[0-9]+|%[sdu]|%\{?[A-Z][A-Z0-9_]*\}?|\$\([A-Za-z0-9_]+\)|\$[0-9]+|\$\{[^}]+\}|</?[a-z][a-z0-9]*(?:\s[^>]*)?>')


def esc(s):
    return s.replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n')


def unesc(s):
    return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')


def overlay_path(po_rel):
    return ROOT / 'l10n' / 'vi' / po_rel


def problems(en, vi):
    out = []
    if sorted(PLACEHOLDER.findall(en)) != sorted(PLACEHOLDER.findall(vi)):
        out.append(f"placeholder {sorted(PLACEHOLDER.findall(en))} != {sorted(PLACEHOLDER.findall(vi))}")
    for m in '~_':
        if re.search(re.escape(m) + r'\w', en) and not re.search(re.escape(m) + r'\w', vi):
            out.append(f"thiếu phím tắt {m}")
    if en.count('\n') != vi.count('\n'):
        out.append("số dòng khác bản gốc")
    if not vi.strip() and vi != en:
        out.append("rỗng")
    return out


def cmd_export(args):
    target = po.load(Path(args.src) / 'translations/source/vi' / args.po)
    done = set()
    ov = overlay_path(args.po)
    if ov.is_file():
        done = {e.key for e in po.load(ov) if e.fields.get('msgid')}
    todo = [e for e in target if e.fields.get('msgid') and not po.is_translated(e) and e.key not in done]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    module = args.po.split('/')[0]
    index = {}
    for n in range(0, len(todo), args.batch):
        chunk = todo[n:n + args.batch]
        name = f"{module}-{n // args.batch + 1:03d}.tsv"
        with open(out / name, 'w', encoding='utf-8') as f:
            for i, e in enumerate(chunk, start=n):
                index[str(i)] = [e.fields.get('msgctxt', ''), e.fields['msgid']]
                f.write(f"{i}\t{esc(e.fields.get('msgctxt', ''))}\t{esc(e.fields['msgid'])}\n")
    (out / f"{module}-index.json").write_text(json.dumps(index, ensure_ascii=False), encoding='utf-8')
    print(f"{len(todo)} chuỗi cần dịch trong {args.po}, chia {-(-len(todo) // args.batch)} lô ở {out}")


def cmd_apply(args):
    module = args.po.split('/')[0]
    index = json.loads((Path(args.tsv[0]).parent / f"{module}-index.json").read_text(encoding='utf-8'))
    ov = overlay_path(args.po)
    entries = po.load(ov) if ov.is_file() else []
    if not entries:
        hdr = po.Entry()
        hdr.comments = ['# 1xVnOffice: lớp dịch tiếng Việt bổ sung cho LibreOffice (MPL-2.0).']
        hdr.set_field('msgid', '')
        hdr.set_field('msgstr', 'Content-Type: text/plain; charset=UTF-8\n')
        entries.append(hdr)
    have = {e.key: e for e in entries if e.fields.get('msgid')}
    added = skipped = 0
    for tsv in args.tsv:
        for line in Path(tsv).read_text(encoding='utf-8').splitlines():
            if not line.strip() or '\t' not in line:
                continue
            i, vi = line.split('\t', 1)
            if i not in index:
                print(f"BỎ {tsv}: id {i} không có trong lô")
                skipped += 1
                continue
            ctx, en = index[i]
            vi = unesc(vi)
            bad = problems(en, vi)
            if bad:
                print(f"BỎ {i} {ctx}: {'; '.join(bad)} | {en!r} -> {vi!r}")
                skipped += 1
                continue
            e = have.get((ctx, en))
            if e is None:
                e = po.Entry()
                e.comments = [f'#: {args.po}']
                e.set_field('msgctxt', ctx)
                e.set_field('msgid', en)
                entries.append(e)
                have[(ctx, en)] = e
            e.set_field('msgstr', vi)
            added += 1
    ov.parent.mkdir(parents=True, exist_ok=True)
    po.save(ov, entries)
    print(f"Thêm/cập nhật {added}, bỏ {skipped}; {ov.relative_to(ROOT)} có {len(have)} chuỗi")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export')
    e.add_argument('--src', required=True)
    e.add_argument('--po', required=True)
    e.add_argument('--out', required=True)
    e.add_argument('--batch', type=int, default=250)
    a = sub.add_parser('apply')
    a.add_argument('--src', required=True)
    a.add_argument('--po', required=True)
    a.add_argument('--tsv', nargs='+', required=True)
    args = ap.parse_args()
    cmd_export(args) if args.cmd == 'export' else cmd_apply(args)


if __name__ == '__main__':
    main()
