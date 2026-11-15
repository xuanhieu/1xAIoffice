# SPDX-License-Identifier: MPL-2.0
"""Sinh bộ hướng dẫn nhanh đi kèm 1xAIoffice: 1xDoc (.docx + .pdf), 1xSheet (.xlsx), 1xSlide (.pptx), mỗi file
tiếng Anh và tiếng Việt. Nội dung do 1x tự viết, ảnh là ảnh chụp chính 1xAIoffice (docs/ui).

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
ABOUT = __import__("json").loads((REPO / "branding" / "about.json").read_text(encoding="utf-8"))
UI = REPO / "docs" / "ui"
# Ảnh app thật, chụp bằng scripts/guides/capture-shots.py (mỗi ảnh đúng một cửa sổ 1xAIoffice), bản vi và en.
SHOTS = {k: f"guide-{k}-{{lang}}.png" for k in ("start", "writer", "nd30", "calc", "impress", "ribbon", "sidebar")}
INK, ACCENT, DOC, SHEET, SLIDE, AI = 0x1C1D22, 0x4C7DFF, 0x3D7BFD, 0x1FA463, 0xF07A28, 0x8B6CFF
MUTED = 0x5F6368
SERIF, SANS = "Noto Serif", "Noto Sans"   # đi kèm app, đủ dấu tiếng Việt
CENTER = 3

NAMES = {
    "en": {"doc": "1xDoc Quick Start Guide", "sheet": "1xSheet Quick Start Guide", "slide": "1xSlide Quick Start Guide"},
    "vi": {"doc": "Hướng dẫn nhanh 1xDoc", "sheet": "Hướng dẫn nhanh 1xSheet", "slide": "Hướng dẫn nhanh 1xSlide"},
}

DOC_TEXT = {
    "en": {
        "brand": "1xAIoffice",
        "title": "Welcome to 1xAIoffice – 1xDoc",
        "intro": "A free office suite made for Vietnam. Documents, spreadsheets and presentations that open and save "
                 "Microsoft Office files, administrative documents laid out by Decree 30, Vietnamese tools built in, "
                 "and an AI assistant on your own account, only when you ask for it.",
        "callouts": [("Top bar", "New ▾ creates any kind of document; Window ▾ switches between open files."),
                     ("Command tabs", "Home, Insert, Layout, References, Review, View: commands grouped by task."),
                     ("AI tab", "Ask AI, rewrite, run a skill, Decree 30 documents and checks, in one place."),
                     ("AI sidebar", "Open it from the right edge when you need it; it shows which AI is in use."),
                     ("Status bar", "Pages, words, document language and zoom, always in view.")],
        "sections": [
            ("Start in one click", "start", [
                "The Start Center shows big cards: blank document, spreadsheet, presentation, and Decree 30 templates "
                "(official letter, proposal, decision, minutes).",
                "Recent documents are listed by Today, Yesterday, Within 7 days and Older, with location, date and "
                "size. Double-click to open.",
                "Click Document, Spreadsheet or Presentation on the left for that app's own page.",
                "VI / EN in the top corner switches the interface language; the app restarts in a few seconds.",
            ]),
            ("An AI assistant when you need it", "sidebar", [
                "Use the AI tab, the AI sidebar, or right-click selected text: Ask AI, Rewrite, Run a skill.",
                "Bring your own AI: the ChatGPT plan you already pay for, an API key (Groq, Gemini, OpenRouter, Mistral "
                "and others have free tiers), or AI running on this computer so nothing leaves it.",
                "AI Accounts lists free providers first and opens the page where you get a key.",
                "Rewrites show a preview first and undo in one step (⌘Z). Asking never changes your document.",
            ]),
            ("Administrative documents (Decree 30)", "nd30", [
                "28 document types from Appendix III of Decree 30/2020/ND-CP, with body templates and signature "
                "blocks, including documents signed by two parties.",
                "Fill in the dialog: issuing organization, number, place, date, subject, body and signer.",
                "Check Decree 30 Format reviews any open document and fixes the page: A4, margins, font.",
                "The tool helps with layout; the issuer stays responsible for content and legal validity.",
            ]),
            ("Vietnamese tools", "ribbon", [
                "Convert TCVN3 (ABC), VNI and VIQR text to Unicode; normalize Vietnamese Unicode.",
                "Remove diacritics for file names, codes and e-mail addresses.",
                "Number to words and amount in words (VND); DOCSO and DOCTIEN functions in 1xSheet.",
            ]),
            ("Your work is saved for you", None, [
                "Recovery data is saved every 2 minutes, and documents that already have a file name are saved "
                "directly at the same pace.",
                "A backup copy is kept each time you save. After a crash, 1xAIoffice offers to recover your work.",
                "Change or turn this off in Tools ▸ Options ▸ Load/Save ▸ General.",
            ]),
            ("Save and share", None, [
                "New documents are saved as .docx, so colleagues using Microsoft Word open them directly.",
                "File ▸ Export as PDF creates a PDF for sending or publishing.",
            ]),
        ],
        "shortcuts_title": "Keyboard shortcuts",
        "shortcuts": [("⌘N", "New document"), ("⌘O", "Open"), ("⌘S", "Save"), ("⌘P", "Print"),
                      ("⌘Z / ⌘⇧Z", "Undo / Redo"), ("⌘B / I / U", "Bold / Italic / Underline"),
                      ("⌘F", "Find"), ("⌘⌥F", "Find and replace"), ("⌘↩", "Page break"),
                      ("F7", "Spelling and grammar")],
        "shortcuts_head": ("Shortcut", "Action"),
        "footer": "On Windows use Ctrl instead of ⌘. Detailed guides: 1xag.com/office",
    },
    "vi": {
        "brand": "1xAIoffice",
        "title": "Chào mừng đến với 1xAIoffice – 1xDoc",
        "intro": "Bộ văn phòng miễn phí làm cho người Việt. Văn bản, bảng tính, trình chiếu mở và lưu được tệp "
                 "Microsoft Office, văn bản hành chính trình bày theo Nghị định 30, công cụ tiếng Việt có sẵn, và trợ "
                 "lý AI dùng tài khoản của chính bạn, chỉ xuất hiện khi bạn cần.",
        "callouts": [("Thanh trên cùng", "Mới ▾ tạo mọi loại tài liệu; Cửa sổ ▾ chuyển nhanh giữa các tệp đang mở."),
                     ("Các thẻ lệnh", "Trang đầu, Chèn, Bố cục, Tham chiếu, Xem lại, Xem: lệnh gom theo việc."),
                     ("Thẻ AI", "Hỏi AI, viết lại, chạy skill, soạn và kiểm văn bản NĐ30, ở cùng một chỗ."),
                     ("Thanh bên AI", "Mở ở mép phải khi cần; luôn cho biết đang dùng AI nào."),
                     ("Thanh trạng thái", "Số trang, số chữ, ngôn ngữ văn bản và thu phóng, luôn trong tầm mắt.")],
        "sections": [
            ("Bắt đầu trong một cú bấm", "start", [
                "Trang chủ có các thẻ lớn: văn bản, bảng tính, trình chiếu trống, và mẫu văn bản NĐ30 (công văn, tờ "
                "trình, quyết định, biên bản).",
                "Tài liệu gần đây xếp theo Hôm nay, Hôm qua, Trong 7 ngày, Cũ hơn, kèm vị trí, ngày sửa và dung lượng. "
                "Nhấn đúp để mở.",
                "Bấm Văn bản, Bảng tính hay Trình chiếu ở cột trái để vào trang riêng của ứng dụng đó.",
                "Nút VI / EN ở góc trên đổi ngôn ngữ giao diện; app khởi động lại trong vài giây.",
            ]),
            ("Trợ lý AI khi bạn cần", "sidebar", [
                "Dùng thẻ AI, thanh bên AI, hoặc bôi đen rồi bấm chuột phải: Hỏi AI, Viết lại, Chạy skill.",
                "Dùng AI của chính bạn: gói ChatGPT đang trả, khoá API (Groq, Gemini, OpenRouter, Mistral và nhiều hãng "
                "khác có gói miễn phí), hoặc AI chạy ngay trong máy để không gửi gì ra ngoài.",
                "Màn hình Tài khoản AI xếp hãng miễn phí lên đầu và mở sẵn trang lấy khoá cho bạn.",
                "Viết lại luôn có bản xem trước và hoàn tác một bước (⌘Z). Chỉ hỏi thì tài liệu không bị đổi.",
            ]),
            ("Văn bản hành chính theo Nghị định 30", "nd30", [
                "28 loại văn bản theo Phụ lục III Nghị định 30/2020/NĐ-CP, có khung nội dung mẫu và khối chữ ký, kể cả "
                "loại hai bên cùng ký.",
                "Điền hộp thoại: cơ quan ban hành, số, địa danh, ngày, trích yếu, nội dung và người ký.",
                "Kiểm thể thức NĐ30 rà mọi văn bản đang mở và sửa phần trang: khổ A4, lề, phông chữ.",
                "Công cụ hỗ trợ trình bày; nội dung và giá trị pháp lý do người ban hành chịu trách nhiệm.",
            ]),
            ("Công cụ tiếng Việt", "ribbon", [
                "Chuyển văn bản TCVN3 (ABC), VNI, VIQR sang Unicode; chuẩn hoá Unicode tiếng Việt.",
                "Bỏ dấu tiếng Việt cho tên tệp, mã số và địa chỉ thư.",
                "Đọc số và đọc số tiền thành chữ; hàm DOCSO, DOCTIEN trong 1xSheet.",
            ]),
            ("Việc của bạn luôn được lưu", None, [
                "Dữ liệu khôi phục được lưu mỗi 2 phút, và văn bản đã có tên tệp được lưu thẳng theo cùng nhịp.",
                "Mỗi lần lưu giữ thêm một bản sao lưu. Nếu app gặp sự cố, lần mở sau sẽ mời bạn khôi phục.",
                "Đổi nhịp hoặc tắt trong Công cụ ▸ Tuỳ chọn ▸ Tải/Lưu ▸ Chung.",
            ]),
            ("Lưu và chia sẻ", None, [
                "Văn bản mới được lưu dạng .docx, người dùng Microsoft Word mở được ngay.",
                "Tệp ▸ Xuất ra PDF để gửi hoặc đăng tải.",
            ]),
        ],
        "shortcuts_title": "Phím tắt",
        "shortcuts": [("⌘N", "Tạo văn bản mới"), ("⌘O", "Mở"), ("⌘S", "Lưu"), ("⌘P", "In"),
                      ("⌘Z / ⌘⇧Z", "Hoàn tác / Làm lại"), ("⌘B / I / U", "Đậm / Nghiêng / Gạch chân"),
                      ("⌘F", "Tìm"), ("⌘⌥F", "Tìm và thay thế"), ("⌘↩", "Ngắt trang"),
                      ("F7", "Chính tả và ngữ pháp")],
        "shortcuts_head": ("Phím", "Việc"),
        "footer": "Trên Windows dùng Ctrl thay cho ⌘. Hướng dẫn chi tiết: 1xag.com/office",
    },
}

SHEET_TEXT = {
    "en": {"sheet": "Get started", "title": "Welcome to 1xAIoffice – 1xSheet",
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
                    "1xAIoffice functions: Excel shows their last values but cannot recalculate them."],
           "chart": "Amount by item",
           "ai_title": "AI in 1xSheet",
           "ai": ["Open the AI sidebar on the right edge, or the AI tab: Ask AI about the sheet, run a skill.",
                  "Use your own AI account: the ChatGPT plan you pay for, a free-tier API key, or AI on this computer.",
                  "Asking never changes your cells. Your work is saved every 2 minutes."]},
    "vi": {"sheet": "Bắt đầu", "title": "Chào mừng đến với 1xAIoffice – 1xSheet",
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
                    "Tệp được lưu dạng .xlsx để người dùng Excel mở được. DOCSO và DOCTIEN là hàm của 1xAIoffice: "
                    "Excel hiện giá trị đã tính nhưng không tính lại được."],
           "chart": "Thành tiền theo mặt hàng",
           "ai_title": "AI trong 1xSheet",
           "ai": ["Mở thanh bên AI ở mép phải, hoặc thẻ AI: hỏi AI về bảng tính, chạy skill.",
                  "Dùng tài khoản AI của chính bạn: gói ChatGPT đang trả, khoá API có gói miễn phí, hoặc AI trong máy.",
                  "Chỉ hỏi thì ô dữ liệu không bị đổi. Việc của bạn được lưu mỗi 2 phút."]},
}

SLIDE_TEXT = {
    "en": [
        ("Welcome to 1xAIoffice – 1xSlide", "Presentations that open in PowerPoint, made in Vietnam. Press F5 to play."),
        ("Start in one click", None, "start"),
        ("The workspace", None, "impress"),
        ("An AI assistant when you need it", ["Open the AI sidebar on the right edge or the AI tab: Ask AI, run a skill.",
                                              "Use your own AI: your ChatGPT plan, a free-tier API key, or AI on this computer.",
                                              "Nothing changes until you accept it; everything is saved every 2 minutes."]),
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
        ("Chào mừng đến với 1xAIoffice – 1xSlide", "Bài trình chiếu mở được bằng PowerPoint, làm tại Việt Nam. Bấm F5 để trình chiếu."),
        ("Bắt đầu trong một cú bấm", None, "start"),
        ("Màn hình làm việc", None, "impress"),
        ("Trợ lý AI khi bạn cần", ["Mở thanh bên AI ở mép phải hoặc thẻ AI: hỏi AI, chạy skill.",
                                   "Dùng AI của bạn: gói ChatGPT, khoá API có gói miễn phí, hoặc AI ngay trong máy.",
                                   "Không gì thay đổi cho tới khi bạn đồng ý; mọi thứ được lưu mỗi 2 phút."]),
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
def gradient(start, end, angle=0):
    g = uno.createUnoStruct("com.sun.star.awt.Gradient")
    g.Style = uno.Enum("com.sun.star.awt.GradientStyle", "LINEAR")
    g.StartColor, g.EndColor, g.Angle = start, end, angle
    g.StartIntensity = g.EndIntensity = 100
    return g


def make_doc(office, lang, out):
    """Kiểu tài liệu chào mừng của WPS: trang bìa nền chuyển màu xanh nhạt, ảnh app lớn kèm chú thích đánh số, rồi
    mỗi tính năng một mục có tiêu đề màu, đoạn giải thích và ảnh thật. Phông Noto (đi kèm app, đủ dấu tiếng Việt)."""
    t = DOC_TEXT[lang]
    doc = office.new("swriter")
    text = doc.Text
    pages = doc.StyleFamilies.getByName("PageStyles")
    for name in ("Standard", "First Page"):
        page = pages.getByName(name)
        page.Width, page.Height = 21000, 29700
        page.LeftMargin = page.RightMargin = 2000
        page.TopMargin = page.BottomMargin = 1800
    cover = pages.getByName("First Page")
    cover.FillStyle = uno.Enum("com.sun.star.drawing.FillStyle", "GRADIENT")
    cover.FillGradient = gradient(0xDCE7FF, 0xFFFFFF)            # xanh nhạt trên, trắng dưới, như bìa WPS
    cover.FollowStyle = "Standard"
    width = 21000 - 4000
    paras = doc.StyleFamilies.getByName("ParagraphStyles")
    paras.getByName("Standard").CharFontName = SANS
    paras.getByName("Text body").CharFontName = SANS
    paras.getByName("Text body").CharHeight = 10.5
    paras.getByName("Text body").ParaBottomMargin = 180
    for name, size, color in (("Title", 26, INK), ("Heading 1", 17, DOC), ("Heading 2", 13, INK)):
        st = paras.getByName(name)
        st.CharFontName, st.CharHeight, st.CharColor = SERIF, size, color
    paras.getByName("Heading 1").ParaTopMargin = 500
    cur = text.createTextCursor()
    first = [True]

    def para(s, style="Text body", center=False, color=None, size=None, bold=False):
        if not first[0]:
            text.insertControlCharacter(cur, 0, False)
        first[0] = False
        cur.ParaStyleName = style
        cur.ParaLeftMargin = cur.ParaFirstLineIndent = 0     # mỗi đoạn mới bắt đầu không thụt
        cur.ParaAdjust = CENTER if center else 0
        for prop_name, value in (("CharColor", color), ("CharHeight", size)):
            if value is not None:
                setattr(cur, prop_name, value)
        if bold:
            cur.CharWeight = 150.0
        text.insertString(cur, s, False)
        for prop_name in ("CharColor", "CharHeight", "CharWeight"):
            cur.setPropertyToDefault(prop_name)

    def rich(term, rest, number=None):
        """Một dòng "① Thuật ngữ: giải thích" với thuật ngữ in đậm."""
        para("", "Text body")
        cur.ParaLeftMargin, cur.ParaFirstLineIndent = 700, -700
        if number is not None:
            cur.CharColor, cur.CharWeight = ACCENT, 150.0
            text.insertString(cur, f"{number}\t", False)
        cur.CharColor, cur.CharWeight = INK, 150.0
        text.insertString(cur, term + ": ", False)
        cur.setPropertyToDefault("CharColor")
        cur.setPropertyToDefault("CharWeight")
        text.insertString(cur, rest, False)

    def image(path, width_mm100=None):
        if not Path(path).is_file():
            return
        para("", center=True)
        g = office.graphic(path)
        obj = doc.createInstance("com.sun.star.text.TextGraphicObject")
        obj.Graphic = g
        obj.AnchorType = uno.Enum("com.sun.star.text.TextContentAnchorType", "AS_CHARACTER")
        obj.Size = fit(g, width_mm100 or width)
        text.insertTextContent(cur, obj, False)

    def bullets(items):
        for item in items:
            para("•\t" + item)          # vẽ dấu đầu dòng bằng tay: gán kiểu List Bullet qua UNO làm 26.8 ngã trên macOS
            cur.ParaLeftMargin, cur.ParaFirstLineIndent = 600, -400

    # --- trang bìa
    para(t["brand"], "Subtitle", center=True, color=ACCENT, bold=True)
    cur.PageDescName = "First Page"
    para(t["title"], "Title", center=True)
    para(t["intro"], center=True, color=MUTED)
    image(shot("writer", lang))
    for i, (term, rest) in enumerate(t["callouts"]):
        rich(term, rest, "①②③④⑤⑥"[i])
    # --- từng tính năng
    for n, (heading, pic, items) in enumerate(t["sections"]):
        para(heading, "Heading 1")
        if n == 0:
            cur.BreakType = uno.Enum("com.sun.star.style.BreakType", "PAGE_BEFORE")
        bullets(items)
        if pic:
            image(shot(pic, lang), int(width * (0.55 if pic == "sidebar" else 0.95)))
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
            tc = cell.Text.createTextCursor()
            tc.gotoEnd(True)
            tc.CharFontName = SANS
            if r == 0:
                cell.BackColor = DOC
                tc.CharColor, tc.CharWeight = 0xFFFFFF, 150.0
            elif r % 2 == 0:
                cell.BackColor = 0xF1F5FF
    end = text.createTextCursor()
    end.gotoEnd(False)
    cur = end
    # --- giới thiệu và ủng hộ (từ branding/about.json, cùng nguồn với README)
    about = ABOUT[lang]
    para(about["title"], "Heading 1")
    para(about["tagline"])
    para(about["mission_title"] + ": " + about["mission"])
    para(about["vision_title"] + ": " + about["vision"])
    for key in ("available", "different"):
        para(about[key + "_title"], "Heading 2")
        bullets(about[key])
    d = ABOUT["donate"]
    para(about["support_title"], "Heading 2")
    para(about["support"])
    # Mã VietQR tĩnh, sinh bởi scripts/brand/make-brand.py và kiểm bằng scripts/check-vietqr.sh.
    image(REPO / "branding" / "out" / "vietqr.svg", 4000)
    para(f'{d["bank"]} · {d["account"]} · {d["holder"]}', center=True)
    para(f'{about["support_link"]}: {d["url_" + lang]}', center=True)
    para(t["footer"], center=True, color=MUTED)
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
    cell("A1").CharHeight, cell("A1").CharWeight, cell("A1").CharColor = 22, 150.0, INK
    cell("A1").CharFontName = SERIF
    cell("A2").String = t["intro"]
    cell("A2").CharColor = MUTED
    band = cell("A1:F2")                    # dải tiêu đề nền xanh lá nhạt, như trang chào của WPS Sheets
    band.CellBackColor = 0xE3F5EA
    sheet.Rows.getByIndex(0).Height = 1300
    sheet.Rows.getByIndex(1).Height = 700
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
        r = tip_row + 1 + i
        cell(f"A{r}").String = f"{i + 1}. {tip}"
        line = cell(f"A{r}:F{r}")               # gộp cả hàng và cho xuống dòng: mẹo dài không bị cắt chữ
        line.merge(True)
        line.IsTextWrapped = True
    # Chart next to the tips.
    rect = uno.createUnoStruct("com.sun.star.awt.Rectangle")
    rect.X, rect.Y, rect.Width, rect.Height = 1000, sheet.Rows.getByIndex(tip_row + 7).Position.Y, 20000, 6200
    chart_range = uno.createUnoStruct("com.sun.star.table.CellRangeAddress")
    chart_range.Sheet, chart_range.StartColumn, chart_range.EndColumn = 0, 4, 4
    chart_range.StartRow, chart_range.EndRow = top - 1, last - 1
    sheet.Charts.addNewByName("Amounts", rect, (chart_range,), True, False)
    chart = sheet.Charts.getByName("Amounts").EmbeddedObject
    chart.HasMainTitle = True
    chart.Title.String = t["chart"]
    chart.HasLegend = False
    chart.getData().setRowDescriptions(tuple(r[1] for r in t["rows"]))  # item names as categories
    # Mục AI: tiêu đề màu, ba dòng giải thích, ảnh app thật bên dưới.
    ai_row = tip_row + 8 + 18                # dưới đáy biểu đồ (cao 6,2 cm), không bị biểu đồ che
    sheet.Rows.getByIndex(ai_row - 1).IsStartOfNewPage = True   # khi in: mục AI và ảnh nằm trọn trang 2
    cell(f"A{ai_row}").String = t["ai_title"]
    cell(f"A{ai_row}").CharWeight, cell(f"A{ai_row}").CharHeight, cell(f"A{ai_row}").CharColor = 150.0, 15, AI
    cell(f"A{ai_row}").CharFontName = SERIF
    for i, line in enumerate(t["ai"]):
        cell(f"A{ai_row + 1 + i}").String = "•  " + line
    pic_path = shot("calc", lang)
    if pic_path.is_file():
        g = office.graphic(pic_path)
        pic = doc.createInstance("com.sun.star.drawing.GraphicObjectShape")
        sheet.DrawPage.add(pic)
        pic.Graphic = g
        pic.Size = fit(g, 22000)                # vừa trang ngang A4, cả mục AI nằm gọn một trang
        pos = uno.createUnoStruct("com.sun.star.awt.Point")
        pos.X, pos.Y = 1000, sheet.Rows.getByIndex(ai_row + 4).Position.Y
        pic.Position = pos
    # In: khổ ngang, co vừa một trang theo bề ngang (cột Bằng chữ không bị tách sang trang riêng).
    page = doc.StyleFamilies.getByName("PageStyles").getByName(sheet.PageStyle)
    page.IsLandscape = True
    page.Width, page.Height = max(page.Width, page.Height), min(page.Width, page.Height)
    page.ScaleToPagesX, page.ScaleToPagesY = 1, 0
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
    bg.FillStyle = uno.Enum("com.sun.star.drawing.FillStyle", "GRADIENT")
    bg.FillGradient = gradient(0xFFF1E6, 0xFFFFFF)     # cam nhạt (màu 1xSlide) sang trắng
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
