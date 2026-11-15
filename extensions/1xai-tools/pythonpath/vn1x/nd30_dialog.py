# SPDX-License-Identifier: MPL-2.0
"""Hộp thoại nhập thông tin văn bản hành chính NĐ30 (dựng bằng mã, không cần file .xdl). Trả về dict cho nd30.build()
hoặc None khi người dùng huỷ.

Nút OK kiểm tra dữ liệu ngay trong hộp thoại: thiếu hoặc sai thì báo lỗi, đưa con trỏ về đúng ô và giữ hộp thoại mở,
để người dùng không mất những gì đã gõ. validate() không cần UNO nên kiểm thử được bằng unittest.
"""
import datetime

from .nd30 import DATA, Nd30Error, build

FIELDS = [  # (khoá, nhãn en, nhãn vi, kiểu, số dòng)
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
    ("body", "Body (one paragraph per line)", "Nội dung (mỗi dòng một đoạn)", "multi", 4),
    ("authority", "Signing authority", "Quyền hạn ký", "list", 1),
    ("authority_title", "Head's title", "Chức danh thủ trưởng", "text", 1),
    ("signer_title", "Signer's title", "Chức vụ người ký", "text", 1),
    ("signer_name", "Signer's name *", "Họ tên người ký *", "text", 1),
    ("cosigner_name", "Co-signer (minutes, two-party documents)", "Người ký thứ hai (biên bản, văn bản hai bên)", "text", 1),
    ("recipients", "Recipients (one per line)", "Nơi nhận (mỗi dòng một nơi)", "multi", 3),
    ("archive_unit", "Archive unit", "Đơn vị lưu", "text", 1),
]
REQUIRED = ("org", "org_abbr", "place", "summary", "signer_name")
TEXTS = {
    "en": {"title": "Administrative document (Decree 30)", "cancel": "Cancel", "missing": "Please fill in: {label}",
           "number": "The number must be a positive whole number.",
           "date": "The date must be a real date written dd/mm/yyyy, for example 05/01/2026.",
           "invalid": "Cannot create the document: {err}"},
    "vi": {"title": "Văn bản hành chính NĐ30", "cancel": "Huỷ", "missing": "Vui lòng nhập: {label}",
           "number": "Số văn bản phải là số nguyên dương.",
           "date": "Ngày phải là ngày có thật, viết dd/mm/yyyy, ví dụ 05/01/2026.",
           "invalid": "Không tạo được văn bản: {err}"},
}


def _label(key, lang):
    for k, en, vi, _, _ in FIELDS:
        if k == key:
            return (vi if lang == "vi" else en).rstrip(" *")
    return key


def parse_date(text):
    d, m, y = (int(x) for x in text.strip().split("/"))
    return datetime.date(y, m, d)


def validate(raw, lang="en", today=None):
    """raw: chữ người dùng nhập (khoá như FIELDS; type/authority đã là khoá trong nd30.json).
    Trả về (fields, None) khi hợp lệ, hoặc (None, (khoá ô cần sửa, thông báo))."""
    t = TEXTS["vi" if lang == "vi" else "en"]
    for key in REQUIRED:
        if not str(raw.get(key, "")).strip():
            return None, (key, t["missing"].format(label=_label(key, lang)))
    out = dict(raw)
    try:
        out["number"] = int(str(raw.get("number", "")).strip() or 1)
        if out["number"] <= 0:
            raise ValueError
    except ValueError:
        return None, ("number", t["number"])
    try:
        text = str(raw.get("date", "")).strip()
        out["date"] = parse_date(text) if text else (today or datetime.date.today())
    except ValueError:
        return None, ("date", t["date"])
    out["body"] = [p for p in str(raw.get("body", "")).splitlines() if p.strip()]
    out["recipients"] = [r for r in str(raw.get("recipients", "")).splitlines() if r.strip()]
    try:
        build(out)
    except Nd30Error as exc:
        return None, ("type", t["invalid"].format(err=exc))
    return out, None


DEFAULT_TYPE = "cong_van"   # loại văn bản dùng nhiều nhất; chọn theo MÃ, không theo vị trí trong danh sách


def default_type_index(types, wanted=None):
    """Vị trí của loại văn bản chọn sẵn (mặc định Công văn) trong danh sách; 0 nếu bảng không có, để hộp thoại vẫn
    mở được. `wanted` là mã loại khi người dùng bấm một thẻ mẫu cụ thể trên Start Center."""
    for code in (wanted, DEFAULT_TYPE):
        found = next((i for i, (c, _) in enumerate(types) if c == code), None)
        if found is not None:
            return found
    return 0

def run(ctx, parent_window, lang="en", doc_type=None):
    import uno  # noqa: F401  (khởi tạo cầu nối UNO trước khi dùng unohelper)
    import unohelper
    from com.sun.star.awt import XActionListener

    t = TEXTS["vi" if lang == "vi" else "en"]
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    row_h, label_w, field_w, x0, y = 14, 105, 190, 8, 8
    model.Width, model.Title = x0 * 3 + label_w + field_w, t["title"]
    types = list(DATA["doc_types"].items())
    prefixes = DATA["authority_prefixes"]
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
            items = [v["name"] for _, v in types] if key == "type" else [a or "—" for a in prefixes]
            ctl.StringItemList = tuple(items)
            ctl.SelectedItems = (default_type_index(types, doc_type) if key == "type" else 0,)
        else:
            ctl = model.createInstance("com.sun.star.awt.UnoControlEditModel")
            ctl.MultiLine = kind == "multi"
            if kind == "multi":
                ctl.VScroll = True
            ctl.Text = defaults.get(key, "")
        ctl.PositionX, ctl.PositionY, ctl.Width, ctl.Height = x0 * 2 + label_w, y, field_w, row_h * lines - 2
        model.insertByName(key, ctl)
        y += row_h * lines
    for name, label, kind, pos in (("ok", "OK", 0, 0), ("cancel", t["cancel"], 2, 1)):
        btn = model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        btn.PositionX, btn.PositionY, btn.Width, btn.Height = model.Width - (pos + 1) * 60, y + 6, 52, 14
        # OK là nút thường (STANDARD) để kiểm tra trước khi đóng; Huỷ đóng ngay (CANCEL).
        btn.Label, btn.PushButtonType, btn.DefaultButton = label, kind, name == "ok"
        model.insertByName(name, btn)
    model.Height = y + 28

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.createPeer(toolkit, parent_window)
    result = {}

    def read():
        raw = {}
        for key, _, _, kind, _ in FIELDS:
            ctl = dialog.getControl(key)
            if kind == "list":
                idx = max(ctl.getSelectedItemPos(), 0)
                raw[key] = types[idx][0] if key == "type" else prefixes[idx]
            else:
                raw[key] = ctl.getText()
        return raw

    class OkListener(unohelper.Base, XActionListener):
        def actionPerformed(self, event):
            fields, problem = validate(read(), lang)
            if problem:
                key, text = problem
                from com.sun.star.awt.MessageBoxType import WARNINGBOX
                box = toolkit.createMessageBox(dialog.getPeer(), WARNINGBOX, 1, t["title"], text)
                box.execute()
                box.dispose()
                dialog.getControl(key).setFocus()
                return
            result["fields"] = fields
            dialog.endExecute()

        def disposing(self, event):
            pass

    dialog.getControl("ok").addActionListener(OkListener())
    try:
        dialog.execute()
        return result.get("fields")
    finally:
        dialog.dispose()
