# SPDX-License-Identifier: MPL-2.0
"""Dựng nội dung văn bản hành chính theo thể thức Nghị định 30/2020/NĐ-CP (thuần Python, không cần UNO).

build(fields) trả về các khối đã định dạng sẵn (chữ, cỡ, đậm, nghiêng, căn lề) để lớp UNO (nd30_writer.py) đặt vào
Writer. Số đo và cỡ chữ lấy từ data/nd30.json, trích dẫn nguồn ở docs/legal. Trình soạn chỉ hỗ trợ trình bày; tính pháp
lý của văn bản do người ban hành chịu trách nhiệm.
"""
import datetime
import json
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent.parent / "data" / "nd30.json").read_text(encoding="utf-8"))


class Nd30Error(ValueError):
    """Thiếu hoặc sai thông tin bắt buộc."""


def doc_type(key):
    try:
        return DATA["doc_types"][key]
    except KeyError:
        raise Nd30Error(f"loại văn bản không hỗ trợ: {key}") from None


def format_number(number):
    """Số văn bản: số nhỏ hơn 10 ghi thêm số 0 phía trước."""
    n = int(number)
    if n <= 0:
        raise Nd30Error("số văn bản phải là số dương")
    return f"{n:02d}"


def format_symbol(type_key, org_abbr, unit_abbr=""):
    """Ký hiệu: <viết tắt tên loại>-<viết tắt cơ quan>; công văn: <viết tắt cơ quan>-<viết tắt đơn vị soạn thảo>."""
    org = org_abbr.strip().upper()
    if not org:
        raise Nd30Error("thiếu chữ viết tắt tên cơ quan ban hành")
    t = doc_type(type_key)
    parts = [org, unit_abbr.strip().upper()] if not t["title"] else [t["abbr"], org]
    return "-".join(p for p in parts if p)


def format_date_line(place, date):
    """"Hà Nội, ngày 05 tháng 01 năm 2026": ngày nhỏ hơn 10 và tháng 1, 2 ghi thêm số 0 phía trước."""
    place = place.strip()
    if not place:
        raise Nd30Error("thiếu địa danh")
    day = f"{date.day:02d}"
    month = f"{date.month:02d}" if date.month <= 2 else str(date.month)
    return f"{place}, ngày {day} tháng {month} năm {date.year}"


def recipients_lines(recipients, archive_unit, copies=None):
    """Danh sách nơi nhận: mỗi dòng "- ...;" và dòng cuối "- Lưu: VT, <đơn vị>[, <n>b]."."""
    lines = [f"- {r.strip().rstrip(';').strip()};" for r in recipients if r.strip()]
    tail = "VT" + (f", {archive_unit.strip()}" if archive_unit.strip() else "")
    if copies:
        tail += f", {int(copies):02d}b"
    lines.append(f"- Lưu: {tail}.")
    return lines


def build(fields):
    """fields: dict với các khoá type, parent_org, org, org_abbr, unit_abbr, number, place, date (datetime.date),
    summary (trích yếu), body (danh sách đoạn), recipient_to (Kính gửi, cho công văn), authority (TM./KT./...),
    authority_title (chức danh có thẩm quyền), signer_title (chức vụ người ký), signer_name, recipients, archive_unit,
    archive_copies. Trả về dict các khối."""
    f = dict(fields)
    t = doc_type(f.get("type", ""))
    for key in ("org", "summary", "signer_name"):
        if not str(f.get(key, "")).strip():
            raise Nd30Error(f"thiếu thông tin bắt buộc: {key}")
    s = DATA["sizes"]
    date = f.get("date") or datetime.date.today()
    number = format_number(f.get("number", 1))
    symbol = format_symbol(f["type"], f.get("org_abbr", ""), f.get("unit_abbr", ""))

    left = []
    if f.get("parent_org", "").strip():
        left.append({"text": f["parent_org"].strip().upper(), "size": s["co_quan_chu_quan"]})
    left.append({"text": f["org"].strip().upper(), "size": s["co_quan_ban_hanh"], "bold": True, "rule": "third"})
    left.append({"text": f"Số: {number}/{symbol}", "size": s["so_ky_hieu"], "space_before": 6})
    if not t["title"]:
        left.append({"text": f"V/v {f['summary'].strip()}", "size": s["vv"], "space_before": 6})

    right = [
        {"text": DATA["quoc_hieu"], "size": s["quoc_hieu"], "bold": True},
        {"text": DATA["tieu_ngu"], "size": s["tieu_ngu"], "bold": True, "rule": "full"},
        {"text": format_date_line(f.get("place", ""), date), "size": s["dia_danh_ngay"], "italic": True,
         "space_before": 6},
    ]

    title = []
    if t["title"]:
        title = [
            {"text": t["name"].upper(), "size": s["ten_loai"], "bold": True, "space_before": 12},
            {"text": f["summary"].strip(), "size": s["trich_yeu"], "bold": True, "rule": "third"},
        ]
    elif f.get("recipient_to", "").strip():
        title = [{"text": f"Kính gửi: {f['recipient_to'].strip()}", "size": s["noi_dung"], "space_before": 12}]

    body = [p.strip() for p in f.get("body", []) if p.strip()] or ["[Nội dung văn bản]"]

    authority = f.get("authority", "").strip()
    if authority and authority not in DATA["authority_prefixes"]:
        raise Nd30Error(f"quyền hạn ký không hợp lệ: {authority}")
    sign = []
    first = " ".join(x for x in (authority, f.get("authority_title", "").strip().upper()) if x)
    if first:
        sign.append({"text": first, "size": s["chuc_vu"], "bold": True})
    if f.get("signer_title", "").strip():
        sign.append({"text": f["signer_title"].strip().upper(), "size": s["chuc_vu"], "bold": True})
    sign.append({"text": "", "size": s["chuc_vu"], "blank_lines": 3})
    sign.append({"text": f["signer_name"].strip(), "size": s["ho_ten"], "bold": True})

    receivers = [{"text": "Nơi nhận:", "size": s["noi_nhan_tieu_de"], "bold": True, "italic": True}]
    receivers += [{"text": line, "size": s["noi_nhan"]}
                  for line in recipients_lines(f.get("recipients", []), f.get("archive_unit", ""),
                                               f.get("archive_copies"))]

    return {"left": left, "right": right, "title": title, "body": body, "sign": sign, "receivers": receivers,
            "page": DATA["page"], "font": DATA["font"], "body_format": DATA["body"],
            "body_size": s["noi_dung"], "page_number_size": s["so_trang"],
            "header_columns_percent": DATA["header_columns_percent"]}
