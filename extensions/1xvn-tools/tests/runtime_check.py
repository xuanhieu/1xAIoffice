# SPDX-License-Identifier: MPL-2.0
# Run with the office's bundled Python against a headless soffice started with ONEX_TOOLS_SILENT=1
# (scripts/build-macos.sh step "tools"). Calls the 1xvn-tools commands through the dispatcher on real documents.
# Usage: runtime_check.py <pipe> writer|calc. Writer and Calc run in separate office sessions: on macOS a headless
# LibreOffice 26.8 aborts in AquaSalMenu::setMainMenu when a Calc document is created after a Writer one.
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
    calc.close(True)


main()
