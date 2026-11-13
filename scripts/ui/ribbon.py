#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Biến ribbon (tabbed notebookbar) của upstream thành bố cục gọn kiểu WPS / Microsoft Office.

Đọc bản gốc trong mã nguồn (<src>/<module>/uiconfig/<app>/ui/notebookbar.ui) và ghi bản đã biến đổi vào app
(Contents/Resources/config/soffice.cfg/modules/<app>/ui/notebookbar.ui), nên chạy lại bao nhiêu lần cũng ra cùng kết
quả và không cần build lại lõi. Quy tắc:
  1. Gỡ tên nhóm (Clipboard, Font, Paragraph…): WPS và Office 2026 không hiện, ribbon thấp và thoáng hơn.
  2. Lệnh chính thành nút lớn có chữ bên dưới (LARGE), giống Paste.
  3. Lệnh phụ chỉ hiện icon (ICON_ONLY), không kèm chữ.
  4. Gỡ thẻ "Extension" (nơi upstream dồn mọi lệnh của extension) và chuyển điểm chèn lệnh extension sang cuối thẻ
     Home, nên nút NĐ30 và công cụ tiếng Việt nằm ngay trên Home như các lệnh riêng của WPS.
Dùng: scripts/ui/ribbon.py --src <mã nguồn upstream> --app <1xVnOffice.app> [--check]
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


def _remove_group_labels(root):
    """Gỡ hẳn nhãn nhóm (Clipboard, Font, ...) khỏi cây thay vì đặt visible=False: nhãn ẩn vẫn được dựng và đo, và
    trên macOS làm tăng hẳn khả năng soffice bị huỷ khi dựng ribbon."""
    parent = {c: p for p in root.iter() for c in p}
    n = 0
    for obj in list(root.iter("object")):
        oid = obj.get("id") or ""
        if obj.get("class") == "GtkLabel" and oid.startswith("lb") and any(
                a.get("name") == "style" and a.get("value") == "italic" for a in obj.iter("attribute")):
            slot = parent.get(obj)
            if slot is not None and slot.tag == "child" and slot in parent:
                parent[slot].remove(slot)
                n += 1
    return n


def transform(root, skip=()):
    stats = {"labels": 0, "large": 0, "icon_only": 0}
    if "labels" not in skip:
        stats["labels"] = _remove_group_labels(root)
    for obj in root.iter("object"):
        cls, oid = obj.get("class"), obj.get("id") or ""
        if cls == TOOLBOX and "style" not in skip:
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


def move_addons_to_home(root):
    """Chuyển NotebookBarAddonsToolMergePoint sang thẻ Home và gỡ thẻ chứa nó. Báo lỗi rõ nếu cấu trúc đổi."""
    parent = {c: p for p in root.iter() for c in p}

    def enclosing_child(el):
        while el is not None and el.tag != "child":
            el = parent.get(el)
        return el

    merge = next((o for o in root.iter("object") if o.get("class") == "NotebookBarAddonsToolMergePoint"), None)
    home = next((o for o in root.iter("object") if o.get("id") == "pmhbHome"), None)
    if merge is None or home is None:
        raise SystemExit("LỖI ribbon: không thấy điểm chèn extension hoặc nhóm Home (bố cục gốc đã đổi?)")
    # Thẻ chứa điểm chèn = tổ tiên là con trực tiếp của NotebookbarTabControl.
    page = merge
    while page is not None:
        holder = parent.get(page)
        if holder is not None and holder.tag == "object" and holder.get("class") == "sfxlo-NotebookbarTabControl" \
                and page.tag == "child":
            break
        page = parent.get(page)
    if page is None:
        raise SystemExit("LỖI ribbon: không thấy thẻ chứa điểm chèn extension")
    notebook = parent[page]
    kids = list(notebook)
    idx = kids.index(page)
    # Trong bản gốc nhãn thẻ đứng NGAY SAU trang của nó: [trang File][nhãn File][trang Home][nhãn Home]...
    tab_label = kids[idx + 1] if idx + 1 < len(kids) and kids[idx + 1].get("type") == "tab" else None
    if tab_label is None:
        raise SystemExit("LỖI ribbon: thẻ Extension không có nhãn đứng sau")
    label_obj = next((o for o in tab_label.iter("object") if o.get("class") == "GtkLabel"), None)
    if label_obj is None or "Extension" not in (label_obj.get("id") or ""):
        raise SystemExit(f"LỖI ribbon: nhãn sau thẻ chứa extension không phải Extension ({label_obj.get('id') if label_obj is not None else None})")
    # Lấy điểm chèn ra khỏi thẻ cũ rồi đặt vào Home.
    slot = enclosing_child(merge)
    parent[slot].remove(slot)
    for pos in slot.iter("property"):
        if pos.get("name") == "position":
            pos.text = "99"
    home.append(slot)
    notebook.remove(page)
    notebook.remove(tab_label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--app", required=True)
    ap.add_argument("--check", action="store_true", help="chỉ kiểm, không ghi")
    ap.add_argument("--skip", action="append", default=[], choices=["labels", "style", "addons"],
                    help="tắt một phần biến đổi để tìm nguyên nhân khi ribbon lỗi")
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
        stats = transform(tree.getroot(), a.skip)
        if "addons" not in a.skip:
            move_addons_to_home(tree.getroot())
        if stats["labels"] == 0:
            print(f"LỖI {app}: không thấy tên nhóm nào, bố cục gốc đã đổi?")
            ok = False
        if not a.check:
            tree.write(dest, encoding="UTF-8", xml_declaration=True)
        print(f"{app}: gỡ {stats["labels"]} tên nhóm, {stats['large']} nút lớn, {stats['icon_only']} nút chỉ icon, "
              "lệnh extension chuyển sang Home")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
