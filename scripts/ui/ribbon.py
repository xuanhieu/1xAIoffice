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
Dùng: scripts/ui/ribbon.py --src <mã nguồn upstream> --app <1xAIoffice.app> [--check]
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
    """Đánh lại packing/position theo đúng thứ tự trong tệp, bằng số ÂM.

    Hai lý do, đều đọc ra từ mã nguồn VCL (vcl/source/window/builder.cxx):

    * Dựng xong một hộp, VCL sắp lại toàn bộ con theo `m_nPosition` (`sortIntoBestTabTraversalOrder`). Vạch ngăn
      mới chèn vào mà không có position thì bị coi như 0 và dồn hết về đầu dải — ba bốn vạch dính nhau ở mép trái.
    * Con nào KHÔNG có position thì `m_nPosition` mặc định là **-1**. Các cụm lệnh của extension do
      `NotebookBarAddonsMerger::MergeNotebookBarAddons` dựng thẳng bằng C++, không đi qua packing của tệp .ui,
      nên luôn mang -1 — tức luôn đứng TRƯỚC mọi nhóm đánh số 0,1,2… Đó là lý do cụm lệnh tiếng Việt bị vẽ ở
      ngoài cùng bên trái dù đã khai ở cuối thẻ Home.

    Đánh số âm (-n-1 … -2) cho những gì mình điều khiển được thì -1 của extension thành lớn nhất, nên cụm lệnh
    tiếng Việt về đúng cuối dải. Không phải vá lõi, chỉ dùng đúng cơ chế sẵn có.
    """
    slots = box.findall("child")
    for index, slot in enumerate(slots):
        packing = slot.find("packing")
        if packing is None:
            packing = ET.SubElement(slot, "packing")
        position = next((q for q in packing.findall("property") if q.get("name") == "position"), None)
        if position is None:
            position = ET.SubElement(packing, "property", {"name": "position"})
        position.text = str(index - len(slots) - 1)


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


# ---------------------------------------------------------------- thẻ AI
# Chức năng của mình phải tự lộ ra: người dùng tìm theo thẻ trên ribbon, không đọc hướng dẫn. Nên có một thẻ riêng
# đứng ngay sau Trang chủ, nút lớn có chữ, thay vì vài icon nhỏ dồn cuối thẻ Home như trước.
T = "vnd.1x.tools:"
AI_TAB = {   # (nhóm, nút lớn?, lệnh). Nhãn lấy từ extensions/1xai-tools/GenericCommands.xcu, theo ngôn ngữ giao diện.
    "swriter": [
        ("Trợ lý AI", True, ["AiAsk", "AiRewrite", "AiSkill"]),
        ("Văn bản NĐ30", True, ["Nd30Document", "Nd30Check"]),
        ("Kết nối", True, ["McpTools", "McpServer", "AiAccounts"]),
        ("Tiếng Việt", False, ["ConvertTCVN3", "ConvertVNI", "ConvertVIQR", "NormalizeUnicode", "RemoveDiacritics",
                               "MoneyToWords"]),
    ],
    "scalc": [
        ("Trợ lý AI", True, ["AiAsk", "AiSkill"]),
        ("Kết nối", True, ["McpTools", "McpServer", "AiAccounts"]),
        ("Dữ liệu tiếng Việt", False, ["OpenCsvSafely", "NumberToWords", "MoneyToWords", "RemoveDiacritics",
                                       "ConvertTCVN3", "NormalizeUnicode"]),
    ],
}


def _el(tag, parent=None, **attrs):
    node = ET.Element(tag, attrs) if parent is None else ET.SubElement(parent, tag, attrs)
    return node


def _props(obj, **values):
    for name, value in values.items():
        _el("property", obj, name=name.replace("_", "-")).text = str(value)


def _ai_group(gid, items, large, position):
    """Một nhóm: hộp chứa một thanh công cụ. Nút lớn thì icon trên chữ dưới; nhóm nhỏ thì hai hàng icon cạnh chữ."""
    child = _el("child")
    box = _el("object", child, **{"class": "GtkBox", "id": f"box1xAI{gid}"})
    _props(box, visible="True", can_focus="False", margin_start=GROUP_GAP, margin_end=GROUP_GAP,
           margin_top=6, margin_bottom=6, spacing=2)
    rows = [items] if large else [items[i::2] for i in range(2)]
    if not large:
        _props(box, orientation="vertical")
    for r, row in enumerate(rows):
        holder = _el("child", box)
        bar = _el("object", holder, **{"class": TOOLBOX, "id": f"tb1xAI{gid}{r}"})
        _props(bar, visible="True", can_focus="False", show_arrow="False",
               toolbar_style="both" if large else "both-horiz")
        if large:
            _props(bar, icon_size=3, valign="center", vexpand="True")
        for i, name in enumerate(row):
            item = _el("child", bar)
            btn = _el("object", item, **{"class": "GtkToolButton", "id": f"bt1xAI{gid}{r}{i}"})
            # Lõi không tự tìm icon cho lệnh extension trên ribbon, nên chỉ thẳng tệp trong icon theme "1x"
            # (scripts/brand/make-brand.py ghi cmd/lc_<lệnh>.svg và cmd/sc_<lệnh>.svg, tên viết thường).
            icon = f"cmd/{'lc' if large else 'sc'}_{name.lower()}.png"
            _props(btn, visible="True", can_focus="False", action_name=T + name, icon_name=icon)
            _props(_el("packing", item), expand="False", homogeneous="False")
        _props(_el("packing", holder), expand="False", fill="True", position=r)
    _props(_el("packing", child), expand="False", fill="True", position=position)
    return child


def add_ai_tab(root, app):
    """Chèn trang "AI" và nhãn của nó ngay sau thẻ Trang chủ. Không có bố cục cho ứng dụng này thì bỏ qua."""
    groups = AI_TAB.get(app)
    if not groups:
        return 0
    parent = {c: p for p in root.iter() for c in p}
    label = next((o for o in root.iter("object") if o.get("id") == "HomeLabel"), None)
    if label is None:
        raise SystemExit(f"LỖI ribbon {app}: không thấy nhãn thẻ Home để đặt thẻ AI sau nó")
    tab_child = parent[label]
    notebook = parent[tab_child]
    page_child = _el("child")
    page = _el("object", page_child, **{"class": "sfxlo-PriorityHBox", "id": "1xAI Tab"})
    _props(page, visible="True", can_focus="False", valign="center", vexpand="True")
    holder = _el("child", page)
    merged = _el("object", holder, **{"class": "sfxlo-PriorityMergedHBox", "id": "pmhb1xAI"})
    _props(merged, visible="True", can_focus="False")
    for n, (_title, large, items) in enumerate(groups):   # vạch ngăn và vị trí do group_rhythm đặt sau
        merged.append(_ai_group(n, items, large, n))
    # PHẢI giãn như hộp của thẻ Home: không giãn thì hộp rộng bằng 0 và PriorityMergedHBox đẩy hết nhóm vào "»".
    _props(_el("packing", holder), expand="True", fill="True", position=0)
    tab = _el("child", type="tab")
    text = _el("object", tab, **{"class": "GtkLabel", "id": "1xAILabel"})
    _props(text, visible="True", can_focus="False", label="AI", use_underline="False")
    style = _el("style", text)
    # Chỉ "context-any" (luôn hiện), KHÔNG "context-default": khi ngữ cảnh mở đầu không khớp thẻ nào (ô của Calc),
    # vcl (NotebookbarTabControlBase::SetContext) chọn thẻ default CUỐI CÙNG, và thẻ AI đứng sau Home sẽ giành mất,
    # tức là ép người dùng vào AI ngay khi mở bảng tính.
    _el("class", style, name="context-any")
    _props(_el("packing", tab), tab_fill="False")
    kids = list(notebook)
    at = kids.index(tab_child) + 1
    notebook.insert(at, page_child)
    notebook.insert(at + 1, tab)
    # Đánh lại vị trí trang/nhãn theo đúng thứ tự trong tệp, để thẻ AI đứng sau Home chứ không bị xếp lại.
    pages = [c for c in notebook if c.tag == "child" and c.get("type") != "tab"]
    labels = [c for c in notebook if c.tag == "child" and c.get("type") == "tab"]
    for group in (pages, labels):
        for i, c in enumerate(group):
            pack = c.find("packing")
            if pack is None:
                pack = _el("packing", c)
            pos = next((x for x in pack.findall("property") if x.get("name") == "position"), None)
            if pos is None:
                pos = _el("property", pack, name="position")
            pos.text = str(i)
    return sum(len(items) for _, _, items in groups)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--app", required=True)
    ap.add_argument("--check", action="store_true", help="chỉ kiểm, không ghi")
    ap.add_argument("--skip", action="append", default=[], choices=["labels", "style", "addons", "rhythm", "ai"],
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
        ai_buttons = add_ai_tab(tree.getroot(), app) if "ai" not in a.skip else 0
        separators = group_rhythm(tree.getroot()) if "rhythm" not in a.skip else 0
        if stats["labels"] == 0:
            print(f"LỖI {app}: không thấy tên nhóm nào, bố cục gốc đã đổi?")
            ok = False
        if not a.check:
            tree.write(dest, encoding="UTF-8", xml_declaration=True)
        print(f"{app}: gỡ {stats['labels']} tên nhóm, giữ {stats['large']} nút lớn, hạ {stats['demoted']} nút lớn "
              f"tên dài, {stats['icon_only']} nút chỉ icon, {separators} vạch ngăn nhóm, "
              f"lệnh extension chuyển sang Home, thẻ AI {ai_buttons} nút")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
