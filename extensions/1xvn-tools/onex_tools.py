# SPDX-License-Identifier: MPL-2.0
"""ProtocolHandler "vnd.1x.tools:" của 1xVnOffice: các lệnh tiếng Việt cho Writer và Calc,
và add-in hàm bảng tính DOCSO, DOCTIEN (interface org.onexvn.tools.XVnSheetFunctions, types/onexvn-tools.rdb).

Lệnh: NumberToWords, MoneyToWords, RemoveDiacritics, NormalizeUnicode, ConvertTCVN3.
Logic chữ nằm trong pythonpath/vn1x (có test riêng, không cần UNO); file này chỉ nối lệnh với tài liệu.
Biến môi trường ONEX_TOOLS_SILENT=1 tắt hộp thông báo (dùng cho kiểm thử tự động).
"""
import os
import sys

import uno
import unohelper
from com.sun.star.frame import XDispatch, XDispatchProvider
from com.sun.star.lang import XInitialization, XServiceInfo
from com.sun.star.document import XDocumentEventListener
from com.sun.star.task import XJob

import datetime
import json
from pathlib import Path

from vn1x import docops
from vn1x import nd30
from vn1x.numwords import NumberWordsError, money_to_words, number_to_words, parse_number_text
from vn1x.vnname import salutation, sort_key, split_name
from vn1x.vntext import (normalize_full, remove_diacritics, tcvn3_to_unicode, tone_style,
                         vni_to_unicode, viqr_to_unicode)

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
        "check_ok": "Decree 30 check: nothing measurable is wrong.",
        "check_found": "Decree 30 check: {n} point(s) to look at.\n\n{list}",
        "check_offer": "\n\nSet the page back to the rules now (paper size, margins, default font)?",
        "check_fixed": "Page set to A4 with Decree 30 margins and {font}. Ctrl+Z undoes it.",
        "check_writer_only": "Open the document in 1xDoc first: this command checks a text document.",
        "mcp_none": ("No MCP server is set up yet.\n\nWrite mcp_servers.json at:\n{path}\n\n"
                     "It takes the same shape as claude_desktop_config.json:\n{example}"),
        "mcp_ask": "{description}\n\nAllow this tool from now on?",
        "mcp_report": "MCP servers ({n}):\n\n{list}",
        "mcp_server_failed": "{id}: {error}",
        "rewrite_title": "Rewrite with AI",
        "rewrite_prompt": "How should it be rewritten? Leave empty for: clearer, keeping the meaning and the terms.",
        "rewrite_default": "clearer and easier to read, keeping the meaning, the terms and the tone",
        "rewrite_none": "Put the cursor in a paragraph, or select the text to rewrite.",
        "rewrite_preview": "{preview}\n\nApply this change? Ctrl+Z undoes it in one step.",
        "rewrite_stale": "The text changed while the AI was working, so nothing was applied. Run the command again.",
        "rewrite_nochange": "The AI returned the same text; nothing to apply.",
        "rewrite_done": "Applied. Ctrl+Z undoes it in one step.",
        "ai_question": "Ask about this document",
        "ai_prompt": "What do you want to know? The answer only reads the document; it changes nothing.",
        "ai_answer": "{text}\n\n— {provider}/{model}, sent {note}, {tokens} tokens.",
        "ai_no_config": ("No AI provider is set up yet.\n\nWrite your own providers.json at:\n{path}\n\n"
                         "Example (the key itself stays in the system keychain, never in this file):\n{example}"),
        "ai_bad_config": "providers.json has problems:\n\n{list}\n\nFile: {path}",
        "ai_failed": "{error}",
        "csv_title": "Open a CSV file safely",
        "csv_done": "Opened {name} as text: leading zeros, codes and dates are kept exactly as written, and cells starting with \"=\" are not run as formulas.",
        "csv_cancel": "",
        "xlsx_warning": ("Saved as {ext}. The sheet uses {n} 1xVnOffice formula(s) ({names}).\n\n"
                         "Excel shows the values they produced but cannot recalculate them: for an Excel user the "
                         "cells are frozen. Save as .ods to keep them live, or replace them with their values "
                         "before sending the file."),
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
        "check_ok": "Kiểm thể thức NĐ30: không thấy điểm nào sai trong những thứ đo được.",
        "check_found": "Kiểm thể thức NĐ30: có {n} điểm cần xem lại.\n\n{list}",
        "check_offer": "\n\nSửa phần trang ngay bây giờ (khổ giấy, lề, phông mặc định)?",
        "check_fixed": "Đã đặt trang A4, lề theo NĐ30 và phông {font}. Bấm Ctrl+Z để hoàn tác.",
        "check_writer_only": "Hãy mở văn bản trong 1xDoc trước: lệnh này kiểm tài liệu văn bản.",
        "mcp_none": ("Chưa khai báo máy chủ MCP nào.\n\nTạo tệp mcp_servers.json tại:\n{path}\n\n"
                     "Cấu trúc giống claude_desktop_config.json nên chép thẳng từ Claude Desktop sang được:\n{example}"),
        "mcp_ask": "{description}\n\nCho phép dùng công cụ này từ giờ?",
        "mcp_report": "Máy chủ MCP ({n}):\n\n{list}",
        "mcp_server_failed": "{id}: {error}",
        "rewrite_title": "Viết lại bằng AI",
        "rewrite_prompt": "Viết lại theo hướng nào? Để trống thì: rõ ràng hơn, giữ nguyên ý và thuật ngữ.",
        "rewrite_default": "rõ ràng và dễ đọc hơn, giữ nguyên ý, thuật ngữ và giọng văn",
        "rewrite_none": "Hãy đặt con trỏ vào một đoạn, hoặc chọn phần chữ cần viết lại.",
        "rewrite_preview": "{preview}\n\nÁp dụng thay đổi này? Bấm Ctrl+Z một lần là hoàn tác.",
        "rewrite_stale": "Chữ đã bị sửa trong lúc AI đang chạy nên chưa áp gì cả. Hãy chạy lại lệnh.",
        "rewrite_nochange": "AI trả về đúng chữ cũ, không có gì để áp.",
        "rewrite_done": "Đã áp dụng. Bấm Ctrl+Z một lần là hoàn tác.",
        "ai_question": "Hỏi về tài liệu này",
        "ai_prompt": "Bạn muốn biết điều gì? Câu trả lời chỉ đọc tài liệu, không sửa gì cả.",
        "ai_answer": "{text}\n\n— {provider}/{model}, đã gửi {note}, {tokens} token.",
        "ai_no_config": ("Chưa khai báo nhà cung cấp AI nào.\n\nTạo tệp providers.json của bạn tại:\n{path}\n\n"
                         "Ví dụ (khoá API nằm trong kho bí mật của hệ điều hành, không bao giờ ghi vào tệp này):\n{example}"),
        "ai_bad_config": "providers.json đang có lỗi:\n\n{list}\n\nTệp: {path}",
        "ai_failed": "{error}",
        "csv_title": "Mở tệp CSV an toàn",
        "csv_done": "Đã mở {name} dưới dạng chữ: số 0 đầu, mã số và ngày tháng giữ nguyên như trong tệp, ô bắt đầu bằng \"=\" không bị chạy như công thức.",
        "csv_cancel": "",
        "xlsx_warning": ("Đã lưu dạng {ext}. Bảng tính đang dùng {n} công thức của 1xVnOffice ({names}).\n\n"
                         "Excel hiện được giá trị đã tính nhưng không tính lại được: với người dùng Excel, các ô đó "
                         "đứng yên. Muốn giữ công thức sống thì lưu dạng .ods, hoặc thay công thức bằng giá trị "
                         "trước khi gửi tệp."),
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
        if url.Path == "OpenCsvSafely":
            self.t = TEXTS[_ui_lang(self.ctx)]
            self.cmd_OpenCsvSafely()
            return
        if url.Path == "Nd30Check":
            self.t = TEXTS[_ui_lang(self.ctx)]
            self.cmd_Nd30Check()
            return
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
        """Dựng sẵn NFC, gộp khoảng trắng và sửa khoảng trắng quanh dấu câu. Kiểu đặt dấu thanh không đổi ở đây."""
        self._text(doc, is_writer, normalize_full, "Normalize Vietnamese")

    def cmd_ToneStyleOld(self, doc, is_writer):
        """Đặt dấu thanh kiểu cũ: hòa, thủy, hòe."""
        self._text(doc, is_writer, lambda t: tone_style(t, modern=False), "Tone style: hòa")

    def cmd_ToneStyleNew(self, doc, is_writer):
        """Đặt dấu thanh kiểu mới: hoà, thuỷ, hoè."""
        self._text(doc, is_writer, lambda t: tone_style(t, modern=True), "Tone style: hoà")

    def cmd_ConvertVNI(self, doc, is_writer):
        """Chữ gõ kiểu VNI ("Vie65t") thành Unicode. Chỉ đổi chỗ có dấu đứng ngay sau nguyên âm."""
        self._text(doc, is_writer, lambda t: vni_to_unicode(t)[0], "Convert VNI typing")

    def cmd_ConvertVIQR(self, doc, is_writer):
        """Chữ gõ kiểu VIQR ("Vie^.t") thành Unicode."""
        self._text(doc, is_writer, lambda t: viqr_to_unicode(t)[0], "Convert VIQR typing")

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

    def cmd_McpTools(self, doc, is_writer):
        """Liệt kê máy chủ MCP đã khai và công cụ của chúng, kèm trạng thái quyền. Chỉ đọc, không chạy công cụ nào."""
        from vn1x import mcpperm
        servers = self._mcp_servers()
        if servers is None:
            return
        store = mcpperm.load(self._profile_file(mcpperm.FILENAME))
        lines = []
        for server in servers:
            tools, error = self._mcp_list(server)
            if error:
                lines.append(self.t["mcp_server_failed"].format(id=server["id"], error=error))
                continue
            lines.append(f"• {server['id']} ({len(tools)} công cụ)")
            for tool in tools:
                state = {mcpperm.ALLOW: "đã cho phép", mcpperm.DENY: "đã từ chối"}.get(
                    mcpperm.decide(store, server["id"], tool), "sẽ hỏi khi dùng")
                lines.append(f"    - {tool['name']} [{state}]: {tool.get('description') or '(không có mô tả)'}")
        self.message(self.t["mcp_report"].format(n=len(servers), list="\n".join(lines)))

    def _profile_file(self, name):
        """Đường dẫn một tệp cấu hình trong hồ sơ người dùng (bước kiểm tự động trỏ chỗ khác)."""
        override = os.environ.get("ONEX_" + name.replace(".json", "").upper() + "_PATH")
        if override:
            return override
        subst = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.util.PathSubstitution", self.ctx)
        return str(Path(uno.fileUrlToSystemPath(subst.substituteVariables("$(userurl)", True))) / name)

    def _mcp_servers(self):
        """Danh sách máy chủ MCP đã khai, hoặc None (đã báo cho người dùng)."""
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent / "agenthost"))
        import mcpclient
        path = self._profile_file("mcp_servers.json")
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else {}
        except ValueError as exc:
            self.message(self.t["ai_bad_config"].format(list=str(exc), path=path))
            return None
        servers = mcpclient.from_claude_desktop(raw)
        if not servers:
            self.message(self.t["mcp_none"].format(path=path, example=MCP_EXAMPLE))
            return None
        return servers

    def _mcp_list(self, server):
        """(danh sách công cụ, lỗi). Mở máy chủ, hỏi công cụ, rồi tắt ngay."""
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent / "agenthost"))
        import mcpclient
        try:
            with mcpclient.StdioServer(server["command"], server.get("args") or [],
                                       env=server.get("env") or {}, cwd=server.get("cwd")) as mcp:
                return mcp.list_tools(), None
        except mcpclient.McpError as exc:
            return [], str(exc)

    def _allowed_mcp_tools(self):
        """Công cụ MCP người dùng đã cho phép, kèm cách chạy máy chủ, để đưa cho Agent Host."""
        from vn1x import mcpperm
        servers = self._mcp_servers_quiet()
        if not servers:
            return []
        path = self._profile_file(mcpperm.FILENAME)
        store = mcpperm.load(path)
        out = []
        for server in servers:
            tools, error = self._mcp_list(server)
            if error:
                continue
            for tool in tools:
                state = mcpperm.decide(store, server["id"], tool)
                if state == mcpperm.ASK:
                    answer = self.ask(self.t["mcp_ask"].format(description=mcpperm.describe(server["id"], tool)))
                    state = mcpperm.ALLOW if answer else mcpperm.DENY
                    store = mcpperm.remember(store, server["id"], tool, state)
                    mcpperm.save(path, store)
                if state == mcpperm.ALLOW:
                    out.append(dict(tool, server={"command": server["command"], "args": server.get("args") or [],
                                                  "env": server.get("env") or {}, "cwd": server.get("cwd")}))
        return out

    def _mcp_servers_quiet(self):
        """Như _mcp_servers nhưng im lặng khi chưa khai báo gì: dùng trong lệnh hỏi AI."""
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent / "agenthost"))
        import mcpclient
        path = self._profile_file("mcp_servers.json")
        if not Path(path).is_file():
            return []
        try:
            return mcpclient.from_claude_desktop(json.loads(Path(path).read_text(encoding="utf-8")))
        except ValueError:
            return []

    def cmd_AiRewrite(self, doc, is_writer):
        """AI viết lại đoạn đang chọn. Không sửa thẳng: dựng ChangeSet, cho xem trước, rồi áp trong một bước hoàn tác."""
        from vn1x import aicontext, changeset
        if not is_writer:
            self.message(self.t["unsupported"])
            return
        config = self._ai_ready()
        if config is None:
            return
        target = self._writer_target(doc)
        if target is None:
            self.message(self.t["rewrite_none"])
            return
        anchor, original = target
        how = os.environ.get("ONEX_AI_REWRITE_HOW")
        if how is None:
            how = self._ask_text(self.t["rewrite_title"], self.t["rewrite_prompt"])
            if how is None:
                return
        how = how.strip() or self.t["rewrite_default"]
        messages = [
            {"role": "system", "content": "Bạn viết lại văn bản tiếng Việt. Chỉ trả về phần chữ đã viết lại, "
                                          "không thêm lời dẫn, không thêm dấu nháy, không giải thích."},
            {"role": "user", "content": f"Viết lại đoạn sau cho {how}:\n\n{original}"},
        ]
        result = self._call_model(config, messages)
        if result is None:
            return
        changes = changeset.build([(anchor, original, result.strip())])
        if not changes:
            self.message(self.t["rewrite_nochange"])
            return
        if not self._confirm_changes(changes):
            return
        if changeset.stale(changes, {anchor: self._anchor_text(doc, anchor)}):
            self.message(self.t["rewrite_stale"])
            return
        self._apply_changes(doc, changes, f"AI: viết lại ({aicontext.trim(how, 40)[0]})")
        self.message(self.t["rewrite_done"])

    def _confirm_changes(self, changes):
        """Hộp xem trước. Khi chạy tự động thì ONEX_AI_AUTO_APPLY=1 đóng vai người dùng bấm Áp dụng."""
        from vn1x import changeset
        text = self.t["rewrite_preview"].format(preview=changeset.preview(changes))
        if os.environ.get("ONEX_TOOLS_SILENT") == "1" or self.frame is None:
            self.message(text)
            return os.environ.get("ONEX_AI_AUTO_APPLY") == "1"
        return self.ask(text)

    def _writer_target(self, doc):
        """(mốc, chữ gốc) của chỗ sẽ sửa: vùng đang chọn, nếu không thì đoạn chứa con trỏ.

        Mốc là chỉ số đoạn trong thân tài liệu, kèm chữ gốc để phát hiện người dùng đã sửa chỗ đó."""
        try:
            selection = doc.getCurrentSelection()
            if selection is not None and selection.getCount():
                piece = selection.getByIndex(0)
                if piece.getString().strip():
                    index = self._paragraph_index(doc, piece.getStart())
                    if index is not None:
                        return f"para:{index}", self._paragraph_at(doc, index).getString()
        except Exception:  # noqa: BLE001 - không có vùng chọn thì rơi xuống đoạn chứa con trỏ
            pass
        try:
            cursor = doc.getCurrentController().getViewCursor()
            index = self._paragraph_index(doc, cursor.getStart())
        except Exception:  # noqa: BLE001
            index = None
        if index is None:
            return None
        paragraph = self._paragraph_at(doc, index)
        return (f"para:{index}", paragraph.getString()) if paragraph.getString().strip() else None

    def _paragraphs(self, doc):
        out = []
        it = doc.getText().createEnumeration()
        while it.hasMoreElements():
            element = it.nextElement()
            if element.supportsService("com.sun.star.text.Paragraph"):
                out.append(element)
        return out

    def _paragraph_at(self, doc, index):
        return self._paragraphs(doc)[index]

    def _paragraph_index(self, doc, position):
        """Chỉ số đoạn chứa `position` (một text range)."""
        text = doc.getText()
        for index, paragraph in enumerate(self._paragraphs(doc)):
            cursor = text.createTextCursorByRange(paragraph)
            if text.compareRegionStarts(cursor, position) >= 0 and text.compareRegionEnds(cursor, position) <= 0:
                return index
        return None

    def _anchor_text(self, doc, anchor):
        try:
            return self._paragraph_at(doc, int(anchor.split(":")[1])).getString()
        except (IndexError, ValueError):
            return ""

    def _apply_changes(self, doc, changes, title):
        """Áp mọi thay đổi trong MỘT bước hoàn tác: Ctrl+Z một lần trả lại như cũ."""
        doc.UndoManager.enterUndoContext(title)
        try:
            for change in changes:
                self._paragraph_at(doc, int(change.anchor.split(":")[1])).setString(change.new)
        finally:
            doc.UndoManager.leaveUndoContext()

    def _ai_ready(self):
        """Cấu hình AI dùng được, hoặc None (đã báo lỗi cho người dùng)."""
        from vn1x import aiconfig
        path = self._ai_config_path()
        try:
            config = aiconfig.load(path)
        except aiconfig.ConfigError as exc:
            self.message(self.t["ai_bad_config"].format(list=str(exc), path=path))
            return None
        if not config.get("providers"):
            self.message(self.t["ai_no_config"].format(path=path, example=AI_EXAMPLE))
            return None
        found = aiconfig.problems(config)
        if found:
            self.message(self.t["ai_bad_config"].format(list="\n".join(f"- {p}" for p in found), path=path))
            return None
        return config

    def _call_model(self, config, messages, role="soan_thao"):
        """Chữ mô hình trả về, hoặc None (đã báo lỗi)."""
        from vn1x import aiconfig
        try:
            provider, model = aiconfig.resolve(config, role)
        except aiconfig.ConfigError as exc:
            self.message(self.t["ai_bad_config"].format(list=str(exc), path=self._ai_config_path()))
            return None
        limit = (config.get("limits") or {}).get("max_output_tokens", 2000)
        result = self._agent_host({"action": "ask", "provider": provider, "model": model,
                                   "messages": messages, "max_tokens": limit})
        if not result.get("ok"):
            self.message(self.t["ai_failed"].format(error=result.get("error", "?")))
            return None
        return result.get("text", "")

    def cmd_AiAsk(self, doc, is_writer):
        """Hỏi mô hình AI về tài liệu đang mở. Chỉ đọc: không sửa gì trong tài liệu."""
        from vn1x import aiconfig, aicontext
        path = self._ai_config_path()
        config = self._ai_ready()
        if config is None:
            return
        question = os.environ.get("ONEX_AI_QUESTION") or self._ask_text(self.t["ai_question"],
                                                                        self.t["ai_prompt"])
        if not question:
            return
        selection, whole = self._document_text(doc, is_writer)
        try:
            provider, model = aiconfig.resolve(config)
            messages, note = aicontext.build(question, selection, whole)
        except (aiconfig.ConfigError, ValueError) as exc:
            self.message(self.t["ai_bad_config"].format(list=str(exc), path=path))
            return
        limit = (config.get("limits") or {}).get("max_output_tokens", 2000)
        result = self._agent_host({"action": "ask", "provider": provider, "model": model,
                                   "messages": messages, "max_tokens": limit,
                                   "tools": self._allowed_mcp_tools()})
        if not result.get("ok"):
            self.message(self.t["ai_failed"].format(error=result.get("error", "?")))
            return
        usage = result.get("usage") or {}
        self.message(self.t["ai_answer"].format(text=result["text"], provider=provider.get("id", "?"), model=model,
                                                note=note, tokens=usage.get("input", 0) + usage.get("output", 0)))

    def _ai_config_path(self):
        """providers.json trong hồ sơ người dùng (bước kiểm tự động trỏ chỗ khác qua ONEX_AI_CONFIG_PATH)."""
        from vn1x import aiconfig
        override = os.environ.get("ONEX_AI_CONFIG_PATH")
        if override:
            return override
        subst = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.util.PathSubstitution", self.ctx)
        profile = uno.fileUrlToSystemPath(subst.substituteVariables("$(userurl)", True))
        return str(Path(profile) / aiconfig.FILENAME)

    def _document_text(self, doc, is_writer):
        """(chữ đang chọn, chữ cả tài liệu). Bảng tính lấy theo vùng ô đang dùng."""
        selection = ""
        try:
            current = doc.getCurrentSelection()
            if current is not None and hasattr(current, "getString"):
                selection = current.getString()
            elif current is not None and current.getCount() and hasattr(current.getByIndex(0), "getString"):
                selection = current.getByIndex(0).getString()
        except Exception:  # noqa: BLE001 - không có vùng chọn thì dùng cả tài liệu
            selection = ""
        if is_writer:
            return selection, doc.getText().getString()
        rows = []
        sheets = doc.getSheets()
        for index in range(sheets.getCount()):
            sheet = sheets.getByIndex(index)
            cursor = sheet.createCursor()
            cursor.gotoEndOfUsedArea(False)
            area = cursor.getRangeAddress()
            rows.append(f"# {sheet.getName()}")
            for row in range(area.EndRow + 1):
                cells = [sheet.getCellByPosition(col, row).getString() for col in range(area.EndColumn + 1)]
                if any(cells):
                    rows.append("\t".join(cells))
        return selection, "\n".join(rows)

    def _agent_host(self, request):
        """Gọi tiến trình Agent Host. Mọi kết nối mạng đi qua đây, không đi thẳng từ trong tài liệu."""
        import subprocess
        host = Path(__file__).resolve().parent / "agenthost" / "host.py"
        if not host.is_file():
            return {"ok": False, "error": f"không thấy Agent Host tại {host}"}
        try:
            done = subprocess.run([self._python_executable(), "-I", str(host)],
                                  input=json.dumps(request), capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "error": f"không chạy được Agent Host: {exc}"}
        try:
            return json.loads(done.stdout or "{}")
        except ValueError:
            return {"ok": False, "error": (done.stderr or done.stdout or "Agent Host không trả lời")[:400]}

    def _python_executable(self):
        candidates = [sys.executable]
        subst = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.util.PathSubstitution", self.ctx)
        inst = uno.fileUrlToSystemPath(subst.substituteVariables("$(inst)", True))
        candidates += [str(Path(inst) / "Resources" / "python"), str(Path(inst) / "program" / "python"), "python3"]
        for candidate in candidates:
            if candidate and Path(candidate).is_file() and "soffice" not in Path(candidate).name:
                return candidate
        return "python3"

    def _ask_text(self, title, prompt):
        """Hộp nhập một dòng. Trả về chuỗi rỗng khi người dùng huỷ."""
        if os.environ.get("ONEX_TOOLS_SILENT") == "1" or self.frame is None:
            return ""
        smgr = self.ctx.ServiceManager
        model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", self.ctx)
        model.Width, model.Height, model.Title = 260, 90, title
        label = model.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
        label.PositionX, label.PositionY, label.Width, label.Height, label.MultiLine = 8, 8, 244, 24
        label.Label = prompt
        model.insertByName("lbl", label)
        edit = model.createInstance("com.sun.star.awt.UnoControlEditModel")
        edit.PositionX, edit.PositionY, edit.Width, edit.Height = 8, 36, 244, 16
        model.insertByName("q", edit)
        for name, text, kind, pos in (("ok", "OK", 1, 0), ("cancel", "Huỷ", 2, 1)):
            button = model.createInstance("com.sun.star.awt.UnoControlButtonModel")
            button.PositionX, button.PositionY = model.Width - (pos + 1) * 60, 60
            button.Width, button.Height = 52, 14
            button.Label, button.PushButtonType, button.DefaultButton = text, kind, kind == 1
            model.insertByName(name, button)
        dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", self.ctx)
        dialog.setModel(model)
        dialog.createPeer(smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx),
                          self.frame.getContainerWindow())
        try:
            return dialog.getControl("q").getText().strip() if dialog.execute() == 1 else None
        finally:
            dialog.dispose()

    def cmd_OpenCsvSafely(self):
        """Mở tệp CSV với mọi cột là chữ, bộ ký tự UTF-8 và không chạy công thức."""
        from vn1x import csvsafe
        path = os.environ.get("ONEX_TOOLS_CSV_PATH") or self._pick_file()
        if not path:
            return
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            first_line = handle.readline()
        options = csvsafe.filter_options(separator=csvsafe.guess_separator(first_line))
        desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
        args = []
        for name, value in (("FilterName", "Text - txt - csv (StarCalc)"), ("FilterOptions", options)):
            item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
            item.Name, item.Value = name, value
            args.append(item)
        desktop.loadComponentFromURL(uno.systemPathToFileUrl(path), "_blank", 0, tuple(args))
        self.message(self.t["csv_done"].format(name=os.path.basename(path)))

    def _pick_file(self):
        """Hộp chọn tệp CSV. Trả về đường dẫn hệ thống, hoặc chuỗi rỗng khi người dùng huỷ."""
        picker = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.ui.dialogs.FilePicker", self.ctx)
        picker.setTitle(self.t["csv_title"])
        picker.appendFilter("CSV (*.csv, *.txt)", "*.csv;*.txt")
        picker.appendFilter("*", "*")
        try:
            if picker.execute() != 1:
                return ""
            files = picker.getSelectedFiles()
            return uno.fileUrlToSystemPath(files[0]) if files else ""
        finally:
            picker.dispose() if hasattr(picker, "dispose") else None

    def cmd_Nd30Check(self):
        """Kiểm thể thức văn bản đang mở theo NĐ30 và mời sửa phần trang."""
        from vn1x import nd30_check, nd30_check_writer
        doc = self.frame.getController().getModel() if self.frame else None
        if doc is None or not doc.supportsService("com.sun.star.text.TextDocument"):
            self.message(self.t["check_writer_only"])
            return
        issues = nd30_check.check(nd30_check_writer.describe(doc))
        out = os.environ.get("ONEX_TOOLS_CHECK_OUT")   # bước kiểm tự động đọc kết quả ở đây
        if out:
            with open(out, "w", encoding="utf-8") as f:
                json.dump([{"key": i.key, "message": i.message, "fix": i.fix} for i in issues], f, ensure_ascii=False)
        if not issues:
            self.message(self.t["check_ok"])
            return
        report = "\n".join(f"{n}. {i.message}" for n, i in enumerate(issues, 1))
        text = self.t["check_found"].format(n=len(issues), list=report)
        if not any(i.fix for i in issues):
            self.message(text)
            return
        if self.ask(text + self.t["check_offer"]):
            fix = nd30_check.page_fix()
            nd30_check_writer.apply_page_fix(doc, fix)
            self.message(self.t["check_fixed"].format(font=fix["font"]))

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

    def ask(self, text):
        """Hỏi Có/Không. Khi chạy tự động (ONEX_TOOLS_SILENT) thì coi như Có, để bước kiểm chạy được phần sửa."""
        if os.environ.get("ONEX_TOOLS_SILENT") == "1" or self.frame is None:
            return os.environ.get("ONEX_TOOLS_CHECK_FIX") == "1"
        from com.sun.star.awt.MessageBoxType import QUERYBOX
        toolkit = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        box = toolkit.createMessageBox(self.frame.getContainerWindow(), QUERYBOX, 3, self.t["title"], text)
        answer = box.execute()
        box.dispose()
        return answer == 2   # com.sun.star.awt.MessageBoxResults.YES

    def message(self, text):
        if os.environ.get("ONEX_TOOLS_SILENT") == "1" or self.frame is None:
            out = os.environ.get("ONEX_TOOLS_WARN_OUT")   # bước kiểm tự động đọc thông báo ở đây
            if out:
                with open(out, "a", encoding="utf-8") as handle:
                    handle.write(text + "\n")
            return
        from com.sun.star.awt.MessageBoxType import INFOBOX
        toolkit = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        box = toolkit.createMessageBox(self.frame.getContainerWindow(), INFOBOX, 1, self.t["title"], text)
        box.execute()


MCP_EXAMPLE = json.dumps({
    "mcpServers": {
        "giay-to": {"command": "python3", "args": ["/duong/dan/toi/may_chu_mcp.py"], "env": {}},
    },
}, ensure_ascii=False, indent=2)

AI_EXAMPLE = json.dumps({
    "providers": [
        {"id": "claude", "type": "anthropic", "secret_ref": "1xvnoffice/anthropic",
         "models": ["claude-sonnet-5-5"]},
        {"id": "local", "type": "ollama", "base_url": "http://127.0.0.1:11434/v1", "models": ["qwen3:8b"]},
    ],
    "roles": {"soan_thao": "claude/claude-sonnet-5-5"},
}, ensure_ascii=False, indent=2)

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
        """Hàm bảng tính của 1xVnOffice: =DOCSO(số; ["lẻ"|"linh"]), =DOCTIEN(số tiền; [đơn vị, mặc định "đồng"]),
        =TACHHO / =TACHDEM / =TACHTEN(họ tên) và =SAPTEN(họ tên) cho khoá sắp xếp. Giá trị không đọc được
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

        def tachho(self, full_name):
            return split_name(full_name)[0]

        def tachdem(self, full_name):
            return split_name(full_name)[1]

        def tachten(self, full_name):
            return split_name(full_name)[2]

        def sapten(self, full_name):
            return sort_key(full_name)

        def bodau(self, text):
            return remove_diacritics(text)

        def xungho(self, gender, full_name):
            return salutation(gender, _optional_text(full_name, ""))

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


WARNER_IMPL = "org.1xvnoffice.tools.XlsxWarner"
ADDIN_MARK = "ORG.ONEXVN.TOOLS."          # công thức của add-in hiện ra dưới tên đầy đủ này
RISKY_EXT = (".xlsx", ".xls", ".xlsm", ".csv")


def _addin_formulas(doc):
    """Tên các hàm của 1xVnOffice đang dùng trong bảng tính, không trùng lặp."""
    from com.sun.star.sheet.CellFlags import FORMULA
    found = set()
    sheets = doc.getSheets()
    for i in range(sheets.getCount()):
        cells = sheets.getByIndex(i).queryContentCells(FORMULA)
        for rng in cells.getRangeAddresses():
            sheet = sheets.getByIndex(rng.Sheet)
            for row in range(rng.StartRow, rng.EndRow + 1):
                for col in range(rng.StartColumn, rng.EndColumn + 1):
                    formula = sheet.getCellByPosition(col, row).getFormula()
                    at = formula.upper().find(ADDIN_MARK)
                    while at >= 0:
                        rest = formula[at + len(ADDIN_MARK):]
                        name = rest.split("(")[0].split(".")[-1]
                        if name:
                            found.add(name.upper())
                        at = formula.upper().find(ADDIN_MARK, at + 1)
    return sorted(found)


class SaveWatcher(unohelper.Base, XDocumentEventListener):
    """Sau khi lưu bảng tính sang định dạng Excel, nhắc rằng hàm riêng của 1xVnOffice không tính lại được ở Excel.
    Mỗi tài liệu chỉ nhắc một lần trong phiên."""

    def __init__(self, ctx, texts):
        self.ctx, self.t, self.warned = ctx, texts, False

    def documentEventOccured(self, event):
        try:
            if self.warned or event.EventName not in ("OnSaveAsDone", "OnSaveDone"):
                return
            doc = event.Source
            url = (doc.getURL() or "").lower()
            ext = next((e for e in RISKY_EXT if url.endswith(e)), None)
            if not ext:
                return
            names = _addin_formulas(doc)
            if not names:
                return
            self.warned = True
            _message_box(self.ctx, doc, self.t["title"],
                         self.t["xlsx_warning"].format(ext=ext, n=len(names), names=", ".join(names)))
        except Exception:  # noqa: BLE001 - một lời nhắc hỏng không được cản việc lưu
            pass

    def disposing(self, event):
        pass


class XlsxWarner(unohelper.Base, XJob):
    """Gắn SaveWatcher vào mỗi bảng tính vừa mở (sự kiện onDocumentOpened trong Jobs.xcu)."""

    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, args):
        try:
            values = {}
            for item in args:
                if item.Name == "Environment":
                    values = {v.Name: v.Value for v in item.Value}
            doc = values.get("Model")
            if doc is not None and doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                doc.addDocumentEventListener(SaveWatcher(self.ctx, TEXTS[_ui_lang(self.ctx)]))
        except Exception:  # noqa: BLE001 - không được cản việc mở tài liệu
            pass
        return None


def _message_box(ctx, doc, title, text):
    """Hộp thông báo gắn vào cửa sổ của tài liệu."""
    if os.environ.get("ONEX_TOOLS_SILENT") == "1":
        out = os.environ.get("ONEX_TOOLS_WARN_OUT")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write(text.replace("\n", " ") + "\n")
        return
    from com.sun.star.awt.MessageBoxType import INFOBOX
    window = doc.getCurrentController().getFrame().getContainerWindow()
    toolkit = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    box = toolkit.createMessageBox(window, INFOBOX, 1, title, text)
    box.execute()
    box.dispose()


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(Handler, IMPL, ("com.sun.star.frame.ProtocolHandler",))
g_ImplementationHelper.addImplementation(GuideSeeder, GUIDES_IMPL, ("com.sun.star.task.Job",))
g_ImplementationHelper.addImplementation(XlsxWarner, WARNER_IMPL, ("com.sun.star.task.Job",))
if XVnSheetFunctions is not None:
    g_ImplementationHelper.addImplementation(SheetFunctions, SHEET_IMPL, ("com.sun.star.sheet.AddIn",))
