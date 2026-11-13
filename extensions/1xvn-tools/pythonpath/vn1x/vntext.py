# SPDX-License-Identifier: MPL-2.0
"""Xử lý chữ tiếng Việt (thuần Python): bỏ dấu, chuẩn hóa Unicode, chuyển mã TCVN3 (ABC)
và chuyển kiểu gõ VNI, VIQR sang Unicode."""
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


# --- Kiểu gõ VNI và VIQR ---
# Dấu thanh và dấu phụ viết bằng ký tự tổ hợp Unicode rồi dựng sẵn bằng NFC.
_ACUTE, _GRAVE, _HOOK, _TILDE, _DOT = "\u0301", "\u0300", "\u0309", "\u0303", "\u0323"
_CIRCUMFLEX, _BREVE, _HORN = "\u0302", "\u0306", "\u031b"
_VOWELS = "aeiouyAEIOUY"
_MODIFIED = "\u00e2\u00ea\u00f4\u01a1\u01b0\u0103\u00c2\u00ca\u00d4\u01a0\u01af\u0102"  # â ê ô ơ ư ă hoa thường

VNI = {"tones": {"1": _ACUTE, "2": _GRAVE, "3": _HOOK, "4": _TILDE, "5": _DOT},
       "marks": {"6": _CIRCUMFLEX, "7": _HORN, "8": _BREVE},
       "stroke": "9"}
VIQR = {"tones": {"'": _ACUTE, "`": _GRAVE, "?": _HOOK, "~": _TILDE, ".": _DOT},
        "marks": {"^": _CIRCUMFLEX, "+": _HORN, "(": _BREVE},
        "stroke": "d"}
_MARK_FITS = {_CIRCUMFLEX: "aeoAEO", _HORN: "ouOU", _BREVE: "aA"}  # dấu phụ chỉ đi với đúng nguyên âm của nó


def _convert_typing(text, rules):
    """Dựng chữ có dấu từ kiểu gõ: mỗi nguyên âm nhận tối đa một dấu phụ và một dấu thanh đứng ngay sau nó."""
    tones, marks, stroke = rules["tones"], rules["marks"], rules["stroke"]
    out, changed, i = [], 0, 0
    while i < len(text):
        ch = text[i]
        if ch in "dD" and i + 1 < len(text) and text[i + 1] == stroke:
            out.append("\u0111" if ch == "d" else "\u0110")
            changed += 1
            i += 2
            continue
        if ch in _VOWELS or ch in _MODIFIED:
            base, mark, tone, j = ch, "", "", i + 1
            while j < len(text):
                nxt = text[j]
                if not mark and not tone and nxt in marks and base in _MARK_FITS[marks[nxt]]:
                    mark = marks[nxt]
                elif not tone and nxt in tones:
                    tone = tones[nxt]
                else:
                    break
                j += 1
            if mark or tone:
                out.append(unicodedata.normalize("NFC", base + mark + tone))
                changed += 1
                i = j
                continue
        out.append(ch)
        i += 1
    return "".join(out), changed


def vni_to_unicode(text):
    """Chữ gõ kiểu VNI sang Unicode: "a1" -> "á", "o6" -> "ô", "d9" -> "đ", "Vie65t" -> "Việt".

    Dấu phải đứng NGAY SAU nguyên âm mang nó ("nu7o71c" -> "nước"). Cách gõ đặt dấu ở cuối âm tiết
    ("nu7o7c1") không được nhận, vì muốn đoán đúng thì phải tách âm tiết, dễ sửa nhầm chữ không phải tiếng Việt.
    Trả về (chuỗi mới, số ký tự đã đổi)."""
    return _convert_typing(text, VNI)


def viqr_to_unicode(text):
    """Chữ gõ kiểu VIQR sang Unicode: "Tie^'ng Vie^.t" -> "Tiếng Việt", "dd" -> "đ".
    Dấu chỉ được áp khi đứng ngay sau nguyên âm, nên dấu câu thường không bị đổi."""
    return _convert_typing(text, VIQR)


def looks_like_typing(text, rules, threshold=0.02):
    """Ước lượng chữ có đang ở kiểu gõ đó không: tỉ lệ dấu đứng ngay sau nguyên âm."""
    letters = [c for c in text if not c.isspace()]
    if not letters:
        return False
    signs = set(rules["tones"]) | set(rules["marks"])
    hits = sum(1 for i, c in enumerate(text)
               if c in signs and i and (text[i - 1] in _VOWELS or text[i - 1] in _MODIFIED))
    return hits / len(letters) >= threshold
