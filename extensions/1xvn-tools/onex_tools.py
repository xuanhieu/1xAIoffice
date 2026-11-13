# SPDX-License-Identifier: MPL-2.0
"""ProtocolHandler "vnd.1x.tools:" của 1xVnOffice: các lệnh tiếng Việt cho Writer và Calc,
và add-in hàm bảng tính DOCSO, DOCTIEN (interface org.onexvn.tools.XVnSheetFunctions, types/onexvn-tools.rdb).

Lệnh: NumberToWords, MoneyToWords, RemoveDiacritics, NormalizeUnicode, ConvertTCVN3.
Logic chữ nằm trong pythonpath/vn1x (có test riêng, không cần UNO); file này chỉ nối lệnh với tài liệu.
Biến môi trường ONEX_TOOLS_SILENT=1 tắt hộp thông báo (dùng cho kiểm thử tự động).
"""
import os

import uno
import unohelper
from com.sun.star.frame import XDispatch, XDispatchProvider
from com.sun.star.lang import XInitialization, XServiceInfo
from com.sun.star.task import XJob

import datetime
import json

from vn1x import docops
from vn1x import nd30
from vn1x.numwords import NumberWordsError, money_to_words, number_to_words, parse_number_text
from vn1x.vntext import normalize, remove_diacritics, tcvn3_to_unicode

IMPL = "org.1xvnoffice.tools.ProtocolHandler"
PROTOCOL = "vnd.1x.tools:"
TCVN3_REPLACEMENT_FONT = "Times New Roman"

TEXTS = {
    "en": {
        "title": "1xVnOffice",
        "words_done": "Converted {n} number(s) to words.",
        "words_calc": "Wrote words for {n} cell(s) into the cell on the right; {k} skipped because that cell was not empty.",
        "not_number": "The selection is not a number: {text}",
        "select_number": "Select a number first.",
        "done": "Changed {n} text part(s).",
        "unsupported": "This command works in Writer and Calc documents.",
        "nd30_error": "Cannot create the document: {err}",
    },
    "vi": {
        "title": "1xVnOffice",
        "words_done": "Đã đọc {n} số thành chữ.",
        "words_calc": "Đã ghi chữ cho {n} ô vào ô bên phải; bỏ qua {k} ô vì ô bên phải không trống.",
        "not_number": "Vùng chọn không phải số: {text}",
        "select_number": "Hãy chọn một số trước.",
        "done": "Đã đổi {n} đoạn chữ.",
        "unsupported": "Lệnh này dùng trong tài liệu Writer và Calc.",
        "nd30_error": "Không tạo được văn bản: {err}",
    },
}


def _ui_lang(ctx):
    try:
        provider = ctx.ServiceManager.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
        arg = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        arg.Name, arg.Value = "nodepath", "/org.openoffice.Office.Linguistic/General"
        node = provider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (arg,))
        return "vi" if node.getPropertyValue("UILocale").startswith("vi") else "en"
    except Exception:  # noqa: BLE001 - fall back to English
        return "en"


class Handler(unohelper.Base, XDispatchProvider, XDispatch, XInitialization, XServiceInfo):
    def __init__(self, ctx, *args):
        self.ctx = ctx
        self.frame = None

    # XInitialization
    def initialize(self, args):
        if args:
            self.frame = args[0]

    # XDispatchProvider
    def queryDispatch(self, url, target, flags):
        return self if url.Protocol == PROTOCOL else None

    def queryDispatches(self, requests):
        return tuple(self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags) for r in requests)

    # XDispatch
    def addStatusListener(self, listener, url):
        state = uno.createUnoStruct("com.sun.star.frame.FeatureStateEvent")
        state.FeatureURL, state.IsEnabled, state.Requery, state.Source = url, True, False, self
        listener.statusChanged(state)

    def removeStatusListener(self, listener, url):
        pass

    def dispatch(self, url, args):
        if url.Path == "Nd30Document":  # works from any module: creates a new Writer document
            self.t = TEXTS[_ui_lang(self.ctx)]
            self.cmd_Nd30Document()
            return
        doc = self.frame.getController().getModel() if self.frame else None
        if doc is None:
            return
        handler = getattr(self, "cmd_" + url.Path, None)
        if handler is None:
            return
        self.t = TEXTS[_ui_lang(self.ctx)]
        is_writer = doc.supportsService("com.sun.star.text.TextDocument")
        is_calc = doc.supportsService("com.sun.star.sheet.SpreadsheetDocument")
        if not (is_writer or is_calc):
            self.message(self.t["unsupported"])
            return
        handler(doc, is_writer)

    # XServiceInfo
    def getImplementationName(self):
        return IMPL

    def supportsService(self, name):
        return name == "com.sun.star.frame.ProtocolHandler"

    def getSupportedServiceNames(self):
        return ("com.sun.star.frame.ProtocolHandler",)

    # Commands
    def _words(self, doc, is_writer, func, title):
        if not is_writer:
            n, k = docops.calc_numbers_to_right(doc, func, title)
            self.message(self.t["words_calc"].format(n=n, k=k))
            return
        ranges = docops._writer_selection(doc)
        if not ranges:
            self.message(self.t["select_number"])
            return
        try:
            values = [parse_number_text(r.getString()) for r in ranges]
        except NumberWordsError:
            self.message(self.t["not_number"].format(text=ranges[0].getString()[:60]))
            return
        with docops._undo(doc, title):
            for r, v in zip(ranges, values):
                r.setString(func(v))
        self.message(self.t["words_done"].format(n=len(ranges)))

    def cmd_NumberToWords(self, doc, is_writer):
        self._words(doc, is_writer, lambda v: number_to_words(v), "Number to words")

    def cmd_MoneyToWords(self, doc, is_writer):
        self._words(doc, is_writer, lambda v: money_to_words(v), "Amount in words")

    def _text(self, doc, is_writer, func, title, portion_filter=None, after=None):
        if is_writer:
            n = docops.writer_transform(doc, func, title, portion_filter, after)
        else:
            n = docops.calc_transform_text(doc, func, title)
        self.message(self.t["done"].format(n=n))

    def cmd_RemoveDiacritics(self, doc, is_writer):
        self._text(doc, is_writer, remove_diacritics, "Remove diacritics")

    def cmd_NormalizeUnicode(self, doc, is_writer):
        self._text(doc, is_writer, normalize, "Normalize Unicode")

    def cmd_ConvertTCVN3(self, doc, is_writer):
        if not is_writer:
            self._text(doc, False, lambda s: tcvn3_to_unicode(s)[0], "Convert TCVN3 to Unicode")
            return
        # Không chọn gì: chỉ đổi các đoạn dùng phông TCVN3 (.VnTime, .VnArialH…) rồi đặt phông Unicode.
        # Phông kết thúc bằng "H" là phông chữ hoa. Có vùng chọn: đổi vùng chọn theo yêu cầu người dùng.
        upper_font = {}

        def is_tcvn3(portion):
            name = (portion.CharFontName or "").strip()
            if name.lower().startswith(".vn"):
                upper_font[id(portion)] = name.upper().endswith("H")
                return True
            return False

        changed = 0
        with docops._undo(doc, "Convert TCVN3 to Unicode"):
            targets = docops._writer_selection(doc)
            from_selection = bool(targets)
            if not targets:
                targets = [p for p in docops._portions(doc.getText()) if is_tcvn3(p)]
            for t in targets:
                old = t.getString()
                new, n = tcvn3_to_unicode(old, upper=upper_font.get(id(t), False))
                if new != old:
                    t.setString(new)
                    changed += 1
                if not from_selection or new != old:
                    t.CharFontName = TCVN3_REPLACEMENT_FONT
        self.message(self.t["done"].format(n=changed))

    def cmd_Nd30Document(self):
        # ONEX_TOOLS_ND30_FIELDS (JSON) bypasses the dialog for automated tests.
        raw = os.environ.get("ONEX_TOOLS_ND30_FIELDS")
        if raw:
            fields = json.loads(raw)
            if fields.get("date"):
                fields["date"] = datetime.date.fromisoformat(fields["date"])
        else:
            from vn1x import nd30_dialog
            parent = self.frame.getContainerWindow() if self.frame else None
            fields = nd30_dialog.run(self.ctx, parent, "vi" if self.t is TEXTS["vi"] else "en")
            if fields is None:
                return
        try:
            spec = nd30.build(fields)
        except nd30.Nd30Error as exc:
            self.message(self.t["nd30_error"].format(err=exc))
            return
        from vn1x import nd30_writer
        # Fill the current Writer document when it is still blank and unmodified (like picking a template in a new
        # document); otherwise open a new Writer window.
        current = self.frame.getController().getModel() if self.frame else None
        blank = (current is not None and current.supportsService("com.sun.star.text.TextDocument")
                 and not current.isModified() and not current.getText().getString()
                 and current.getTextTables().getCount() == 0)
        if blank:
            doc = current
        else:
            desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
            doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
        nd30_writer.fill(doc, spec)

    def message(self, text):
        if os.environ.get("ONEX_TOOLS_SILENT") == "1" or self.frame is None:
            return
        from com.sun.star.awt.MessageBoxType import INFOBOX
        toolkit = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        box = toolkit.createMessageBox(self.frame.getContainerWindow(), INFOBOX, 1, self.t["title"], text)
        box.execute()


SHEET_IMPL = "org.onexvn.tools.SheetFunctions"


def _optional_text(value, default):
    """Tham số tuỳ chọn của hàm Calc đến dưới dạng any: rỗng (None) khi bị bỏ qua."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    if isinstance(value, float):
        raise ValueError("cần chữ")
    return str(value).strip()


def _illegal(message):
    from com.sun.star.lang import IllegalArgumentException
    return IllegalArgumentException(message, None, 0)


try:
    from org.onexvn.tools import XVnSheetFunctions
except ImportError:  # type library not registered (e.g. imported outside the office)
    XVnSheetFunctions = None

if XVnSheetFunctions is not None:
    class SheetFunctions(unohelper.Base, XVnSheetFunctions, XServiceInfo):
        """=DOCSO(số; ["lẻ"|"linh"]) và =DOCTIEN(số tiền; [đơn vị, mặc định "đồng"]). Giá trị không đọc được
        (quá 18 chữ số…) báo lỗi trong ô thay vì trả về chữ sai."""

        def __init__(self, ctx, *args):
            self.ctx = ctx

        def docso(self, number, zero):
            try:
                le = _optional_text(zero, "lẻ")
                if le not in ("lẻ", "linh"):
                    raise ValueError(le)
                return number_to_words(repr(number), le=le, capitalize=True)
            except (NumberWordsError, ValueError) as exc:
                raise _illegal(str(exc))

        def doctien(self, amount, currency):
            try:
                return money_to_words(repr(amount), currency=_optional_text(currency, "đồng"))
            except (NumberWordsError, ValueError) as exc:
                raise _illegal(str(exc))

        def getImplementationName(self):
            return SHEET_IMPL

        def supportsService(self, name):
            return name in ("com.sun.star.sheet.AddIn",)

        def getSupportedServiceNames(self):
            return ("com.sun.star.sheet.AddIn",)


GUIDES_IMPL = "org.1xvnoffice.tools.GuideSeeder"


class GuideSeeder(unohelper.Base, XJob):
    """First run (job event onFirstRunInitialization): put the bundled quick start guides into Recent documents, like
    WPS does, then reload the Start Center so they show at once. Only when Recent is still empty, so a user's own
    history is never touched."""

    def __init__(self, ctx):
        self.ctx = ctx

    def _config(self, path, update=False):
        provider = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", self.ctx)
        arg = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        arg.Name, arg.Value = "nodepath", path
        kind = "ConfigurationUpdateAccess" if update else "ConfigurationAccess"
        return provider.createInstanceWithArguments("com.sun.star.configuration." + kind, (arg,))

    def execute(self, args):
        try:
            self.seed()
        except Exception:  # a failed convenience must never disturb start-up
            pass
        return None

    def seed(self):
        import base64
        from vn1x.guides import guide_files, thumbnail_png
        subst = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.util.PathSubstitution", self.ctx)
        root = uno.fileUrlToSystemPath(subst.substituteVariables("$(inst)", True)) + "/Resources/guides"
        locale = self._config("/org.openoffice.Office.Linguistic/General").UILocale
        files = guide_files(root, locale)
        if not files:
            return
        histories = self._config("/org.openoffice.Office.Histories/Histories", update=True)
        if not histories.hasByName("PickList"):
            return
        pick = histories.getByName("PickList")
        items, order = pick.getByName("ItemList"), pick.getByName("OrderList")
        if items.ElementNames:
            return
        for i, (path, filt) in enumerate(files):
            url = uno.systemPathToFileUrl(str(path))
            item = items.createInstance()
            png = thumbnail_png(path)
            thumb = base64.b64encode(png).decode("ascii") if png else ""
            item.Filter, item.Title, item.Thumbnail, item.ReadOnly, item.Pinned = filt, path.name, thumb, False, False
            items.insertByName(url, item)
            ref = order.createInstance()
            ref.HistoryItemRef = url
            order.insertByName(str(i), ref)
        histories.commitChanges()
        self.reload_start_center()

    def reload_start_center(self):
        desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
        frames = desktop.getFrames()
        for i in range(frames.getCount()):
            frame = frames.getByIndex(i)
            controller = frame.getController()
            if controller is None or controller.getModel() is not None:
                continue  # only the Start Center has a controller without a document
            window = frame.getContainerWindow()
            start = self.ctx.ServiceManager.createInstanceWithArgumentsAndContext(
                "com.sun.star.frame.StartModule", (window,), self.ctx)
            frame.setComponent(start, start)
            start.attachFrame(frame)
            window.setVisible(True)


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(Handler, IMPL, ("com.sun.star.frame.ProtocolHandler",))
g_ImplementationHelper.addImplementation(GuideSeeder, GUIDES_IMPL, ("com.sun.star.task.Job",))
if XVnSheetFunctions is not None:
    g_ImplementationHelper.addImplementation(SheetFunctions, SHEET_IMPL, ("com.sun.star.sheet.AddIn",))
