#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Biến ribbon (tabbed notebookbar) của upstream thành bố cục gọn kiểu WPS / Microsoft Office.

Đọc bản gốc trong mã nguồn (<src>/<module>/uiconfig/<app>/ui/notebookbar.ui) và ghi bản đã biến đổi vào app
(Contents/Resources/config/soffice.cfg/modules/<app>/ui/notebookbar.ui), nên chạy lại bao nhiêu lần cũng ra cùng kết
quả và không cần build lại lõi. Quy tắc:
  1. Gỡ tên nhóm (Clipboard, Font, Paragraph…): WPS và Office 2026 không hiện, ribbon thấp và thoáng hơn.
  2. Giữ nguyên nút lớn của bản gốc, chỉ hạ những nút đã nhìn thấy gây hại (DEMOTE_LARGE). Nút lớn mang tên
     dài như "Merge and Center Cells" kéo cả cột rộng ra và để lại mảng trống giữa ribbon — đó chính là lỗ
     hổng thấy được khi so với WPS. Không hạ hàng loạt: ribbon của mình vốn đã ít chữ hơn WPS rồi.
  3. Lệnh phụ chỉ hiện icon (ICON_ONLY), không kèm chữ.
  3b. Thêm nhịp nhóm: một vạch dọc mảnh thụt vào giữa hai nhóm, hai bên cách 6px. Gỡ tên nhóm mà không thay
     bằng gì thì cả dải chỉ còn một hàng icon không phân biệt được nhóm nào với nhóm nào. Số đo lấy theo thang
     4px và vạch ngăn mảnh của WPS (skins/2018white_dark: separator ở mức trắng 10%, thang 0/4/8/12/16/20/24/32).
  4. Gỡ thẻ "Extension" (nơi upstream dồn mọi lệnh của extension) và chuyển điểm chèn lệnh extension sang cuối thẻ
     Home, nên nút NĐ30 và công cụ tiếng Việt nằm ngay trên Home như các lệnh riêng của WPS.
Dùng: scripts/ui/ribbon.py --src <mã nguồn upstream> --app <1xVnOffice.app> [--check]
"""
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

APPS = {"swriter": "sw", "scalc": "sc", "simpress": "sd", "sdraw": "sd"}
# Hạ đúng những nút lớn đã NHÌN THẤY gây hại, không hạ hàng loạt: mỗi nút lớn bị hạ là mất một cái nhãn,
# mà ribbon của mình vốn đã ít chữ hơn WPS. Thêm vào đây sau khi xem tận mắt, không đoán.
DEMOTE_LARGE = {".uno:ToggleMergeCells"}   # "Merge and Center Cells": tên dài, kéo rộng cột, để trống giữa ribbon
GROUP_GAP = 6          # mỗi bên vạch ngăn; tổng 12px giữa hai nhóm, đúng thang 4px
SEPARATOR_INSET = 6    # vạch ngắn hơn chiều cao nhóm, nên nó mảnh chứ không cắt ngang ribbon
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
    stats = {"labels": 0, "large": 0, "icon_only": 0, "demoted": 0}
    if "labels" not in skip:
        stats["labels"] = _remove_group_labels(root)
    for obj in root.iter("object"):
        cls, oid = obj.get("class"), obj.get("id") or ""
        if cls == TOOLBOX and "style" not in skip:
            acts = _actions(obj)
            style = _prop(obj, "toolbar-style")
            if style is not None and style.text == "both" and acts and acts <= DEMOTE_LARGE:
                # Nút lớn tên dài: hạ xuống chỉ icon, lấy lại chỗ và bỏ mảng trống giữa ribbon.
                _set(obj, "toolbar-style", "icons")
                stats["demoted"] += 1
            elif acts and style is not None and style.text == "both":
                stats["large"] += 1
            elif acts and acts <= ICON_ONLY and style is not None and style.text == "both-horiz":
                _set(obj, "toolbar-style", "icons")
                stats["icon_only"] += 1
    return stats


def group_rhythm(root):
    """Đặt vạch ngăn mảnh giữa các nhóm lệnh của mỗi thẻ, và giãn hai bên theo thang 4px.

    Chạy SAU khi đã chuyển lệnh extension sang Home, để nhóm lệnh tiếng Việt cũng có vạch ngăn của nó.
    """
    added = 0
    for box in root.iter("object"):
        if box.get("class") != "sfxlo-PriorityMergedHBox":
            continue
        groups = [ch for ch in box.findall("child") if _has_content(ch.find("object"))]
        if len(groups) < 2:
            continue
        for index, slot in enumerate(groups):
            if index == 0:
                continue
            box.insert(list(box).index(slot), _separator(f"{box.get('id')}Sep{index}"))
            added += 1
        _renumber(box)
    return added


def _renumber(box):
    """Đánh lại packing/position theo đúng thứ tự trong tệp.

    Các nhóm của bản gốc mang position 0,1,2… Vạch ngăn mới chèn vào mà không có position thì VCL coi như 0 và
    dồn hết chúng về đầu dải — nhìn thấy ngay: ba bốn vạch dính nhau ở mép trái. Đánh số lại cho cả hộp là xong.
    """
    for index, slot in enumerate(box.findall("child")):
        packing = slot.find("packing")
        if packing is None:
            packing = ET.SubElement(slot, "packing")
        position = next((q for q in packing.findall("property") if q.get("name") == "position"), None)
        if position is None:
            position = ET.SubElement(packing, "property", {"name": "position"})
        position.text = str(index)


def _has_content(group):
    """Nhóm có gì để hiện không? Nhóm rỗng hoặc đang ẩn mà vẫn kèm vạch ngăn thì ribbon đầy vạch thừa."""
    if group is None:
        return False
    visible = next((p.text for p in group.findall("property") if p.get("name") == "visible"), "True")
    if visible == "False":
        return False
    return any(o.get("class") == TOOLBOX for o in group.iter("object"))


def _separator(ident):
    """Một vạch dọc mảnh, thụt trên dưới nên trông nhẹ thay vì cắt ngang cả dải ribbon."""
    slot = ET.Element("child")
    obj = ET.SubElement(slot, "object", {"class": "GtkSeparator", "id": ident})
    for name, value in (("visible", "True"), ("orientation", "vertical"),
                        ("margin-start", str(GROUP_GAP)), ("margin-end", str(GROUP_GAP)),
                        ("margin-top", str(SEPARATOR_INSET)), ("margin-bottom", str(SEPARATOR_INSET))):
        ET.SubElement(obj, "property", {"name": name}).text = value
    packing = ET.SubElement(slot, "packing")
    # KHÔNG đặt "position": VCL hiểu đó là vị trí tuyệt đối trong hộp, nên mọi vạch ngăn dồn hết về đầu dải.
    for name, value in (("expand", "False"), ("fill", "False")):
        ET.SubElement(packing, "property", {"name": name}).text = value
    return slot


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
    ap.add_argument("--skip", action="append", default=[], choices=["labels", "style", "addons", "rhythm"],
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
        separators = group_rhythm(tree.getroot()) if "rhythm" not in a.skip else 0
        if stats["labels"] == 0:
            print(f"LỖI {app}: không thấy tên nhóm nào, bố cục gốc đã đổi?")
            ok = False
        if not a.check:
            tree.write(dest, encoding="UTF-8", xml_declaration=True)
        print(f"{app}: gỡ {stats['labels']} tên nhóm, giữ {stats['large']} nút lớn, hạ {stats['demoted']} nút lớn "
              f"tên dài, {stats['icon_only']} nút chỉ icon, {separators} vạch ngăn nhóm, "
              "lệnh extension chuyển sang Home")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
