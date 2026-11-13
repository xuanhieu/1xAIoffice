# SPDX-License-Identifier: MPL-2.0
"""Xử lý chữ tiếng Việt (thuần Python): bỏ dấu, chuẩn hóa Unicode, chuyển mã TCVN3 (ABC) sang Unicode."""
import json
import unicodedata
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent.parent / "data"
_TCVN3 = None


def _tcvn3_table():
    global _TCVN3
    if _TCVN3 is None:
        _TCVN3 = json.loads((_DATA / "tcvn3.json").read_text(encoding="utf-8"))
    return _TCVN3


def remove_diacritics(text):
    """"Đường Lê Lợi" -> "Duong Le Loi". Giữ nguyên mọi ký tự không phải chữ có dấu."""
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", stripped.replace("đ", "d").replace("Đ", "D"))


def normalize(text):
    """Chuẩn hóa về Unicode dựng sẵn (NFC): chữ dán từ web hay PDF thường ở dạng tổ hợp (NFD), làm sai tìm kiếm,
    sắp xếp và kiểm tra chính tả."""
    return unicodedata.normalize("NFC", text)


def tcvn3_to_unicode(text, upper=False):
    """Chuyển chữ gõ bằng phông TCVN3 (.VnTime…) sang Unicode. Trả về (chuỗi mới, số ký tự đã đổi).

    Ký tự ngoài bảng (ASCII, chữ đã là Unicode) giữ nguyên. upper=True cho chữ của phông chữ hoa (.VnTimeH…), vốn
    đặt chữ hoa có dấu vào vị trí của chữ thường."""
    table = _tcvn3_table()
    out, changed = [], 0
    for ch in text:
        uni = table.get(ch)
        if uni is None:
            out.append(ch.upper() if upper else ch)
        else:
            out.append(uni.upper() if upper else uni)
            changed += 1
    return "".join(out), changed


def looks_like_tcvn3(text, threshold=0.05):
    """Ước lượng chữ có phải TCVN3 không: tỉ lệ ký tự thuộc bảng TCVN3 mà không phải chữ tiếng Việt Unicode."""
    if not text:
        return False
    table = _tcvn3_table()
    letters = [c for c in text if not c.isspace()]
    hits = sum(1 for c in letters if c in table and c not in table.values())
    return bool(letters) and hits / len(letters) >= threshold
