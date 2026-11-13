# SPDX-License-Identifier: MPL-2.0
"""Hộp thoại nhập thông tin văn bản hành chính NĐ30 (dựng bằng mã, không cần file .xdl). Trả về dict cho nd30.build()
hoặc None khi người dùng huỷ."""
import datetime

import uno

from .nd30 import DATA

FIELDS = [  # (khoá, nhãn en, nhãn vi, kiểu, chiều cao dòng)
    ("type", "Document type", "Loại văn bản", "list", 1),
    ("parent_org", "Parent organization", "Cơ quan chủ quản", "text", 1),
    ("org", "Issuing organization *", "Cơ quan ban hành *", "text", 1),
    ("org_abbr", "Organization abbreviation *", "Viết tắt cơ quan *", "text", 1),
    ("unit_abbr", "Drafting unit (letters)", "Viết tắt đơn vị soạn thảo", "text", 1),
    ("number", "Number", "Số", "text", 1),
    ("place", "Place *", "Địa danh *", "text", 1),
    ("date", "Date (dd/mm/yyyy)", "Ngày (dd/mm/yyyy)", "text", 1),
    ("summary", "Subject *", "Trích yếu *", "text", 1),
    ("recipient_to", "To (letters)", "Kính gửi (công văn)", "text", 1),
    ("authority", "Signing authority", "Quyền hạn ký", "list", 1),
    ("authority_title", "Head's title", "Chức danh thủ trưởng", "text", 1),
    ("signer_title", "Signer's title", "Chức vụ người ký", "text", 1),
    ("signer_name", "Signer's name *", "Họ tên người ký *", "text", 1),
    ("recipients", "Recipients (one per line)", "Nơi nhận (mỗi dòng một nơi)", "multi", 3),
    ("archive_unit", "Archive unit", "Đơn vị lưu", "text", 1),
]


def _parse_date(text):
    d, m, y = (int(x) for x in text.strip().split("/"))
    return datetime.date(y, m, d)


def run(ctx, parent_window, lang="en"):
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    row_h, label_w, field_w, x0, y = 14, 105, 190, 8, 8
    model.Width, model.Title = x0 * 3 + label_w + field_w, ("Văn bản hành chính NĐ30" if lang == "vi" else
                                                            "Administrative document (Decree 30)")
    types = list(DATA["doc_types"].items())
    defaults = {"number": "1", "date": datetime.date.today().strftime("%d/%m/%Y"), "place": "Hà Nội",
                "recipients": "Như trên", "archive_unit": "VT"}
    for key, en, vi, kind, lines in FIELDS:
        lab = model.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
        lab.PositionX, lab.PositionY, lab.Width, lab.Height = x0, y + 2, label_w, 10
        lab.Label = vi if lang == "vi" else en
        model.insertByName("lbl_" + key, lab)
        if kind == "list":
            ctl = model.createInstance("com.sun.star.awt.UnoControlListBoxModel")
            ctl.Dropdown = True
            items = [v["name"] for _, v in types] if key == "type" else [a or "—" for a in DATA["authority_prefixes"]]
            ctl.StringItemList = tuple(items)
            ctl.SelectedItems = (1 if key == "type" else 0,)
        else:
            ctl = model.createInstance("com.sun.star.awt.UnoControlEditModel")
            ctl.MultiLine = kind == "multi"
            ctl.Text = defaults.get(key, "")
        ctl.PositionX, ctl.PositionY, ctl.Width, ctl.Height = x0 * 2 + label_w, y, field_w, row_h * lines - 2
        model.insertByName(key, ctl)
        y += row_h * lines
    for name, label, kind, pos in (("ok", "OK", 1, 0), ("cancel", "Huỷ" if lang == "vi" else "Cancel", 2, 1)):
        btn = model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        btn.PositionX, btn.PositionY, btn.Width, btn.Height = model.Width - (pos + 1) * 60, y + 6, 52, 14
        btn.Label, btn.PushButtonType, btn.DefaultButton = label, kind, kind == 1
        model.insertByName(name, btn)
    model.Height = y + 28

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.createPeer(toolkit, parent_window)
    try:
        if dialog.execute() != 1:
            return None
        out = {}
        for key, _, _, kind, _ in FIELDS:
            ctl = dialog.getControl(key)
            if kind == "list":
                idx = ctl.getSelectedItemPos()
                out[key] = types[idx][0] if key == "type" else DATA["authority_prefixes"][max(idx, 0)]
            else:
                out[key] = ctl.getText()
        out["number"] = int(out["number"] or 1)
        out["date"] = _parse_date(out["date"]) if out["date"].strip() else datetime.date.today()
        out["recipients"] = [r for r in out["recipients"].splitlines() if r.strip()]
        return out
    finally:
        dialog.dispose()
