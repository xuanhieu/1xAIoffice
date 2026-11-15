#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Đưa lệnh AI, NĐ30 và tiếng Việt vào menu chuột phải của Writer và Calc.

Người dùng tìm chức năng ở chỗ họ đang trỏ chuột: bôi đen một đoạn rồi bấm chuột phải. Trước đây các lệnh này chỉ có
trong menu Công cụ, nên gần như không ai thấy. Script đọc bản menu gốc trong mã nguồn (không đọc bản đã sửa trong app,
nên chạy lại bao nhiêu lần cũng ra cùng một kết quả), chèn một cụm lệnh lên đầu, rồi ghi vào app đã dựng.

Dùng: scripts/ui/menus.py --src <thư mục mã nguồn LibreOffice> --app <.app> [--check]
"""
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://openoffice.org/2001/menu"
ET.register_namespace("menu", NS)
T = "vnd.1x.tools:"

# (ứng dụng, tệp menu, lệnh đứng ngay trước chỗ chèn hoặc None để chèn lên đầu, các mục)
# Mục là lệnh, hoặc None cho vạch ngăn. Nhãn lõi tự lấy từ extensions/1xai-tools/GenericCommands.xcu (PopupLabel).
MENUS = [
    ("swriter", "text.xml", ".uno:NoBreak", [
        T + "AiAsk",
        T + "AiRewrite",
        T + "AiSkill",
        T + "Nd30Check",
        None,
    ]),
    ("scalc", "cell.xml", None, [
        T + "AiAsk",
        T + "AiSkill",
        None,
        T + "NumberToWords",
        T + "MoneyToWords",
        T + "RemoveDiacritics",
        None,
    ]),
]


def _q(tag):
    return f"{{{NS}}}{tag}"


def insert(root, after, items):
    """Chèn các mục vào menu gốc; trả về số lệnh đã chèn. Đã có rồi thì không chèn lần nữa."""
    if any(el.get(_q("id"), "").startswith(T) for el in root.iter()):
        return 0
    kids = list(root)
    at = 0
    if after:
        anchor = next((i for i, el in enumerate(kids) if el.get(_q("id")) == after), None)
        if anchor is None:
            raise SystemExit(f"LỖI menu: không thấy {after} trong menu gốc (bố cục gốc đã đổi?)")
        at = anchor + 1
        if at < len(kids) and kids[at].tag == _q("menuseparator"):
            at += 1                     # chèn SAU vạch ngăn đi kèm mục neo, để cụm của mình đứng thành nhóm riêng
    nodes = []
    for item in items:
        if item is None:
            nodes.append(ET.Element(_q("menuseparator")))
        else:
            nodes.append(ET.Element(_q("menuitem"), {_q("id"): item}))
    for offset, node in enumerate(nodes):
        root.insert(at + offset, node)
    return sum(1 for item in items if item)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--app", required=True)
    ap.add_argument("--check", action="store_true", help="chỉ kiểm, không ghi")
    a = ap.parse_args()
    modules = {"swriter": "sw", "scalc": "sc"}
    ok = True
    for app, name, after, items in MENUS:
        src = Path(a.src) / modules[app] / "uiconfig" / app / "popupmenu" / name
        dest = Path(a.app) / "Contents/Resources/config/soffice.cfg/modules" / app / "popupmenu" / name
        if not src.is_file() or not dest.parent.is_dir():
            print(f"BỎ QUA {app}/{name}: thiếu {src if not src.is_file() else dest.parent}")
            ok = False
            continue
        tree = ET.parse(src)
        count = insert(tree.getroot(), after, items)
        if not a.check:
            tree.write(dest, encoding="UTF-8", xml_declaration=True)
        print(f"{app}/{name}: thêm {count} lệnh vào đầu menu chuột phải")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
