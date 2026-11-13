#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Biến ribbon (tabbed notebookbar) của LibreOffice thành bố cục gọn kiểu WPS / Microsoft Office.

Đọc bản gốc trong mã nguồn (<src>/<module>/uiconfig/<app>/ui/notebookbar.ui) và ghi bản đã biến đổi vào app
(Contents/Resources/config/soffice.cfg/modules/<app>/ui/notebookbar.ui), nên chạy lại bao nhiêu lần cũng ra cùng kết
quả và không cần build lại lõi. Quy tắc:
  1. Ẩn tên nhóm (Clipboard, Font, Paragraph…): WPS và Office 2026 không hiện, ribbon thấp và thoáng hơn.
  2. Lệnh chính thành nút lớn có chữ bên dưới (LARGE), giống Paste.
  3. Lệnh phụ chỉ hiện icon (ICON_ONLY), không kèm chữ.
Dùng: scripts/ui/ribbon.py --src <mã nguồn LibreOffice> --app <1xVnOffice.app> [--check]
"""
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

APPS = {"swriter": "sw", "scalc": "sc", "simpress": "sd", "sdraw": "sd"}
LARGE = {".uno:FormatPaintbrush", ".uno:SearchDialog"}
ICON_ONLY = {".uno:Cut", ".uno:Copy", ".uno:ResetAttributes", ".uno:SetDefault"}
TOOLBOX = "sfxlo-NotebookbarToolBox"


def _prop(obj, name):
    for p in obj.findall("property"):
        if p.get("name") == name:
            return p
    return None


def _set(obj, name, value):
    p = _prop(obj, name)
    if p is None:
        p = ET.SubElement(obj, "property", {"name": name})
        obj.remove(p)
        obj.insert(0, p)
    p.text = value


def _actions(toolbox):
    return {p.text for p in toolbox.iter("property") if p.get("name") == "action-name"}


def transform(root):
    stats = {"labels": 0, "large": 0, "icon_only": 0}
    for obj in root.iter("object"):
        cls, oid = obj.get("class"), obj.get("id") or ""
        if cls == "GtkLabel" and oid.startswith("lb") and any(
                a.get("name") == "style" and a.get("value") == "italic" for a in obj.iter("attribute")):
            _set(obj, "visible", "False")
            stats["labels"] += 1
        elif cls == TOOLBOX:
            acts = _actions(obj)
            if acts and acts <= LARGE:
                _set(obj, "toolbar-style", "both")
                _set(obj, "icon_size", "3")
                _set(obj, "valign", "center")
                _set(obj, "vexpand", "True")
                stats["large"] += 1
            elif acts and acts <= ICON_ONLY and (_prop(obj, "toolbar-style") is not None and
                                                 _prop(obj, "toolbar-style").text == "both-horiz"):
                _set(obj, "toolbar-style", "icons")
                stats["icon_only"] += 1
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--app", required=True)
    ap.add_argument("--check", action="store_true", help="chỉ kiểm, không ghi")
    a = ap.parse_args()
    ok = True
    for app, module in APPS.items():
        src = Path(a.src) / module / "uiconfig" / app / "ui" / "notebookbar.ui"
        dest = Path(a.app) / "Contents/Resources/config/soffice.cfg/modules" / app / "ui" / "notebookbar.ui"
        if not src.is_file() or not dest.parent.is_dir():
            print(f"BỎ QUA {app}: thiếu {src if not src.is_file() else dest.parent}")
            ok = False
            continue
        tree = ET.parse(src)
        stats = transform(tree.getroot())
        if stats["labels"] == 0:
            print(f"LỖI {app}: không thấy tên nhóm nào, bố cục gốc đã đổi?")
            ok = False
        if not a.check:
            tree.write(dest, encoding="UTF-8", xml_declaration=True)
        print(f"{app}: ẩn {stats['labels']} tên nhóm, {stats['large']} nút lớn, {stats['icon_only']} nút chỉ icon")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
