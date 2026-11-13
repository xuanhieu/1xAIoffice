# SPDX-License-Identifier: MPL-2.0
"""Sinh bộ hướng dẫn nhanh đi kèm 1xVnOffice: 1xDoc (.docx + .pdf), 1xSheet (.xlsx), 1xSlide (.pptx), mỗi file
tiếng Anh và tiếng Việt. Nội dung do 1x tự viết, ảnh là ảnh chụp chính 1xVnOffice (docs/ui).

Chạy bằng Python của app, nối vào một soffice headless đang nghe ở pipe:
  App/Contents/Resources/python scripts/guides/make-guides.py --pipe <tên> --out <thư mục> --only vi:doc
scripts/build-macos.sh (bước "guides") lo việc khởi động soffice và cài kết quả vào App/Contents/Resources/guides.
"""
import argparse
import time
from pathlib import Path

import uno
from com.sun.star.awt import Size
from com.sun.star.beans import PropertyValue

REPO = Path(__file__).resolve().parents[2]
UI = REPO / "docs" / "ui"
SHOTS = {"start": "startcenter-{lang}-2026-11-13.png", "writer": "writer-theme-2026-11-13.png",
         "calc": "calc-theme-2026-11-13.png", "impress": "impress-theme-2026-11-13.png"}
INK, ACCENT, DOC, SHEET, SLIDE = 0x1C1D22, 0x4C7DFF, 0x3D7BFD, 0x1FA463, 0xF07A28
CENTER = 3

NAMES = {
    "en": {"doc": "1xDoc Quick Start Guide", "sheet": "1xSheet Quick Start Guide", "slide": "1xSlide Quick Start Guide"},
    "vi": {"doc": "Hướng dẫn nhanh 1xDoc", "sheet": "Hướng dẫn nhanh 1xSheet", "slide": "Hướng dẫn nhanh 1xSlide"},
}

DOC_TEXT = {
    "en": {
        "title": "Welcome to 1xVnOffice – 1xDoc",
        "intro": "1xVnOffice is a free office suite made for Vietnam: documents, spreadsheets and presentations that open "
                 "and save Microsoft Office files, with Vietnamese tools built in. No ads, no tracking, and macros are "
                 "blocked unless you trust them.",
        "sections": [
            ("The ribbon at a glance", [
                "File – open, save, export to PDF, print and document properties.",
                "Home – clipboard, font, paragraph and styles: everything you use most.",
                "Insert – tables, pictures, charts, shapes, headers and page numbers.",
                "Layout – page size, margins, orientation, columns and breaks.",
                "References – table of contents, footnotes, captions and citations.",
                "Review – spelling, comments and track changes.",
                "View – zoom, page views, rulers and the navigator.",
            ]),
            ("Administrative documents (Decree 30)", [
                "Open the Vietnamese menu and choose New Administrative Document (Decree 30)…",
                "Fill in the issuing organization, number, place, date, subject, body and signer, then press OK.",
                "1xDoc lays the document out as Appendix I of Decree 30/2020/ND-CP requires: A4, margins, Times New "
                "Roman, the national title, rules, the signature block and the recipients list.",
                "Missing or wrong fields are flagged in the dialog, so nothing you typed is lost.",
                "The tool helps with the layout; the issuer stays responsible for the content and legal validity.",
            ]),
            ("Vietnamese tools", [
                "Convert TCVN3 (ABC) text to Unicode, in documents and spreadsheets.",
                "Normalize Vietnamese Unicode so search, sorting and spell check work reliably.",
                "Remove diacritics, for file names, codes and e-mail addresses.",
                "Number to words and amount in words (VND), as menu commands and as the DOCSO and DOCTIEN functions in "
                "1xSheet.",
            ]),
            ("Save and share", [
                "New documents are saved as .docx, so colleagues using Microsoft Word open them directly.",
                "File ▸ Export as PDF creates a PDF for sending or publishing.",
                "Agencies that must publish editable files in ODF can switch the default format in Options.",
            ]),
        ],
        "shortcuts_title": "Keyboard shortcuts",
        "shortcuts": [("Ctrl+N", "New document"), ("Ctrl+O", "Open"), ("Ctrl+S", "Save"), ("Ctrl+P", "Print"),
                      ("Ctrl+Z / Ctrl+Y", "Undo / Redo"), ("Ctrl+B / I / U", "Bold / Italic / Underline"),
                      ("Ctrl+F", "Find"), ("Ctrl+H", "Find and replace"), ("Ctrl+Enter", "Page break"),
                      ("F7", "Spelling and grammar")],
        "shortcuts_head": ("Shortcut", "Action"),
        "footer": "On macOS use ⌘ instead of Ctrl. Tips and more guides: menu Help.",
        "callouts": ["Start Center: open recent files or create a new document.",
                     "The ribbon groups commands by task, like Microsoft Office and WPS."],
    },
    "vi": {
        "title": "Chào mừng đến với 1xVnOffice – 1xDoc",
        "intro": "1xVnOffice là bộ văn phòng miễn phí làm cho người Việt: văn bản, bảng tính và trình chiếu mở và lưu "
                 "được file Microsoft Office, có sẵn công cụ tiếng Việt. Không quảng cáo, không theo dõi, macro bị chặn "
                 "trừ khi bạn tin cậy.",
        "sections": [
            ("Ribbon trong một trang", [
                "Tệp: mở, lưu, xuất PDF, in và thuộc tính tài liệu.",
                "Trang đầu: bảng tạm, phông chữ, đoạn văn và kiểu, những lệnh dùng nhiều nhất.",
                "Chèn: bảng, ảnh, biểu đồ, hình vẽ, đầu trang và số trang.",
                "Bố cục: khổ giấy, lề, hướng trang, cột và ngắt trang.",
                "Tham chiếu: mục lục, chú thích cuối trang, chú thích ảnh và trích dẫn.",
                "Xem lại: chính tả, ghi chú và theo dõi thay đổi.",
                "Xem: thu phóng, chế độ trang, thước và bộ điều hướng.",
            ]),
            ("Văn bản hành chính theo Nghị định 30", [
                "Mở menu Tiếng Việt, chọn Văn bản hành chính NĐ30 mới…",
                "Nhập cơ quan ban hành, số, địa danh, ngày, trích yếu, nội dung và người ký rồi bấm OK.",
                "1xDoc trình bày đúng Phụ lục I Nghị định 30/2020/NĐ-CP: khổ A4, lề, phông Times New Roman, Quốc hiệu, "
                "Tiêu ngữ, đường kẻ, khối chữ ký và nơi nhận.",
                "Ô thiếu hoặc sai được báo ngay trong hộp thoại, những gì bạn đã gõ không bị mất.",
                "Công cụ chỉ hỗ trợ trình bày; nội dung và giá trị pháp lý do người ban hành chịu trách nhiệm.",
            ]),
            ("Công cụ tiếng Việt", [
                "Chuyển mã TCVN3 (ABC) sang Unicode, trong cả văn bản lẫn bảng tính.",
                "Chuẩn hoá Unicode tiếng Việt để tìm kiếm, sắp xếp và kiểm chính tả chạy đúng.",
                "Bỏ dấu tiếng Việt, dùng cho tên tệp, mã số và địa chỉ thư.",
                "Đọc số và đọc số tiền thành chữ, có ở menu và ở hai hàm DOCSO, DOCTIEN trong 1xSheet.",
            ]),
            ("Lưu và chia sẻ", [
                "Văn bản mới được lưu dạng .docx, người dùng Microsoft Word mở được ngay.",
                "Tệp ▸ Xuất ra PDF để gửi hoặc đăng tải.",
                "Cơ quan phải đăng tài liệu sửa được ở dạng ODF có thể đổi định dạng mặc định trong Tuỳ chọn.",
            ]),
        ],
        "shortcuts_title": "Phím tắt",
        "shortcuts": [("Ctrl+N", "Tạo văn bản mới"), ("Ctrl+O", "Mở"), ("Ctrl+S", "Lưu"), ("Ctrl+P", "In"),
                      ("Ctrl+Z / Ctrl+Y", "Hoàn tác / Làm lại"), ("Ctrl+B / I / U", "Đậm / Nghiêng / Gạch chân"),
                      ("Ctrl+F", "Tìm"), ("Ctrl+H", "Tìm và thay thế"), ("Ctrl+Enter", "Ngắt trang"),
                      ("F7", "Chính tả và ngữ pháp")],
        "shortcuts_head": ("Phím", "Việc"),
        "footer": "Trên macOS dùng ⌘ thay cho Ctrl. Mẹo và hướng dẫn khác: menu Trợ giúp.",
        "callouts": ["Trang chủ: mở tệp gần đây hoặc tạo tài liệu mới.",
                     "Ribbon gom lệnh theo việc, giống Microsoft Office và WPS."],
    },
}

SHEET_TEXT = {
    "en": {"sheet": "Get started", "title": "Welcome to 1xVnOffice – 1xSheet",
           "intro": "Try it here: change a quantity or a price and every total, the amount in words and the chart update.",
           "head": ["Code", "Item", "Qty", "Unit price (VND)", "Amount (VND)", "Amount in words"],
           "rows": [("VPP01", "A4 paper, 500 sheets", 20, 78000), ("VPP02", "Ballpoint pens, box of 20", 15, 65000),
                    ("VPP03", "Lever arch files", 40, 32000), ("VPP04", "Toner cartridge", 4, 1250000),
                    ("VPP05", "Stapler", 10, 85000), ("VPP06", "Sticky notes", 30, 18000)],
           "total": "Total",
           "tips_title": "Tips",
           "tips": ["Amount in words uses DOCTIEN(amount); DOCSO(number) reads any number in Vietnamese.",
                    "The header row is frozen: scroll down and it stays on screen (View ▸ Freeze Cells).",
                    "Use the filter arrows in the header to show only some rows (Data ▸ AutoFilter).",
                    "Amounts above 1,000,000 VND are highlighted by conditional formatting (Format ▸ Conditional).",
                    "Select the table and use Insert ▸ Chart to chart it; the chart on the right is an example.",
                    "Files are saved as .xlsx by default so Excel users can open them. DOCSO and DOCTIEN are "
                    "1xVnOffice functions: Excel shows their last values but cannot recalculate them."],
           "chart": "Amount by item"},
    "vi": {"sheet": "Bắt đầu", "title": "Chào mừng đến với 1xVnOffice – 1xSheet",
           "intro": "Thử ngay tại đây: đổi số lượng hoặc đơn giá, mọi tổng, số tiền bằng chữ và biểu đồ tự cập nhật.",
           "head": ["Mã", "Mặt hàng", "SL", "Đơn giá (đồng)", "Thành tiền (đồng)", "Bằng chữ"],
           "rows": [("VPP01", "Giấy A4, ram 500 tờ", 20, 78000), ("VPP02", "Bút bi, hộp 20 cây", 15, 65000),
                    ("VPP03", "Bìa còng", 40, 32000), ("VPP04", "Hộp mực máy in", 4, 1250000),
                    ("VPP05", "Dập ghim", 10, 85000), ("VPP06", "Giấy nhớ", 30, 18000)],
           "total": "Tổng cộng",
           "tips_title": "Mẹo",
           "tips": ["Cột bằng chữ dùng DOCTIEN(số tiền); DOCSO(số) đọc mọi con số bằng tiếng Việt.",
                    "Dòng tiêu đề đã được cố định: cuộn xuống vẫn thấy (Xem ▸ Cố định ô).",
                    "Dùng mũi tên lọc ở dòng tiêu đề để chỉ hiện một số dòng (Dữ liệu ▸ Tự động lọc).",
                    "Thành tiền trên 1.000.000 đồng được tô nổi bằng định dạng có điều kiện (Định dạng ▸ Có điều kiện).",
                    "Chọn bảng rồi Chèn ▸ Biểu đồ để vẽ biểu đồ; biểu đồ bên phải là ví dụ.",
                    "Tệp được lưu dạng .xlsx để người dùng Excel mở được. DOCSO và DOCTIEN là hàm của 1xVnOffice: "
                    "Excel hiện giá trị đã tính nhưng không tính lại được."],
           "chart": "Thành tiền theo mặt hàng"},
}

SLIDE_TEXT = {
    "en": [
        ("Welcome to 1xVnOffice – 1xSlide", "Presentations that open in PowerPoint, made in Vietnam. Press F5 to play."),
        ("The workspace", None, "impress"),
        ("Build your slides", ["Home ▸ New Slide adds a slide; right-click a thumbnail to duplicate or delete it.",
                               "Drag thumbnails on the left to reorder.",
                               "Pick a layout in the sidebar: title, title and content, two columns…"]),
        ("Make it look good", ["Design ▸ choose a master slide to restyle every slide at once.",
                               "Insert pictures, tables, charts and shapes from the Insert tab.",
                               "Keep one idea per slide and big text: it reads well on a projector."]),
        ("Present", ["F5 starts from the first slide, Shift+F5 from the current one.",
                     "With two screens, the presenter console shows notes, the next slide and a timer.",
                     "Esc ends the show; B or W blanks the screen."]),
        ("Share", ["Saved as .pptx by default, ready for PowerPoint users.",
                   "File ▸ Export as PDF for handouts or e-mail.",
                   "Fonts that the other computer lacks can be embedded: File ▸ Properties ▸ Font."]),
    ],
    "vi": [
        ("Chào mừng đến với 1xVnOffice – 1xSlide", "Bài trình chiếu mở được bằng PowerPoint, làm tại Việt Nam. Bấm F5 để trình chiếu."),
        ("Màn hình làm việc", None, "impress"),
        ("Dựng các slide", ["Trang đầu ▸ Slide mới để thêm slide; bấm chuột phải vào ảnh thu nhỏ để nhân bản hoặc xoá.",
                            "Kéo ảnh thu nhỏ ở cột trái để đổi thứ tự.",
                            "Chọn bố cục ở thanh bên: tiêu đề, tiêu đề và nội dung, hai cột…"]),
        ("Làm cho đẹp", ["Thiết kế ▸ chọn slide cái để đổi kiểu mọi slide cùng lúc.",
                         "Chèn ảnh, bảng, biểu đồ và hình vẽ từ thẻ Chèn.",
                         "Mỗi slide một ý, chữ lớn: chiếu lên máy chiếu vẫn dễ đọc."]),
        ("Trình chiếu", ["F5 chiếu từ slide đầu, Shift+F5 chiếu từ slide đang chọn.",
                         "Có hai màn hình thì màn hình người trình bày hiện ghi chú, slide kế tiếp và đồng hồ.",
                         "Esc để dừng; B hoặc W để tạm che màn hình."]),
        ("Chia sẻ", ["Mặc định lưu dạng .pptx, người dùng PowerPoint mở được ngay.",
                     "Tệp ▸ Xuất ra PDF để in phát tay hoặc gửi thư.",
                     "Có thể nhúng phông chữ mà máy khác không có: Tệp ▸ Thuộc tính ▸ Phông chữ."]),
    ],
}


def prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


class Office:
    def __init__(self, pipe):
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        for _ in range(90):
            try:
                self.ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
                break
            except Exception:
                time.sleep(1)
        else:
            raise SystemExit("không nối được soffice")
        smgr = self.ctx.ServiceManager
        self.desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
        self.graphics = smgr.createInstanceWithContext("com.sun.star.graphic.GraphicProvider", self.ctx)

    def new(self, kind):
        """One visible document per soffice session: a hidden document, or a second document window, makes headless
        macOS soffice abort in AquaSalMenu::setMainMenu (same pattern as tests/runtime_check.py)."""
        return self.desktop.loadComponentFromURL(f"private:factory/{kind}", "_blank", 0, (prop("Hidden", False),))

    def graphic(self, path):
        return self.graphics.queryGraphic((prop("URL", uno.systemPathToFileUrl(str(path))),))


def store(doc, path, filt):
    doc.storeToURL(uno.systemPathToFileUrl(str(path)), (prop("FilterName", filt), prop("Overwrite", True)))


def thumbnail(doc, out, filename, filt, w, h):
    """Ảnh xem trước trang đầu cho mục Gần đây: guides/<lang>/thumbs/<tên tệp>.png."""
    (out / "thumbs").mkdir(exist_ok=True)
    data = uno.Any("[]com.sun.star.beans.PropertyValue", (prop("PixelWidth", w), prop("PixelHeight", h)))
    doc.storeToURL(uno.systemPathToFileUrl(str(out / "thumbs" / f"{filename}.png")),
                   (prop("FilterName", filt), prop("FilterData", data), prop("Overwrite", True)))


def shot(name, lang):
    return UI / SHOTS[name].format(lang=lang)


def fit(graphic, width_mm100):
    px = graphic.SizePixel
    return Size(width_mm100, int(width_mm100 * px.Height / px.Width))


# ---------------------------------------------------------------- 1xDoc
def make_doc(office, lang, out):
    t = DOC_TEXT[lang]
    doc = office.new("swriter")
    text = doc.Text
    page = doc.StyleFamilies.getByName("PageStyles").getByName("Standard")
    page.Width, page.Height = 21000, 29700
    page.LeftMargin = page.RightMargin = 2000
    page.TopMargin = page.BottomMargin = 1800
    width = page.Width - page.LeftMargin - page.RightMargin
    paras = doc.StyleFamilies.getByName("ParagraphStyles")
    for name, color in (("Title", INK), ("Heading 1", DOC)):
        paras.getByName(name).CharColor = color
    cur = text.createTextCursor()
    first = [True]

    def para(s, style="Text body", center=False, color=None):
        if not first[0]:
            text.insertControlCharacter(cur, 0, False)
        first[0] = False
        cur.ParaStyleName = style
        cur.ParaAdjust = CENTER if center else 0
        if color is not None:
            cur.CharColor = color
        text.insertString(cur, s, False)
        if color is not None:
            cur.setPropertyToDefault("CharColor")

    def image(path, caption):
        para("", center=True)
        g = office.graphic(path)
        obj = doc.createInstance("com.sun.star.text.TextGraphicObject")
        obj.Graphic = g
        obj.AnchorType = uno.Enum("com.sun.star.text.TextContentAnchorType", "AS_CHARACTER")
        obj.Size = fit(g, width)
        text.insertTextContent(cur, obj, False)
        para(caption, "Caption" if paras.hasByName("Caption") else "Text body", center=True)

    para("1xVnOffice", "Subtitle", center=True, color=ACCENT)
    para(t["title"], "Title", center=True)
    para(t["intro"], center=True)
    image(shot("start", lang), "① " + t["callouts"][0])
    image(shot("writer", lang), "② " + t["callouts"][1])
    # Bullets are drawn by hand: applying the "List Bullet" style over UNO aborts LibreOffice 26.8 on macOS.
    for heading, items in t["sections"]:
        para(heading, "Heading 1")
        for item in items:
            para("•\t" + item)
            cur.ParaLeftMargin, cur.ParaFirstLineIndent = 700, -500
    cur.ParaLeftMargin = cur.ParaFirstLineIndent = 0
    para(t["shortcuts_title"], "Heading 1")
    rows = [t["shortcuts_head"]] + t["shortcuts"]
    table = doc.createInstance("com.sun.star.text.TextTable")
    table.initialize(len(rows), 2)
    text.insertControlCharacter(cur, 0, False)
    text.insertTextContent(cur, table, False)
    for r, (a, b) in enumerate(rows):
        for c, v in enumerate((a, b)):
            cell = table.getCellByPosition(c, r)
            cell.setString(v)
            if r == 0:
                cell.BackColor = DOC
                tc = cell.Text.createTextCursor()
                tc.gotoEnd(True)
                tc.CharColor, tc.CharWeight = 0xFFFFFF, 150.0
    end = text.createTextCursor()
    end.gotoEnd(False)
    cur = end
    para(t["footer"], center=True, color=0x6B6E78)
    name = NAMES[lang]["doc"]
    store(doc, out / f"{name}.docx", "MS Word 2007 XML")
    store(doc, out / f"{name}.pdf", "writer_pdf_Export")
    doc.CurrentController.ViewCursor.jumpToFirstPage()  # PNG export draws the page holding the cursor
    thumbnail(doc, out, f"{name}.docx", "writer_png_Export", 256, 362)


# ---------------------------------------------------------------- 1xSheet
def make_sheet(office, lang, out):
    t = SHEET_TEXT[lang]
    doc = office.new("scalc")
    sheets = doc.Sheets
    sheet = sheets.getByIndex(0)
    sheets.getByIndex(0).Name = t["sheet"]
    cell = sheet.getCellRangeByName
    cell("A1").String = t["title"]
    cell("A1").CharHeight, cell("A1").CharWeight, cell("A1").CharColor = 20, 150.0, INK
    cell("A2").String = t["intro"]
    cell("A2").CharColor = 0x6B6E78
    top = 4  # header row (1-based)
    for c, h in enumerate(t["head"]):
        x = sheet.getCellByPosition(c, top - 1)
        x.String = h
        x.CellBackColor, x.CharColor, x.CharWeight = SHEET, 0xFFFFFF, 150.0
    for i, (code, item, qty, price) in enumerate(t["rows"]):
        r = top + 1 + i
        cell(f"A{r}").String, cell(f"B{r}").String = code, item
        cell(f"C{r}").Value, cell(f"D{r}").Value = qty, price
        cell(f"E{r}").Formula = f"=C{r}*D{r}"
        cell(f"F{r}").Formula = f"=DOCTIEN(E{r})"
    last = top + len(t["rows"])
    tot = last + 1
    cell(f"B{tot}").String = t["total"]
    cell(f"E{tot}").Formula = f"=SUM(E{top + 1}:E{last})"
    cell(f"F{tot}").Formula = f"=DOCTIEN(E{tot})"
    for ref in (f"B{tot}", f"E{tot}", f"F{tot}"):
        cell(ref).CharWeight = 150.0
    fmt = doc.NumberFormats.queryKey("#,##0", doc.CharLocale, False)
    if fmt == -1:
        fmt = doc.NumberFormats.addNew("#,##0", doc.CharLocale)
    cell(f"D{top + 1}:E{tot}").NumberFormat = fmt
    cols = sheet.Columns
    for i, w in enumerate((1800, 5600, 1500, 3600, 3800, 12000)):
        cols.getByIndex(i).Width = w
    # Conditional formatting: amounts above 1,000,000 use the built-in "Good" style.
    rng = cell(f"E{top + 1}:E{last}")
    cf = rng.ConditionalFormat
    cf.addNew((prop("Operator", uno.Enum("com.sun.star.sheet.ConditionOperator", "GREATER")),
               prop("Formula1", "1000000"), prop("StyleName", "Good")))
    rng.ConditionalFormat = cf
    # AutoFilter on the table.
    addr = cell(f"A{top}:F{last}").RangeAddress
    dbs = doc.DatabaseRanges
    if not dbs.hasByName("Items"):
        dbs.addNewByName("Items", addr)
    dbs.getByName("Items").AutoFilter = True
    # Tips.
    tip_row = tot + 2
    cell(f"A{tip_row}").String = t["tips_title"]
    cell(f"A{tip_row}").CharWeight, cell(f"A{tip_row}").CharHeight = 150.0, 13
    for i, tip in enumerate(t["tips"]):
        cell(f"A{tip_row + 1 + i}").String = f"{i + 1}. {tip}"
    # Chart next to the tips.
    rect = uno.createUnoStruct("com.sun.star.awt.Rectangle")
    rect.X, rect.Y, rect.Width, rect.Height = 1000, sheet.Rows.getByIndex(tip_row + 8).Position.Y, 16000, 8000
    chart_range = uno.createUnoStruct("com.sun.star.table.CellRangeAddress")
    chart_range.Sheet, chart_range.StartColumn, chart_range.EndColumn = 0, 4, 4
    chart_range.StartRow, chart_range.EndRow = top - 1, last - 1
    sheet.Charts.addNewByName("Amounts", rect, (chart_range,), True, False)
    chart = sheet.Charts.getByName("Amounts").EmbeddedObject
    chart.HasMainTitle = True
    chart.Title.String = t["chart"]
    chart.HasLegend = False
    chart.getData().setRowDescriptions(tuple(r[1] for r in t["rows"]))  # item names as categories
    doc.CurrentController.freezeAtPosition(0, top)
    store(doc, out / f"{NAMES[lang]['sheet']}.xlsx", "Calc MS Excel 2007 XML")
    thumbnail(doc, out, f"{NAMES[lang]['sheet']}.xlsx", "calc_png_Export", 256, 362)


# ---------------------------------------------------------------- 1xSlide
def make_slide(office, lang, out):
    slides = SLIDE_TEXT[lang]
    doc = office.new("simpress")
    pages = doc.DrawPages
    master = doc.MasterPages.getByIndex(0)
    bg = doc.createInstance("com.sun.star.drawing.Background")
    bg.FillStyle = uno.Enum("com.sun.star.drawing.FillStyle", "SOLID")
    bg.FillColor = 0xF7F8FB
    master.Background = bg
    W, H = pages.getByIndex(0).Width, pages.getByIndex(0).Height
    for i, spec in enumerate(slides):
        page = pages.getByIndex(0) if i == 0 else pages.insertNewByIndex(pages.Count - 1)
        title = spec[0]
        if i == 0:
            page.Layout = 0  # title slide
        else:
            page.Layout = 1  # title, content
        shapes = [page.getByIndex(k) for k in range(page.Count)]
        if shapes:
            shapes[0].String = title
            shapes[0].CharColor = SLIDE if i else INK
        body = spec[1]
        if i == 0 and len(shapes) > 1:
            shapes[1].String = body
        elif isinstance(body, list) and len(shapes) > 1:
            shapes[1].String = "\n".join(body)
        elif body is None:
            for s in shapes[1:]:
                page.remove(s)
            g = office.graphic(shot(spec[2], lang))
            pic = doc.createInstance("com.sun.star.drawing.GraphicObjectShape")
            page.add(pic)
            pic.Graphic = g
            size = fit(g, int(W * 0.82))
            if size.Height > H * 0.7:
                size = Size(int(size.Width * H * 0.7 / size.Height), int(H * 0.7))
            pic.Size = size
            pos = uno.createUnoStruct("com.sun.star.awt.Point")
            pos.X, pos.Y = (W - size.Width) // 2, int(H * 0.24)
            pic.Position = pos
    store(doc, out / f"{NAMES[lang]['slide']}.pptx", "Impress MS PowerPoint 2007 XML")
    doc.CurrentController.setCurrentPage(doc.DrawPages.getByIndex(0))
    thumbnail(doc, out, f"{NAMES[lang]['slide']}.pptx", "impress_png_Export", 256, 144)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipe", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", required=True, help="<lang>:<doc|sheet|slide>; headless macOS soffice aborts when a "
                                                   "second document window opens, so each file gets its own session")
    a = ap.parse_args()
    lang, kind = a.only.split(":")
    out = Path(a.out) / lang
    out.mkdir(parents=True, exist_ok=True)
    {"doc": make_doc, "sheet": make_sheet, "slide": make_slide}[kind](Office(a.pipe), lang, out)
    print(f"{lang}:{kind} OK", flush=True)


if __name__ == "__main__":
    main()
