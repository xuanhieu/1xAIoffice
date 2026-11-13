# SPDX-License-Identifier: MPL-2.0
"""Tách họ, đệm, tên và tạo khoá sắp xếp theo thứ tự chữ cái tiếng Việt (thuần Python).

Người Việt sắp danh sách theo TÊN trước, rồi đệm, rồi họ. Sắp bằng hàm có sẵn của bảng tính thì sai hai chỗ: thứ tự
chữ cái (ă, â, đ, ê, ô, ơ, ư nằm sai chỗ) và thứ tự dấu thanh. sort_key() trả về chuỗi sắp đúng cả hai.
"""
import unicodedata

# Thứ tự chữ cái tiếng Việt. Chữ không có trong bảng (chữ nước ngoài, số) xếp sau, theo thứ tự Unicode.
ALPHABET = ["a", "ă", "â", "b", "c", "d", "đ", "e", "ê", "g", "h", "i", "k", "l", "m",
            "n", "o", "ô", "ơ", "p", "q", "r", "s", "t", "u", "ư", "v", "x", "y"]
# Thứ tự dấu thanh: ngang, huyền, hỏi, ngã, sắc, nặng.
TONES = {"": 0, "̀": 1, "̉": 2, "̃": 3, "́": 4, "̣": 5}
_LETTER = {letter: index for index, letter in enumerate(ALPHABET)}
_MARKS = {"̂": "â", "̆": "ă", "̛": "ơ"}   # dấu mũ, dấu á, dấu móc


def split_name(full):
    """"Nguyễn Thị Ánh Nguyệt" -> ("Nguyễn", "Thị Ánh", "Nguyệt"). Tên là tiếng cuối, họ là tiếng đầu.

    Một tiếng thì coi là tên. Chuỗi rỗng trả về ba chuỗi rỗng."""
    parts = str(full).split()
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return "", "", parts[0]
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def _syllable_key(word):
    letters, tones = [], []
    for ch in unicodedata.normalize("NFD", word.casefold()):
        if ch in TONES:
            tones.append(str(TONES[ch]))
            continue
        if ch in _MARKS:                      # dấu phụ: gộp lại với nguyên âm vừa thêm
            if letters:
                base = letters.pop()
                combined = unicodedata.normalize("NFC", base + ch)
                letters.append(combined if combined in _LETTER else base)
            continue
        letters.append(ch)
    codes = "".join(f"{_LETTER[c]:02d}" if c in _LETTER else f"9{ord(c):05d}" for c in letters)
    return codes + "\x01" + "".join(tones)


def sort_key(full):
    """Khoá sắp xếp danh sách người Việt: tên trước, rồi đệm, rồi họ; đúng thứ tự chữ cái và dấu thanh."""
    ho, dem, ten = split_name(full)
    order = [ten] + dem.split() + ([ho] if ho else [])
    return "\x00".join(_syllable_key(word) for word in order if word)
