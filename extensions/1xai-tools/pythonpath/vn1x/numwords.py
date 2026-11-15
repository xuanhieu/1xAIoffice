# SPDX-License-Identifier: MPL-2.0
"""Đọc số thành chữ tiếng Việt (thuần Python, không cần UNO).

Quy ước mặc định theo cách đọc trong văn bản kế toán, hành chính:
  21 -> "hai mươi mốt", 25 -> "hai mươi lăm", 15 -> "mười lăm", 105 -> "một trăm lẻ năm",
  1.000.001 -> "một triệu không trăm lẻ một" (nhóm toàn số 0 được bỏ qua), 24 -> "hai mươi bốn".
Tuỳ chọn: le="linh" (105 -> "một trăm linh năm"), tu=True (24 -> "hai mươi tư"), nghin="ngàn".
Số có tối đa 18 chữ số phần nguyên; quá giới hạn thì báo lỗi thay vì đọc sai.
"""
from decimal import Decimal, InvalidOperation

DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
MAX_INTEGER_DIGITS = 18


class NumberWordsError(ValueError):
    """Giá trị không đọc được (không phải số, quá lớn)."""


def _group_units(nghin):
    # Đơn vị theo nhóm 3 chữ số, từ phải sang trái.
    return ["", nghin, "triệu", "tỷ", f"{nghin} tỷ", "triệu tỷ"]


def _read_three(n, full, le, tu):
    """Đọc một nhóm 0..999. full=True: đọc đủ "không trăm" khi đứng sau một nhóm lớn hơn."""
    tram, chuc, dv = n // 100, (n // 10) % 10, n % 10
    words = []
    if full or tram:
        words += [DIGITS[tram], "trăm"]
    if chuc == 0:
        if dv and words:
            words.append(le)
    elif chuc == 1:
        words.append("mười")
    else:
        words += [DIGITS[chuc], "mươi"]
    if dv:
        if dv == 1 and chuc >= 2:
            words.append("mốt")
        elif dv == 5 and chuc >= 1:
            words.append("lăm")
        elif dv == 4 and chuc >= 2 and tu:
            words.append("tư")
        else:
            words.append(DIGITS[dv])
    return words


def integer_to_words(n, le="lẻ", tu=False, nghin="nghìn"):
    if n < 0:
        return "âm " + integer_to_words(-n, le, tu, nghin)
    if n == 0:
        return DIGITS[0]
    if len(str(n)) > MAX_INTEGER_DIGITS:
        raise NumberWordsError(f"số quá lớn (tối đa {MAX_INTEGER_DIGITS} chữ số)")
    units = _group_units(nghin)
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    words = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        words += _read_three(g, full=bool(words), le=le, tu=tu)
        if units[i]:
            words.append(units[i])
    return " ".join(words)


def _to_decimal(value):
    if isinstance(value, bool):
        raise NumberWordsError("không phải số")
    try:
        d = Decimal(str(value).strip().replace(" ", ""))
    except (InvalidOperation, ValueError):
        raise NumberWordsError(f"không phải số: {value!r}") from None
    if not d.is_finite():
        raise NumberWordsError("không phải số hữu hạn")
    return d


def parse_number_text(text):
    """Đọc chuỗi số người dùng gõ trong văn bản: "1.250.000", "1.250.000,5" (kiểu Việt), "1,250,000.5" (kiểu Anh),
    "3,5", "12 500", "-7". Trả về chuỗi số dạng chuẩn (dấu chấm thập phân) hoặc báo NumberWordsError."""
    s = (text or "").strip().replace(" ", "").replace(" ", "")
    s = s.rstrip("đ₫").rstrip()
    if not s or not any(c.isdigit() for c in s):
        raise NumberWordsError(f"không phải số: {text!r}")
    dots, commas = s.count("."), s.count(",")
    if dots and commas:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        grp = "." if dec == "," else ","
        s = s.replace(grp, "").replace(dec, ".")
    elif dots or commas:
        sep = "." if dots else ","
        parts = s.lstrip("+-").split(sep)
        # Nhiều dấu, hoặc đúng 3 chữ số sau dấu duy nhất: dấu nhóm nghìn. Còn lại: dấu thập phân.
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and parts[0] not in ("", "0")):
            s = s.replace(sep, "")
        else:
            s = s.replace(sep, ".")
    _to_decimal(s)
    return s


def number_to_words(value, le="lẻ", tu=False, nghin="nghìn", capitalize=False):
    """Đọc một số (int, float, Decimal hoặc chuỗi dùng dấu chấm thập phân), kể cả phần thập phân ("phẩy")."""
    d = _to_decimal(value)
    sign = "âm " if d < 0 else ""
    d = abs(d)
    text = format(d, "f")
    whole, _, frac = text.partition(".")
    frac = frac.rstrip("0")
    words = integer_to_words(int(whole), le, tu, nghin)
    if frac:
        # Phần thập phân: các số 0 ở đầu đọc từng chữ "không", phần còn lại đọc như một số.
        lead = len(frac) - len(frac.lstrip("0"))
        rest = frac.lstrip("0")
        tail = " ".join([DIGITS[0]] * lead + ([integer_to_words(int(rest), le, tu, nghin)] if rest else []))
        words += " phẩy " + tail
    words = sign + words
    return words[:1].upper() + words[1:] if capitalize else words


def money_to_words(value, currency="đồng", le="lẻ", tu=False, nghin="nghìn", even_suffix=""):
    """Đọc số tiền: "Một triệu hai trăm nghìn đồng". Số lẻ được làm tròn tới đơn vị tiền; even_suffix (vd "chẵn")
    được thêm khi số tiền tròn nghìn."""
    d = _to_decimal(value).quantize(Decimal(1))
    words = integer_to_words(int(d), le, tu, nghin) + f" {currency}"
    if even_suffix and int(d) % 1000 == 0 and int(d) != 0:
        words += f" {even_suffix}"
    return words[:1].upper() + words[1:]
