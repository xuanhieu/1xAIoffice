# SPDX-License-Identifier: MPL-2.0
"""Áp một phép biến đổi chữ lên tài liệu Writer hoặc Calc qua UNO, giữ định dạng và gom thành một bước hoàn tác.

Writer: có vùng chọn thì đổi chữ trong vùng chọn (định dạng ký tự bên trong vùng chọn có thể bị gộp); không chọn gì thì
duyệt cả tài liệu theo từng đoạn chữ cùng định dạng (TextPortion), kể cả ô bảng, nên định dạng được giữ nguyên.
Calc: đổi các ô chữ trong vùng chọn.
"""


def _undo(doc, title):
    class _Ctx:
        def __enter__(self):
            doc.UndoManager.enterUndoContext(title)

        def __exit__(self, *exc):
            doc.UndoManager.leaveUndoContext()
            return False
    return _Ctx()


def _portions(text):
    """Mọi TextPortion chữ trong một XText, kể cả trong bảng."""
    enum = text.createEnumeration()
    while enum.hasMoreElements():
        para = enum.nextElement()
        if para.supportsService("com.sun.star.text.TextTable"):
            for name in para.getCellNames():
                yield from _portions(para.getCellByName(name).getText())
            continue
        if not para.supportsService("com.sun.star.text.Paragraph"):
            continue
        portions = para.createEnumeration()
        while portions.hasMoreElements():
            p = portions.nextElement()
            if p.TextPortionType == "Text":
                yield p


def _writer_selection(doc):
    sel = doc.getCurrentController().getSelection()
    ranges = []
    if sel is not None and sel.supportsService("com.sun.star.text.TextRanges"):
        for i in range(sel.getCount()):
            r = sel.getByIndex(i)
            if r.getString():
                ranges.append(r)
    return ranges


def writer_transform(doc, func, title, portion_filter=None, after=None):
    """func(str) -> str. portion_filter(portion) -> bool chọn đoạn cần đổi khi không có vùng chọn.
    after(portion_or_range) chạy sau khi đổi (vd đổi phông). Trả về số đoạn đã đổi."""
    changed = 0
    with _undo(doc, title):
        selected = _writer_selection(doc)
        targets = selected or [p for p in _portions(doc.getText()) if portion_filter is None or portion_filter(p)]
        for t in targets:
            old = t.getString()
            new = func(old)
            if new != old:
                t.setString(new)
                changed += 1
            if after is not None and (new != old or selected):
                after(t)
    return changed


def _calc_cells(doc):
    sel = doc.getCurrentController().getSelection()
    if sel.supportsService("com.sun.star.sheet.SheetCellRanges"):
        ranges = [sel.getByIndex(i) for i in range(sel.getCount())]
    else:
        ranges = [sel]
    for r in ranges:
        addr = r.getRangeAddress()
        for row in range(addr.EndRow - addr.StartRow + 1):
            for col in range(addr.EndColumn - addr.StartColumn + 1):
                yield r.getCellByPosition(col, row)


def calc_transform_text(doc, func, title):
    from com.sun.star.table.CellContentType import TEXT
    changed = 0
    with _undo(doc, title):
        for cell in _calc_cells(doc):
            if cell.getType() == TEXT:
                old = cell.getString()
                new = func(old)
                if new != old:
                    cell.setString(new)
                    changed += 1
    return changed


def calc_numbers_to_right(doc, func, title):
    """Với mỗi ô số trong vùng chọn, ghi func(giá trị) vào ô bên phải nếu ô đó đang trống."""
    from com.sun.star.table.CellContentType import EMPTY, FORMULA, VALUE
    written = skipped = 0
    with _undo(doc, title):
        for cell in _calc_cells(doc):
            if cell.getType() not in (VALUE, FORMULA) or cell.getError():
                continue
            addr = cell.getCellAddress()
            sheet = doc.getSheets().getByIndex(addr.Sheet)
            target = sheet.getCellByPosition(addr.Column + 1, addr.Row)
            if target.getType() != EMPTY:
                skipped += 1
                continue
            target.setString(func(cell.getValue()))
            written += 1
    return written, skipped
