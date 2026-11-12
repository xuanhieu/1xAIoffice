#!/usr/bin/env python3
"""Measure how a notebookbar (ribbon) .ui file places the commands of a Word-style command map.

For each row of the map (tab, group, command) it reports: the command is defined in LibreOffice; it appears on the
ribbon; and it sits on the expected tab. Exit code 1 when the share on the expected tab is below --min.

Usage:
  scripts/ui-coverage.py --map docs/ui/writer-command-map.csv \
      --ui $SRC/sw/uiconfig/swriter/ui/notebookbar.ui \
      --commands $SRC/officecfg/registry/data/org/openoffice/Office/UI \
      [--tab-names Home=Trang đầu,Insert=Chèn,...] [--min 0.0] [--markdown out.md]
"""
import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# LibreOffice tab label ids -> the tab names used in the command map (Word layout, Vietnamese).
DEFAULT_TABS = {
    "HomeLabel": "Trang đầu", "InsertLabel": "Chèn", "DesignLabel": "Thiết kế", "LayoutLabel": "Bố cục",
    "ReferencesLabel": "Tham chiếu", "MailingsLabel": "Thư", "ReviewLabel": "Xem lại", "ViewLabel": "Xem",
    "HelpLabel": "Trợ giúp", "FileLabel": "Tệp",
}


def defined_commands(folder):
    names = set()
    for path in Path(folder).glob("*Commands.xcu"):
        for node in ET.parse(path).iter("node"):
            name = node.get("{http://openoffice.org/2001/registry}name", "")
            if name.startswith(".uno:"):
                names.add(name)
    return names


def actions_under(element):
    found = set()
    for prop in element.iter("property"):
        if prop.get("name") in ("action-name", "action_name") and (prop.text or "").startswith(".uno:"):
            found.add(prop.text.strip())
    return found


def ribbon_tabs(ui_path):
    """{tab label id: set of commands} for the largest GtkNotebook, plus every command anywhere in the file."""
    root = ET.parse(ui_path).getroot()
    notebooks = [o for o in root.iter("object") if o.get("class") in ("GtkNotebook", "sfxlo-NotebookbarTabControl")]
    if not notebooks:
        sys.exit(f"no notebook (tab control) in {ui_path}")
    main = max(notebooks, key=lambda nb: len(list(nb.iter("object"))))
    tabs, page = {}, None
    for child in main.findall("child"):
        obj = child.find("object")
        if obj is None:
            continue
        if child.get("type") == "tab":
            if page is not None:
                tabs[obj.get("id", "?")] = actions_under(page)
            page = None
        else:
            page = obj
    return tabs, actions_under(root)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--ui", required=True)
    ap.add_argument("--commands", required=True)
    ap.add_argument("--min", type=float, default=0.0)
    ap.add_argument("--markdown")
    args = ap.parse_args()

    known = defined_commands(args.commands)
    tabs, anywhere = ribbon_tabs(args.ui)
    where = {}
    for tab_id, cmds in tabs.items():
        for c in cmds:
            where.setdefault(c, []).append(DEFAULT_TABS.get(tab_id, tab_id))

    rows = list(csv.DictReader(open(args.map, encoding="utf-8")))
    on_tab = on_ribbon = undefined = 0
    lines = ["| Thẻ mong đợi | Nhóm | Lệnh | Tên lệnh UNO | Đang ở | Kết quả |", "|---|---|---|---|---|---|"]
    for r in rows:
        # A cell may list alternatives ("a|b"): LibreOffice often has several commands for one Office action.
        cmds, tab = r["command"].split("|"), r["tab"]
        here = sorted({t for c in cmds for t in where.get(c, [])})
        if not any(c in known for c in cmds):
            status = "lệnh không tồn tại"
            undefined += 1
        elif tab in here:
            status = "đúng thẻ"
            on_tab += 1
            on_ribbon += 1
        elif here or any(c in anywhere for c in cmds):
            status = "sai thẻ"
            on_ribbon += 1
        else:
            status = "thiếu trên ribbon"
        shown = " / ".join(f"`{c}`" for c in cmds)
        lines.append(f"| {tab} | {r['group']} | {r['label_vi']} | {shown} | {', '.join(here) or '-'} | {status} |")

    total = len(rows)
    share = on_tab / total if total else 0.0
    summary = (f"{total} lệnh: {on_tab} đúng thẻ ({share:.0%}), {on_ribbon - on_tab} sai thẻ, "
               f"{total - on_ribbon - undefined} thiếu trên ribbon, {undefined} tên lệnh không tồn tại.")
    print(summary)
    if args.markdown:
        Path(args.markdown).write_text(f"# Độ phủ ribbon\n\nFile: `{Path(args.ui).name}`\n\n{summary}\n\n"
                                       + "\n".join(lines) + "\n", encoding="utf-8")
    sys.exit(0 if share >= args.min else 1)


if __name__ == "__main__":
    main()
