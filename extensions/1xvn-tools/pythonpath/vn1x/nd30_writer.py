# SPDX-License-Identifier: MPL-2.0
"""Đặt các khối do nd30.build() tạo ra vào một tài liệu Writer (cần UNO).

Bố cục theo Mục IV Phần I Phụ lục I NĐ30: bảng không viền 2 cột ở đầu trang (trái: cơ quan, số ký hiệu, V/v; phải:
Quốc hiệu, Tiêu ngữ, địa danh ngày tháng), tên loại và trích yếu canh giữa, nội dung canh đều, bảng 2 cột cuối văn bản
(trái: nơi nhận; phải: quyền hạn, chức vụ, họ tên người ký). Số trang canh giữa ở lề trên, không hiện ở trang đầu.
"""
import uno

PT_TO_MM100 = 35.278  # 1 pt = 0.35278 mm
CENTER, LEFT, BLOCK = 3, 0, 2  # com.sun.star.style.ParagraphAdjust


def _char_em(c):
    """Bề rộng ước lượng của một ký tự Times New Roman, theo em."""
    if c == " ":
        return 0.25
    if c.isupper():
        return 0.72
    if c.isdigit():
        return 0.5
    return 0.48 if c.isalpha() else 0.33


def text_width_mm100(text, size_pt, bold=False):
    em = sum(_char_em(c) for c in text) * (1.06 if bold else 1.0)
    return int(em * size_pt * PT_TO_MM100)


def _border(width_mm100=18):
    line = uno.createUnoStruct("com.sun.star.table.BorderLine2")
    line.OuterLineWidth = width_mm100
    line.LineWidth = width_mm100
    return line


def _vi_locale():
    loc = uno.createUnoStruct("com.sun.star.lang.Locale")
    loc.Language, loc.Country = "vi", "VN"
    return loc


def _no_border():
    return uno.createUnoStruct("com.sun.star.table.BorderLine2")


class Writer:
    def __init__(self, doc, font):
        self.doc = doc
        self.font = font

    def para(self, xtext, block, adjust=CENTER, first=False, indent=0, space_after=0, line_percent=100):
        cur = xtext.createTextCursor()
        cur.gotoEnd(False)
        if not first:
            xtext.insertControlCharacter(cur, 0, False)  # PARAGRAPH_BREAK
        # A new paragraph inherits the previous one's attributes: undo the indents and border of a rule paragraph.
        cur.ParaLeftMargin = 0
        cur.ParaRightMargin = 0
        cur.BottomBorder = _no_border()
        cur.BottomBorderDistance = 0
        cur.ParaAdjust = adjust
        cur.ParaFirstLineIndent = indent
        cur.ParaTopMargin = int(block.get("space_before", 0) * PT_TO_MM100)
        cur.ParaBottomMargin = int(space_after * PT_TO_MM100)
        spacing = uno.createUnoStruct("com.sun.star.style.LineSpacing")
        spacing.Mode, spacing.Height = 0, line_percent  # PROP
        cur.ParaLineSpacing = spacing
        cur.CharFontName = self.font
        cur.CharLocale = _vi_locale()  # kiểm chính tả tiếng Việt, không theo ngôn ngữ giao diện
        cur.CharHeight = block["size"]
        cur.CharWeight = 150.0 if block.get("bold") else 100.0
        cur.CharPosture = uno.Enum("com.sun.star.awt.FontSlant", "ITALIC" if block.get("italic") else "NONE")
        xtext.insertString(cur, block["text"], False)
        for _ in range(block.get("blank_lines", 0)):
            xtext.insertControlCharacter(cur, 1, False)  # LINE_BREAK: chỗ trống để ký
        return cur

    def rule(self, xtext, block, column_mm100, share):
        """Đường kẻ ngang dưới một dòng chữ: một đoạn rỗng cỡ 2pt có viền dưới, lề hai bên để đường kẻ canh giữa và
        dài bằng share x bề rộng dòng chữ."""
        width = int(text_width_mm100(block["text"], block["size"], block.get("bold")) * share)
        width = min(width, column_mm100)
        cur = xtext.createTextCursor()
        cur.gotoEnd(False)
        xtext.insertControlCharacter(cur, 0, False)
        cur.CharHeight = 2
        cur.ParaTopMargin = cur.ParaBottomMargin = 0
        side = max(0, (column_mm100 - width) // 2)
        cur.ParaLeftMargin = side
        cur.ParaRightMargin = side
        cur.ParaFirstLineIndent = 0
        cur.BottomBorder = _border()
        cur.BottomBorderDistance = 0

    def blocks(self, xtext, blocks, column_mm100, adjust=CENTER, first=True):
        for i, b in enumerate(blocks):
            self.para(xtext, b, adjust=adjust, first=first and i == 0)
            if b.get("rule"):
                self.rule(xtext, b, column_mm100, 1.0 if b["rule"] == "full" else 0.4)

    def table(self, cursor, percents):
        text = self.doc.getText()
        table = self.doc.createInstance("com.sun.star.text.TextTable")
        table.initialize(1, 2)
        text.insertTextContent(cursor, table, False)
        sep = table.TableColumnSeparators
        sep[0].Position = int(10000 * percents[0] / 100)
        table.TableColumnSeparators = sep
        borders = table.TableBorder2
        for name in ("TopLine", "BottomLine", "LeftLine", "RightLine", "HorizontalLine", "VerticalLine"):
            setattr(borders, name, _no_border())
        table.TableBorder2 = borders
        return table


def _setup_pages(doc, spec):
    page, font = spec["page"], spec["font"]
    styles = doc.getStyleFamilies()
    para_styles = styles.getByName("ParagraphStyles")
    default = para_styles.getByName("Standard")
    default.CharFontName = font
    default.CharHeight = spec["body_size"]
    default.CharLocale = _vi_locale()
    pages = styles.getByName("PageStyles")
    for name in ("Standard", "First Page"):
        ps = pages.getByName(name)
        ps.Width, ps.Height = page["width_mm"] * 100, page["height_mm"] * 100
        ps.TopMargin, ps.BottomMargin = page["margin_top_mm"] * 100, page["margin_bottom_mm"] * 100
        ps.LeftMargin, ps.RightMargin = page["margin_left_mm"] * 100, page["margin_right_mm"] * 100
    first = pages.getByName("First Page")
    first.HeaderIsOn = False
    first.FollowStyle = "Standard"
    std = pages.getByName("Standard")
    std.HeaderIsOn = True
    header = std.HeaderText
    cur = header.createTextCursor()
    cur.ParaAdjust = CENTER
    cur.CharFontName = font
    cur.CharHeight = spec["page_number_size"]
    field = doc.createInstance("com.sun.star.text.TextField.PageNumber")
    field.NumberingType = 4  # com.sun.star.style.NumberingType.ARABIC
    field.SubType = uno.Enum("com.sun.star.text.PageNumberType", "CURRENT")
    header.insertTextContent(cur, field, False)
    return (page["width_mm"] - page["margin_left_mm"] - page["margin_right_mm"]) * 100


def fill(doc, spec):
    """Ghi văn bản vào tài liệu Writer trống `doc` (gom thành một bước hoàn tác)."""
    doc.UndoManager.enterUndoContext("Văn bản hành chính NĐ30")
    try:
        w = Writer(doc, spec["font"])
        text_width = _setup_pages(doc, spec)
        text = doc.getText()
        cur = text.createTextCursor()
        left_pct, right_pct = spec["header_columns_percent"]
        head = w.table(cur, spec["header_columns_percent"])
        head.PageDescName = "First Page"  # the table is the first element: page 1 without page number
        w.blocks(head.getCellByName("A1").getText(), spec["left"], text_width * left_pct // 100)
        w.blocks(head.getCellByName("B1").getText(), spec["right"], text_width * right_pct // 100)

        first = True
        for b in spec["title"]:
            w.para(text, b, adjust=CENTER, first=first)
            first = False
            if b.get("rule"):
                w.rule(text, b, text_width, 0.4)
        body = spec["body_format"]
        for i, p in enumerate(spec["body"]):
            w.para(text, {"text": p, "size": spec["body_size"], "space_before": 6 if i == 0 else 0},
                   adjust=BLOCK, first=first, indent=int(body["first_line_indent_mm"] * 100),
                   space_after=body["space_after_pt"], line_percent=body["line_spacing_percent"])
            first = False

        end = text.createTextCursor()
        end.gotoEnd(False)
        text.insertControlCharacter(end, 0, False)
        if spec.get("sign_columns"):
            # Văn bản hai bên (và biên bản theo Mẫu 1.9): hai cột chữ ký bằng nhau, "Nơi nhận" xuống dưới.
            left_col, right_col = spec["sign_columns"]
            signs = w.table(end, [50, 50])
            w.blocks(signs.getCellByName("A1").getText(), left_col, text_width // 2)
            w.blocks(signs.getCellByName("B1").getText(), right_col, text_width // 2)
            after = text.createTextCursor()
            after.gotoEnd(False)
            w.blocks(text, spec["receivers"], text_width, adjust=LEFT, first=True)
        else:
            sign = w.table(end, [45, 55])
            w.blocks(sign.getCellByName("A1").getText(), spec["receivers"], text_width * 45 // 100, adjust=LEFT)
            w.blocks(sign.getCellByName("B1").getText(), spec["sign"], text_width * 55 // 100)
    finally:
        doc.UndoManager.leaveUndoContext()
