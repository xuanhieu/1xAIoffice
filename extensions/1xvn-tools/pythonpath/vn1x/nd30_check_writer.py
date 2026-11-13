# SPDX-License-Identifier: MPL-2.0
"""Đọc một tài liệu Writer thành bản mô tả cho nd30_check.check(), và sửa phần trang khi người dùng đồng ý (cần UNO)."""
CENTER = 3
MM100 = 100.0


def _paragraphs(text):
    """Lần lượt các đoạn văn trong `text`, bỏ qua bảng."""
    it = text.createEnumeration()
    while it.hasMoreElements():
        element = it.nextElement()
        if element.supportsService("com.sun.star.text.Paragraph"):
            yield element


def _tables_text(doc):
    tables = doc.getTextTables()
    for i in range(tables.getCount()):
        table = tables.getByIndex(i)
        for name in table.getCellNames():
            yield table.getCellByName(name).getString()


def _page_style(doc):
    """Kiểu trang đang dùng: lấy theo đoạn đầu nếu đoạn đó chỉ định, nếu không thì Standard."""
    pages = doc.getStyleFamilies().getByName("PageStyles")
    for para in _paragraphs(doc.getText()):
        name = para.PageDescName
        if name and pages.hasByName(name):
            return pages.getByName(name)
        break
    tables = doc.getTextTables()
    if tables.getCount():
        name = tables.getByIndex(0).PageDescName
        if name and pages.hasByName(name):
            return pages.getByName(name)
    return pages.getByName("Standard")


def describe(doc):
    """Bản mô tả tài liệu: khổ trang, các đoạn nội dung và toàn bộ chữ (kể cả trong bảng)."""
    style = _page_style(doc)
    default = doc.getStyleFamilies().getByName("ParagraphStyles").getByName("Standard")
    page = {"width_mm": style.Width / MM100, "height_mm": style.Height / MM100,
            "margin_top_mm": style.TopMargin / MM100, "margin_bottom_mm": style.BottomMargin / MM100,
            "margin_left_mm": style.LeftMargin / MM100, "margin_right_mm": style.RightMargin / MM100,
            "font": default.CharFontName}
    body, texts = [], []
    for para in _paragraphs(doc.getText()):
        content = para.getString()
        texts.append(content)
        if not content.strip() or para.ParaAdjust == CENTER:
            continue    # bỏ phần canh giữa: tên loại, trích yếu, Kính gửi
        body.append({"text": content, "size": para.CharHeight, "font": para.CharFontName,
                     "adjust": para.ParaAdjust, "indent_mm": para.ParaFirstLineIndent / MM100})
    texts.extend(_tables_text(doc))
    return {"page": page, "body": body, "texts": texts}


def apply_page_fix(doc, fix):
    """Đặt lại khổ giấy, lề và phông mặc định theo NĐ30. Gom thành một bước hoàn tác."""
    doc.UndoManager.enterUndoContext("Sửa thể thức trang NĐ30")
    try:
        pages = doc.getStyleFamilies().getByName("PageStyles")
        used = {_page_style(doc).Name}
        for name in ("Standard", "First Page"):
            if pages.hasByName(name):
                used.add(name)
        for name in used:
            style = pages.getByName(name)
            style.Width, style.Height = int(fix["width_mm"] * MM100), int(fix["height_mm"] * MM100)
            style.TopMargin = int(fix["margin_top_mm"] * MM100)
            style.BottomMargin = int(fix["margin_bottom_mm"] * MM100)
            style.LeftMargin = int(fix["margin_left_mm"] * MM100)
            style.RightMargin = int(fix["margin_right_mm"] * MM100)
        doc.getStyleFamilies().getByName("ParagraphStyles").getByName("Standard").CharFontName = fix["font"]
    finally:
        doc.UndoManager.leaveUndoContext()
