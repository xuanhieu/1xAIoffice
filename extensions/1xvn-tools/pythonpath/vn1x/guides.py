# SPDX-License-Identifier: MPL-2.0
"""Chọn bộ hướng dẫn nhanh đi kèm app (App/Contents/Resources/guides/<lang>/) để đưa vào mục Gần đây ở lần chạy đầu,
giống cách WPS hiện sẵn Quick Start Guide. Thuần Python, không cần UNO."""
from pathlib import Path

# 1xDoc lên đầu danh sách Gần đây. Bản PDF của hướng dẫn 1xDoc vẫn nằm trong thư mục nhưng không đưa vào Gần đây:
# Start Center hiện tên không kèm đuôi, hai mục cùng tên chỉ gây rối.
ORDER = (".docx", ".xlsx", ".pptx")
FILTERS = {".docx": "MS Word 2007 XML", ".xlsx": "Calc MS Excel 2007 XML", ".pptx": "Impress MS PowerPoint 2007 XML"}


def pick_language(ui_locale):
    return "vi" if (ui_locale or "").lower().startswith("vi") else "en"


def thumbnail_png(path):
    """Ảnh xem trước do scripts/guides/make-guides.py sinh (thumbs/<tên tệp>.png), hoặc None."""
    png = Path(path).parent / "thumbs" / (Path(path).name + ".png")
    return png.read_bytes() if png.is_file() else None


def guide_files(root, ui_locale):
    """Danh sách (đường dẫn, filter) theo thứ tự hiển thị; rỗng nếu app không có bộ hướng dẫn."""
    folder = Path(root) / pick_language(ui_locale)
    if not folder.is_dir():
        return []
    files = [p for p in folder.iterdir() if p.suffix.lower() in FILTERS]
    files.sort(key=lambda p: (ORDER.index(p.suffix.lower()), p.name))
    return [(p, FILTERS[p.suffix.lower()]) for p in files]
