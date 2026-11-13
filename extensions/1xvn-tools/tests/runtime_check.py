# SPDX-License-Identifier: MPL-2.0
# Run with the office's bundled Python against a headless soffice started with ONEX_TOOLS_SILENT=1
# (scripts/build-macos.sh step "tools"). Calls the 1xvn-tools commands through the dispatcher on real documents.
# Usage: runtime_check.py <pipe> writer|calc. Writer and Calc run in separate office sessions: on macOS a headless
# upstream 26.8 aborts in AquaSalMenu::setMainMenu when a Calc document is created after a Writer one.
import sys
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def connect(pipe):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            return resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
        except Exception:  # noqa: BLE001 - office still starting
            time.sleep(1)
    sys.exit("không kết nối được tới soffice")


def main():
    ctx = connect(sys.argv[1])
    part = sys.argv[2]
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    dispatcher = smgr.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)
    failures = []

    def check(name, got, want):
        ok = got == want
        print(f"{'OK  ' if ok else 'SAI '} {name}: {got!r}" + ("" if ok else f" (mong đợi {want!r})"))
        if not ok:
            failures.append(name)

    def run(doc, cmd):
        dispatcher.executeDispatch(doc.getCurrentController().getFrame(), f"vnd.1x.tools:{cmd}", "", 0, ())

    if part == "writer":
        writer_checks(desktop, prop, run, check)
    elif part == "nd30":
        nd30_checks(desktop, prop, run, check)
    elif part == "nd30check":
        nd30_check_checks(desktop, prop, run, check)
    elif part == "xlsxwarn":
        xlsx_warning_checks(desktop, prop, run, check)
    elif part == "csv":
        csv_checks(desktop, prop, run, check)
    else:
        calc_checks(desktop, prop, run, check)
    try:
        desktop.terminate()
    except Exception:  # noqa: BLE001 - the bridge drops when the office exits
        pass
    sys.exit(1 if failures else 0)


def writer_checks(desktop, prop, run, check):
    # Writer: TCVN3 paragraph in a .VnTime font + one Unicode paragraph that must stay untouched.
    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, (prop("Hidden", False),))
    text = doc.getText()
    cur = text.createTextCursor()
    cur.CharFontName = ".VnTime"
    text.insertString(cur, "Céng hoµ x· héi chñ nghÜa ViÖt Nam", False)
    text.insertControlCharacter(cur, 0, False)  # paragraph break
    cur.CharFontName = "Liberation Serif"
    text.insertString(cur, "Đã là Unicode", False)
    run(doc, "ConvertTCVN3")
    paras = text.getString().replace("\r\n", "\n").split("\n")
    check("Writer TCVN3 -> Unicode", paras[0], "Cộng hoà xã hội chủ nghĩa Việt Nam")
    check("Writer Unicode giữ nguyên", paras[1], "Đã là Unicode")
    first = text.createEnumeration().nextElement()
    check("Writer đổi phông", first.createEnumeration().nextElement().CharFontName, "Times New Roman")
    check("Writer hoàn tác một bước", doc.UndoManager.getCurrentUndoActionTitle(), "Convert TCVN3 to Unicode")

    # Writer: number in the selection -> words.
    text.setString("1.250.000")
    vc = doc.getCurrentController().getViewCursor()
    vc.gotoStart(False)
    vc.gotoEnd(True)
    run(doc, "MoneyToWords")
    check("Writer đọc số tiền", text.getString(), "Một triệu hai trăm năm mươi nghìn đồng")

    doc.close(True)


def csv_checks(desktop, prop, run, check):
    """Chuỗi tuỳ chọn mở CSV an toàn phải thật sự giữ nguyên dữ liệu trong Calc thật.

    Ở đây nạp thẳng tệp bằng chuỗi tuỳ chọn, không đi qua lệnh trên menu: soffice headless trên macOS dừng khi mở
    tài liệu thứ hai trong một phiên, mà lệnh đó luôn mở tài liệu mới. Phần nối lệnh được thử bằng tay trên app có
    giao diện; phần quyết định đúng sai là chuỗi tuỳ chọn, và nó được kiểm thật ở đây.
    """
    import os
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pythonpath"))
    from vn1x import csvsafe
    path = os.environ["ONEX_TOOLS_CSV_PATH"]
    rows = ['ho_ten,dien_thoai,cccd,ngay,ghi_chu',
            'Nguyễn Văn A,0912345678,001234567890,1/2,=1+1',
            'Trần Thị B,0987654321,079300012345,10/3,"Hà Nội, Việt Nam"']
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(rows) + "\n")
    # Một phiên trước bị dừng giữa chừng để lại tệp khoá; soffice headless không hỏi được nên sẽ từ chối mở.
    lock = os.path.join(os.path.dirname(path), "." + "~lock." + os.path.basename(path) + "#")
    if os.path.exists(lock):
        os.remove(lock)
    options = csvsafe.filter_options(separator=csvsafe.guess_separator(rows[0]))
    doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(path), "_blank", 0,
                                       (prop("FilterName", "Text - txt - csv (StarCalc)"),
                                        prop("FilterOptions", options), prop("Hidden", True)))
    check("Nạp được CSV bằng chuỗi tuỳ chọn an toàn", doc is not None, True)
    if doc is None:
        return
    sheet = doc.getSheets().getByIndex(0)
    at = lambda col, row: sheet.getCellByPosition(col, row).getString()  # noqa: E731
    check("CSV giữ số 0 đầu của số điện thoại", at(1, 1), "0912345678")
    check("CSV giữ nguyên số căn cước", at(2, 1), "001234567890")
    check("CSV không đổi 1/2 thành ngày", at(3, 1), "1/2")
    check("CSV không chạy ô bắt đầu bằng =", at(4, 1), "=1+1")
    check("CSV giữ dấu phẩy trong ô có dấu bao", at(4, 2), "Hà Nội, Việt Nam")
    check("CSV đọc đúng chữ tiếng Việt", at(0, 1), "Nguyễn Văn A")
    doc.close(True)


def xlsx_warning_checks(desktop, prop, run, check):
    """Lưu bảng tính có hàm riêng sang .xlsx thì phải nhắc người dùng. soffice chạy với ONEX_TOOLS_WARN_OUT."""
    import os
    import tempfile
    out = os.environ.get("ONEX_TOOLS_WARN_OUT")
    if out and os.path.exists(out):
        os.remove(out)
    doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, (prop("Hidden", False),))
    sheet = doc.getSheets().getByIndex(0)
    sheet.getCellByPosition(0, 0).setValue(21)
    sheet.getCellByPosition(1, 0).setFormula("=DOCSO(A1)")
    doc.calculateAll()
    folder = tempfile.mkdtemp()
    for name, filt in (("plain.ods", "calc8"), ("excel.xlsx", "Calc MS Excel 2007 XML")):
        url = uno.systemPathToFileUrl(os.path.join(folder, name))
        doc.storeToURL(url, (prop("FilterName", filt), prop("Overwrite", True)))
    # storeToURL không đổi URL tài liệu nên không bắn sự kiện lưu: dùng storeAsURL cho phép kiểm thật.
    doc.storeAsURL(uno.systemPathToFileUrl(os.path.join(folder, "thucte.xlsx")),
                   (prop("FilterName", "Calc MS Excel 2007 XML"), prop("Overwrite", True)))
    text = open(out, encoding="utf-8").read() if out and os.path.exists(out) else ""
    check("Lưu .xlsx có hàm riêng thì nhắc", ".xlsx" in text and "DOCSO" in text, True)
    doc.storeAsURL(uno.systemPathToFileUrl(os.path.join(folder, "thucte.ods")),
                   (prop("FilterName", "calc8"), prop("Overwrite", True)))
    after = open(out, encoding="utf-8").read() if out and os.path.exists(out) else ""
    check("Lưu .ods thì không nhắc thêm", after.count("DOCSO"), text.count("DOCSO"))
    doc.close(True)


def nd30_check_checks(desktop, prop, run, check):
    """Lệnh kiểm thể thức trên một tài liệu sai chuẩn: phải tìm ra lỗi rồi sửa được phần trang.
    soffice chạy với ONEX_TOOLS_CHECK_OUT (nơi ghi kết quả) và ONEX_TOOLS_CHECK_FIX=1 (coi như người dùng đồng ý sửa).
    """
    import json
    import os
    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, (prop("Hidden", False),))
    pages = doc.getStyleFamilies().getByName("PageStyles")
    std = pages.getByName("Standard")
    std.Width, std.Height = 21590, 27940          # khổ Letter
    std.LeftMargin = std.RightMargin = 2500       # lề sai
    styles = doc.getStyleFamilies().getByName("ParagraphStyles")
    styles.getByName("Standard").CharFontName = "Arial"
    doc.getText().setString("Một đoạn nội dung bất kỳ, không có Quốc hiệu.")
    run(doc, "Nd30Check")
    out = os.environ.get("ONEX_TOOLS_CHECK_OUT")
    found = json.load(open(out, encoding="utf-8")) if out and os.path.exists(out) else []
    keys = sorted(i["key"] for i in found)
    check("Kiểm NĐ30 tìm ra lỗi trang", [k for k in keys if k in ("page_size", "margin_left_mm", "font")],
          ["font", "margin_left_mm", "page_size"])
    check("Kiểm NĐ30 báo thiếu Quốc hiệu", "quoc_hieu" in keys, True)
    check("Kiểm NĐ30 sửa được phần trang", all(i["fix"] for i in found if i["key"] in
                                                ("page_size", "margin_left_mm", "font")), True)
    near = lambda got, want: all(abs(g - w) <= 2 for g, w in zip(got, want))  # noqa: E731
    check("Kiểm NĐ30 đã sửa về A4", near((std.Width, std.Height), (21000, 29700)), True)
    check("Kiểm NĐ30 đã sửa lề trái", abs(std.LeftMargin - 3000) <= 2, True)
    check("Kiểm NĐ30 đã sửa phông", styles.getByName("Standard").CharFontName, "Times New Roman")


def nd30_checks(desktop, prop, run, check):
    # The soffice process was started with ONEX_TOOLS_ND30_FIELDS (see scripts/build-macos.sh), so the command
    # builds the document without opening the dialog.
    start = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, (prop("Hidden", False),))
    run(start, "Nd30Document")
    doc = start  # a blank, unmodified Writer document is filled in place
    check("NĐ30 dựng vào tài liệu trống", doc.getTextTables().getCount(), 2)
    pages = doc.getStyleFamilies().getByName("PageStyles")
    std = pages.getByName("Standard")
    # Writer stores page sizes in twips: 1/100 mm values come back with ±0.01 mm rounding.
    near = lambda got, want: all(abs(g - w) <= 2 for g, w in zip(got, want))  # noqa: E731
    check("NĐ30 khổ A4 (±0,02 mm)", near((std.Width, std.Height), (21000, 29700)), True)
    check("NĐ30 lề 20/20/30/15 mm (±0,02 mm)",
          near((std.TopMargin, std.BottomMargin, std.LeftMargin, std.RightMargin), (2000, 2000, 3000, 1500)), True)
    check("NĐ30 trang đầu không có số trang", pages.getByName("First Page").HeaderIsOn, False)
    check("NĐ30 trang sau có số trang", std.HeaderIsOn, True)
    tables = doc.getTextTables()
    head = tables.getByIndex(0)
    check("NĐ30 trang đầu dùng kiểu First Page", head.PageDescName, "First Page")
    left = head.getCellByName("A1").getText().getString().replace("\r\n", "\n").split("\n")
    right = head.getCellByName("B1").getText().getString().replace("\r\n", "\n").split("\n")
    check("NĐ30 cơ quan chủ quản", left[0], "UBND TỈNH ĐÀ NẴNG")
    check("NĐ30 cơ quan ban hành", left[1], "SỞ KHOA HỌC VÀ CÔNG NGHỆ")
    check("NĐ30 số ký hiệu", [x for x in left if x.startswith("Số:")], ["Số: 05/TTr-SKHCN"])
    check("NĐ30 quốc hiệu", right[0], "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    check("NĐ30 tiêu ngữ", right[1], "Độc lập - Tự do - Hạnh phúc")
    check("NĐ30 địa danh ngày", [x for x in right if x.startswith("Đà Nẵng")], ["Đà Nẵng, ngày 05 tháng 01 năm 2026"])
    first_para = head.getCellByName("B1").getText().createEnumeration().nextElement()
    check("NĐ30 quốc hiệu Times New Roman 13 đậm",
          (first_para.CharFontName, first_para.CharHeight, first_para.CharWeight), ("Times New Roman", 13.0, 150.0))
    body = doc.getText().getString()
    check("NĐ30 tên loại", "TỜ TRÌNH" in body, True)
    check("NĐ30 trích yếu", "Về việc phê duyệt kế hoạch năm 2026" in body, True)
    paras = doc.getText().createEnumeration()
    content = None
    while paras.hasMoreElements():
        p = paras.nextElement()
        if p.supportsService("com.sun.star.text.Paragraph") and p.getString() == "Đoạn một.":
            content = p
    check("NĐ30 nội dung canh đều, lùi đầu dòng 1,27 cm, cỡ 14",
          content is not None and (content.ParaAdjust, content.ParaFirstLineIndent, content.CharHeight),
          (2, 1270, 14.0))
    sign = tables.getByIndex(1)
    signer = sign.getCellByName("B1").getText().getString()
    check("NĐ30 quyền hạn ký", signer.startswith("KT. GIÁM ĐỐC"), True)
    check("NĐ30 họ tên", signer.rstrip().endswith("Nguyễn Văn A"), True)
    receivers = sign.getCellByName("A1").getText().getString().replace("\r\n", "\n").split("\n")
    check("NĐ30 nơi nhận", (receivers[0], receivers[-1]), ("Nơi nhận:", "- Lưu: VT, VP, 02b."))
    loc = sign.getCellByName("B1").getText().createTextCursor().CharLocale
    check("NĐ30 ngôn ngữ chữ tiếng Việt", (loc.Language, loc.Country), ("vi", "VN"))
    out = __import__("os").environ.get("ONEX_TOOLS_ND30_PNG")
    if out:
        doc.storeToURL(uno.systemPathToFileUrl(out), (prop("FilterName", "writer_png_Export"),))
    doc.close(True)


def calc_checks(desktop, prop, run, check):
    # Calc: numbers in A1:A2 -> words in B1:B2; B3 occupied -> skipped.
    calc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, (prop("Hidden", False),))
    sheet = calc.getSheets().getByIndex(0)
    sheet.getCellByPosition(0, 0).setValue(21)
    sheet.getCellByPosition(0, 1).setValue(105)
    sheet.getCellByPosition(0, 2).setValue(7)
    sheet.getCellByPosition(1, 2).setString("đã có")
    calc.getCurrentController().select(sheet.getCellRangeByName("A1:A3"))
    run(calc, "NumberToWords")
    check("Calc A1 -> B1", sheet.getCellByPosition(1, 0).getString(), "hai mươi mốt")
    check("Calc A2 -> B2", sheet.getCellByPosition(1, 1).getString(), "một trăm lẻ năm")
    check("Calc B3 không bị ghi đè", sheet.getCellByPosition(1, 2).getString(), "đã có")
    sheet.getCellByPosition(2, 0).setString("Nguyễn Thị Ánh")
    calc.getCurrentController().select(sheet.getCellRangeByName("C1"))
    run(calc, "RemoveDiacritics")
    check("Calc bỏ dấu", sheet.getCellByPosition(2, 0).getString(), "Nguyen Thi Anh")
    # Sheet functions from the add-in.
    for ref, formula, want in [("D1", "=DOCSO(21)", "Hai mươi mốt"),
                               ("D2", '=DOCSO(105;"linh")', "Một trăm linh năm"),
                               ("D3", "=DOCSO(3.25)", "Ba phẩy hai mươi lăm"),
                               ("D4", "=DOCTIEN(1250000)", "Một triệu hai trăm năm mươi nghìn đồng"),
                               ("D5", '=DOCTIEN(100;"USD")', "Một trăm USD"),
                               ("D6", "=DOCTIEN(A1*1000)", "Hai mươi mốt nghìn đồng")]:
        cell = sheet.getCellRangeByName(ref)
        cell.setFormula(formula)
        check(f"Calc {formula}", cell.getString(), want)
    bad = sheet.getCellRangeByName("D7")
    bad.setFormula("=DOCSO(10^20)")
    check("Calc =DOCSO(10^20) báo lỗi", bad.getError() != 0, True)
    sheet.getCellByPosition(0, 6).setString("Nguyễn Thị Ánh Nguyệt")
    for col, formula in ((1, "=TACHHO(A7)"), (2, "=TACHDEM(A7)"), (3, "=TACHTEN(A7)")):
        sheet.getCellByPosition(col, 6).setFormula(formula)
    calc.calculateAll()
    check("Calc tách họ tên", tuple(sheet.getCellByPosition(c, 6).getString() for c in (1, 2, 3)),
          ("Nguyễn", "Thị Ánh", "Nguyệt"))
    sheet.getCellByPosition(0, 7).setString("Lê Đông")
    sheet.getCellByPosition(0, 8).setString("Lê Dung")
    sheet.getCellByPosition(1, 7).setFormula("=SAPTEN(A8)")
    sheet.getCellByPosition(1, 8).setFormula("=SAPTEN(A9)")
    calc.calculateAll()
    # Thứ tự tiếng Việt: Dung đứng trước Đông, nên khoá của Dung phải nhỏ hơn.
    check("Calc =SAPTEN sắp đúng d trước đ",
          sheet.getCellByPosition(1, 8).getString() < sheet.getCellByPosition(1, 7).getString(), True)
    calc.close(True)


main()
