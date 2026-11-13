# SPDX-License-Identifier: MPL-2.0
"""Kiểm thể thức một văn bản đã có theo Nghị định 30/2020/NĐ-CP (thuần Python, không cần UNO).

Nhận một bản mô tả tài liệu do lớp UNO đọc ra (nd30_check_writer.py) và trả về danh sách lỗi. Chỉ kiểm những điều đo
được chắc chắn: khổ giấy, lề, phông chữ, cỡ chữ, cách căn lề, và sự có mặt của Quốc hiệu, Tiêu ngữ, Nơi nhận. Không
kết luận về nội dung hay giá trị pháp lý: phần đó thuộc người ban hành.

Mỗi lỗi có `fix` = True khi công cụ sửa tự động được (hiện mới làm phần trang: khổ giấy, lề, phông mặc định).
"""
from .nd30 import DATA

R = DATA["ranges"]
A4_MM = (DATA["page"]["width_mm"], DATA["page"]["height_mm"])
TOLERANCE_MM = 1.0


class Issue:
    """Một điểm chưa đúng thể thức."""

    def __init__(self, key, message, fix=False, where=""):
        self.key, self.message, self.fix, self.where = key, message, fix, where

    def __repr__(self):
        return f"Issue({self.key!r}, {self.message!r}, fix={self.fix})"

    def __eq__(self, other):
        return (self.key, self.message, self.fix, self.where) == (other.key, other.message, other.fix, other.where)


def _in_range(value, name):
    low, high = R[name]
    return low - 1e-9 <= value <= high + 1e-9


def _mm(value):
    return f"{value:.0f}".rstrip("0").rstrip(".") if float(value).is_integer() else f"{value:.1f}"


def check_page(page):
    """page: {width_mm, height_mm, margin_*_mm, font}."""
    out = []
    if abs(page["width_mm"] - A4_MM[0]) > TOLERANCE_MM or abs(page["height_mm"] - A4_MM[1]) > TOLERANCE_MM:
        out.append(Issue("page_size", f"Khổ giấy {_mm(page['width_mm'])}×{_mm(page['height_mm'])} mm, "
                                      f"NĐ30 yêu cầu A4 ({A4_MM[0]}×{A4_MM[1]} mm).", fix=True))
    sides = (("margin_top_mm", "Lề trên"), ("margin_bottom_mm", "Lề dưới"),
             ("margin_left_mm", "Lề trái"), ("margin_right_mm", "Lề phải"))
    for key, label in sides:
        value = page.get(key)
        if value is None:
            continue
        if not _in_range(value, key):
            low, high = R[key]
            out.append(Issue(key, f"{label} {_mm(value)} mm, NĐ30 cho phép {_mm(low)}–{_mm(high)} mm.", fix=True))
    font = (page.get("font") or "").strip()
    if font and font.casefold() != DATA["font"].casefold():
        out.append(Issue("font", f"Phông mặc định là “{font}”, NĐ30 yêu cầu {DATA['font']}.", fix=True))
    return out


def check_body(paragraphs):
    """paragraphs: [{text, size, font, adjust, indent_mm}] của phần nội dung (đã bỏ phần đầu và chữ ký)."""
    out = []
    body = [p for p in paragraphs if (p.get("text") or "").strip()]
    if not body:
        return out
    sizes = sorted({round(float(p["size"]), 1) for p in body if p.get("size")})
    wrong = [s for s in sizes if not _in_range(s, "noi_dung")]
    if wrong:
        low, high = R["noi_dung"]
        out.append(Issue("body_size", f"Cỡ chữ nội dung {', '.join(_mm(s) for s in wrong)} pt, "
                                      f"NĐ30 yêu cầu {_mm(low)}–{_mm(high)} pt.", where="nội dung"))
    fonts = {(p.get("font") or "").strip() for p in body if p.get("font")}
    other = sorted(f for f in fonts if f and f.casefold() != DATA["font"].casefold())
    if other:
        out.append(Issue("body_font", f"Nội dung dùng phông {', '.join(other)}; NĐ30 yêu cầu {DATA['font']}.",
                         where="nội dung"))
    not_justified = sum(1 for p in body if p.get("adjust") is not None and p["adjust"] != 2)
    if not_justified and not_justified > len(body) // 2:
        out.append(Issue("body_adjust", "Phần lớn đoạn nội dung chưa canh đều hai bên.", where="nội dung"))
    indents = [p["indent_mm"] for p in body if p.get("indent_mm") is not None]
    if indents and not any(_in_range(i, "first_line_indent_mm") for i in indents):
        low, high = R["first_line_indent_mm"]
        out.append(Issue("body_indent", f"Chưa thấy đoạn nào lùi đầu dòng {_mm(low)}–{_mm(high)} mm.",
                         where="nội dung"))
    return out


def check_parts(texts):
    """texts: danh sách chữ của mọi đoạn trong văn bản (kể cả trong bảng), để tìm các phần bắt buộc."""
    joined = " ".join(" ".join((t or "").split()) for t in texts).casefold()
    out = []
    for key, needed, label in (("quoc_hieu", DATA["quoc_hieu"], "Quốc hiệu"),
                               ("tieu_ngu", DATA["tieu_ngu"], "Tiêu ngữ"),
                               ("noi_nhan", "Nơi nhận:", "mục “Nơi nhận:”")):
        if " ".join(needed.split()).casefold() not in joined:
            out.append(Issue(key, f"Không thấy {label} (“{needed}”)."))
    return out


def check(doc):
    """doc: {page, body, texts}. Trả về danh sách Issue, rỗng nghĩa là không thấy lỗi đo được."""
    return check_page(doc["page"]) + check_parts(doc.get("texts", [])) + check_body(doc.get("body", []))


def page_fix():
    """Giá trị trang đúng chuẩn để sửa tự động."""
    page = DATA["page"]
    return {"width_mm": page["width_mm"], "height_mm": page["height_mm"],
            "margin_top_mm": page["margin_top_mm"], "margin_bottom_mm": page["margin_bottom_mm"],
            "margin_left_mm": page["margin_left_mm"], "margin_right_mm": page["margin_right_mm"],
            "font": DATA["font"]}
