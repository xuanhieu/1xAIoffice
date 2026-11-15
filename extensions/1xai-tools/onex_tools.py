# SPDX-License-Identifier: MPL-2.0
"""ProtocolHandler "vnd.1x.tools:" của 1xAIoffice: các lệnh tiếng Việt cho Writer và Calc,
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
from com.sun.star.bridge import XInstanceProvider

import datetime
import json
from pathlib import Path

from vn1x import docops
from vn1x import nd30
from vn1x.numwords import NumberWordsError, money_to_words, number_to_words, parse_number_text
from vn1x.vnname import salutation, sort_key, split_name
from vn1x.vntext import (normalize_full, remove_diacritics, tcvn3_to_unicode, tone_style,
                         vni_to_unicode, viqr_to_unicode)

FIELD_LABELS = {
    "client_id": "client_id của ứng dụng OAuth",
    "tenant": "mã tenant (thư mục Entra ID của cơ quan)",
    "base_url": "địa chỉ máy chủ",
    "authorize_url": "địa chỉ đăng nhập (authorize)",
    "token_url": "địa chỉ cấp thẻ (token)",
}

IMPL = "org.1xaioffice.tools.ProtocolHandler"
PROTOCOL = "vnd.1x.tools:"
BOLD_WEIGHT = 150.0      # com.sun.star.awt.FontWeight.BOLD
TCVN3_REPLACEMENT_FONT = "Times New Roman"

TEXTS = {
    "en": {
        "title": "1xAIoffice",
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
        "mcp_login_ask": "“{id}” is a remote MCP server and asks you to sign in.\n\nSign in now? A browser window opens; nothing is sent until you agree there.",
        "mcp_login_ok": "Signed in to “{id}”: {state}.",
        "mcp_login_failed": "Could not sign in to “{id}”: {error}",
        "mcpsrv_off": ("The MCP server is off, so no assistant can read or change your documents.\n\n"
                       "Turn it on? You will still approve each assistant, and each change."),
        "mcpsrv_on": ("The MCP server is on ({pipe}).\n\nConfiguration for Claude Desktop / Cursor "
                      "(claude_desktop_config.json):\n{config}\n\n{clients}"),
        "mcpsrv_started": "The MCP server is on. Assistant configuration:\n{config}",
        "mcpsrv_stop": "Turn the MCP server off?",
        "mcpsrv_stopped": "The MCP server is off.",
        "mcpsrv_pair": "“{name}” asked to read and change your documents through MCP.\n\nAllow it from now on?",
        "mcpsrv_clients": "Assistants allowed: {allowed}",
        "skill_title": "Skills",
        "skill_prompt": "Which skill? ({names})",
        "skill_none": "No skill is installed for this kind of document.",
        "skill_unknown": "There is no skill called “{name}”. Installed: {names}",
        "skill_broken": "Skipped {n} broken skill(s): {list}",
        "skill_answer": "{answer}\n\n— skill “{name}” {version}",
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
        "ai_no_account": ("No AI account is connected yet.\n\nConnect one now? You can use the ChatGPT plan you already "
                          "pay for, an API key, or an AI server on this computer."),
        "acct_open_key_page": "{label} needs an API key.\n\nOpen the page where you create one ({url}) in your browser now? Sign in there, create a key, copy it, then come back here to paste it.",
        "acct_open_failed": "Could not open the browser. Open this address yourself: {url}",
        "cancel": "Cancel",
        "panel_no_ai": "No AI account yet. Open AI Accounts below; free providers come first.",
        "panel_ai": "AI in use: {name}",
        "acct_title": "AI accounts",
        "acct_overview": "AI accounts\n\nSet up now:\n{current}\n\nYou can add:\n{catalogue}",
        "acct_pick": "Type the number or the name of the provider to add (empty to close):",
        "acct_unknown": "There is no provider called “{name}”.",
        "acct_field": "{label}\n\n{field}:",
        "acct_key": "{label}\n\nPaste the API key. It goes straight into this computer's secret store ({ref}); it is never written into providers.json and never shown again.",
        "acct_client_secret": "{label}\n\nPaste the client secret of your OAuth app. Google issues one even for Desktop apps. It goes into this computer's secret store, never into providers.json.",
        "acct_key_failed": "Could not write the key into the secret store.",
        "acct_oauth_how": "{label}\n\nSign in with the browser on this computer?\n\nChoose No to sign in with a short code on another device.",
        "acct_device": "Open:\n{url}\n\nand type this code:\n\n{code}\n\nThen come back and press OK.",
        "acct_login_ok": "Signed in: {state}.",
        "acct_login_failed": "Sign-in failed: {error}",
        "acct_model_ask": "Which model? Known: {models}",
        "acct_model_free": "Type the model name (for Azure OpenAI this is the deployment name):",
        "acct_saved": "Saved the account “{id}” ({model}).\n\n{file}",
        "acct_nothing": "Nothing was saved.",
        "ai_bad_config": "providers.json has problems:\n\n{list}\n\nFile: {path}",
        "ai_failed": "{error}",
        "csv_title": "Open a CSV file safely",
        "csv_done": "Opened {name} as text: leading zeros, codes and dates are kept exactly as written, and cells starting with \"=\" are not run as formulas.",
        "csv_cancel": "",
        "xlsx_warning": ("Saved as {ext}. The sheet uses {n} 1xAIoffice formula(s) ({names}).\n\n"
                         "Excel shows the values they produced but cannot recalculate them: for an Excel user the "
                         "cells are frozen. Save as .ods to keep them live, or replace them with their values "
                         "before sending the file."),
    },
    "vi": {
        "title": "1xAIoffice",
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
        "mcp_login_ask": "“{id}” là máy chủ MCP ở xa và đang đòi đăng nhập.\n\nĐăng nhập bây giờ? Trình duyệt sẽ mở ra; chưa gửi gì đi cho tới khi bạn đồng ý ở đó.",
        "mcp_login_ok": "Đã đăng nhập “{id}”: {state}.",
        "mcp_login_failed": "Không đăng nhập được “{id}”: {error}",
        "mcpsrv_off": ("Máy chủ MCP đang TẮT, nên chưa trợ lý nào đọc hay sửa được tài liệu của bạn.\n\n"
                       "Bật lên? Bật rồi thì mỗi trợ lý vẫn phải được bạn cho phép, và mỗi lần sửa tài liệu "
                       "vẫn hỏi bạn."),
        "mcpsrv_on": ("Máy chủ MCP đang BẬT ({pipe}).\n\nCấu hình để dán vào Claude Desktop / Cursor "
                      "(claude_desktop_config.json):\n{config}\n\n{clients}"),
        "mcpsrv_started": "Đã bật máy chủ MCP. Cấu hình cho trợ lý:\n{config}",
        "mcpsrv_stop": "Tắt máy chủ MCP?",
        "mcpsrv_stopped": "Đã tắt máy chủ MCP.",
        "mcpsrv_pair": "“{name}” xin được đọc và sửa tài liệu của bạn qua MCP.\n\nCho phép từ giờ?",
        "mcpsrv_clients": "Trợ lý đã được phép: {allowed}",
        "skill_title": "Skill",
        "skill_prompt": "Dùng skill nào? ({names})",
        "skill_none": "Chưa có skill nào dùng được cho loại tài liệu này.",
        "skill_unknown": "Không có skill tên “{name}”. Đang có: {names}",
        "skill_broken": "Bỏ qua {n} skill hỏng: {list}",
        "skill_answer": "{answer}\n\n— skill “{name}” {version}",
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
        "ai_no_account": ("Chưa gắn tài khoản AI nào.\n\nGắn ngay bây giờ? Bạn có thể dùng gói ChatGPT đang trả, "
                          "một khoá API, hoặc máy chủ AI chạy trong máy."),
        "acct_open_key_page": "{label} cần một khoá API.\n\nMở trang tạo khoá ({url}) trong trình duyệt ngay bây giờ? Bạn đăng nhập ở đó, tạo khoá, chép lại, rồi quay về đây dán vào.",
        "acct_open_failed": "Không mở được trình duyệt. Bạn tự mở địa chỉ này: {url}",
        "cancel": "Huỷ",
        "panel_no_ai": "Chưa gắn tài khoản AI. Bấm Tài khoản AI bên dưới; hãng miễn phí nằm đầu.",
        "panel_ai": "Đang dùng: {name}",
        "acct_title": "Tài khoản AI",
        "acct_overview": "Tài khoản AI\n\nĐang có:\n{current}\n\nThêm được:\n{catalogue}",
        "acct_pick": "Gõ số hoặc tên nhà cung cấp muốn thêm (bỏ trống để đóng):",
        "acct_unknown": "Không có nhà cung cấp nào tên “{name}”.",
        "acct_field": "{label}\n\n{field}:",
        "acct_key": "{label}\n\nDán khoá API vào đây. Khoá đi thẳng vào kho bí mật của máy này ({ref}); không ghi vào providers.json và không hiện lại lần nào nữa.",
        "acct_client_secret": "{label}\n\nDán client secret của ứng dụng OAuth. Google cấp secret này cho cả ứng dụng Desktop. Nó đi vào kho bí mật của máy, không vào providers.json.",
        "acct_key_failed": "Không ghi được khoá vào kho bí mật của máy.",
        "acct_oauth_how": "{label}\n\nĐăng nhập bằng trình duyệt trên máy này?\n\nChọn Không để đăng nhập bằng mã ngắn trên máy khác.",
        "acct_device": "Mở:\n{url}\n\nrồi gõ mã này:\n\n{code}\n\nXong thì quay lại và bấm OK.",
        "acct_login_ok": "Đã đăng nhập: {state}.",
        "acct_login_failed": "Đăng nhập không thành công: {error}",
        "acct_model_ask": "Dùng mô hình nào? Đang có: {models}",
        "acct_model_free": "Gõ tên mô hình (với Azure OpenAI thì đây là tên deployment):",
        "acct_saved": "Đã lưu tài khoản “{id}” ({model}).\n\n{file}",
        "acct_nothing": "Chưa lưu gì cả.",
        "ai_bad_config": "providers.json đang có lỗi:\n\n{list}\n\nTệp: {path}",
        "ai_failed": "{error}",
        "csv_title": "Mở tệp CSV an toàn",
        "csv_done": "Đã mở {name} dưới dạng chữ: số 0 đầu, mã số và ngày tháng giữ nguyên như trong tệp, ô bắt đầu bằng \"=\" không bị chạy như công thức.",
        "csv_cancel": "",
        "xlsx_warning": ("Đã lưu dạng {ext}. Bảng tính đang dùng {n} công thức của 1xAIoffice ({names}).\n\n"
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
        if url.Path in ("Nd30Document", "Nd30Gallery"):  # works from any module: creates a new Writer document
            self.t = TEXTS[_ui_lang(self.ctx)]
            self.cmd_Nd30Document()
            return
        if url.Path in START_CARD_TYPES:   # thẻ mẫu trên Start Center: mở hộp soạn NĐ30 đã chọn sẵn loại
            self.t = TEXTS[_ui_lang(self.ctx)]
            self.cmd_Nd30Document(START_CARD_TYPES[url.Path])
            return
        if url.Path in START_CARD_BLANK:   # thẻ trống: mở ứng dụng ngay trong cửa sổ Start Center
            self._open_blank(START_CARD_BLANK[url.Path])
            return
        if url.Path == "AiAccounts":    # cần chạy được ở Start Center, nơi chưa có tài liệu nào
            self.t = TEXTS[_ui_lang(self.ctx)]
            self.cmd_AiAccounts(None, False)
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

    def cmd_AiSkill(self, doc, is_writer):
        """Chạy một skill: gói hướng dẫn sẵn cho trợ lý (ai-platform-design.md mục 9).

        Nạp từng phần: chỗ này chỉ đọc tên và mô tả của mọi skill; thân SKILL.md chỉ được đọc khi skill đã chọn.
        Lệnh **chỉ đọc**: nó trả lời bằng hộp thông báo, không tự sửa tài liệu. Muốn sửa thì dùng Viết lại bằng AI.
        """
        from vn1x import aicontext, skills
        config = self._ai_ready()
        if config is None:
            return
        found, problems = skills.discover(Path(__file__).resolve().parent / "skills",
                                          Path(self._profile_file("skills")))
        if problems:
            self.message(self.t["skill_broken"].format(n=len(problems), list="; ".join(problems)))
        app = "doc" if is_writer else "sheet"
        usable = skills.summaries(found, app=app)
        if not usable:
            self.message(self.t["skill_none"])
            return
        names = ", ".join(item["name"] for item in usable)
        wanted = os.environ.get("ONEX_SKILL_NAME")
        if wanted is None:
            wanted = self._ask_text(self.t["skill_title"], self.t["skill_prompt"].format(names=names))
            if not wanted:
                return
        skill = next((s for s in found if s["name"] == wanted.strip() and app in s["apps"]), None)
        if skill is None:
            self.message(self.t["skill_unknown"].format(name=wanted, names=names))
            return
        question = os.environ.get("ONEX_SKILL_QUESTION")
        if question is None:
            question = self._ask_text(skill["name"], skill["description"]) or ""
        selection, whole = self._document_text(doc, is_writer)
        document, _ = aicontext.trim(selection or whole)
        messages = [{"role": "system", "content": skills.prompt(skill, question)},
                    {"role": "user", "content": f"Tài liệu đang mở:\n\n{document}"}]
        answer = self._call_model(config, messages)
        if answer is None:
            return
        self.message(self.t["skill_answer"].format(answer=answer.strip(), name=skill["name"],
                                                   version=skill["version"]))

    def cmd_McpServer(self, doc, is_writer):
        """Bật/tắt máy chủ MCP của 1xAIoffice và duyệt những trợ lý đang xin phép.

        Mặc định TẮT (ai-platform-design.md mục 8 và bảng mục 14): chưa bật thì không trợ lý nào vào được.
        """
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent / "mcpserver"))
        state = self._mcp_server_state()
        if not state.get("enabled"):
            if not self.ask(self.t["mcpsrv_off"]):
                return
            state = {"enabled": True, "pipe": state.get("pipe") or f"1xaioffice-{os.getuid()}"}
            self._write_json(self._profile_file("mcp_server.json"), state)
            _start_acceptor(self.ctx, state["pipe"])
            self.message(self.t["mcpsrv_started"].format(config=self._mcp_server_config(state["pipe"])))
            return
        self._approve_pending_clients()
        allowed = ", ".join(sorted(self._mcp_clients().get("clients", {}))) or "(chưa có)"
        self.message(self.t["mcpsrv_on"].format(pipe=state["pipe"],
                                                config=self._mcp_server_config(state["pipe"]),
                                                clients=self.t["mcpsrv_clients"].format(allowed=allowed)))
        if self.ask(self.t["mcpsrv_stop"]):
            self._write_json(self._profile_file("mcp_server.json"), {"enabled": False, "pipe": state["pipe"]})
            self.message(self.t["mcpsrv_stopped"])

    def _mcp_server_state(self):
        try:
            return json.loads(Path(self._profile_file("mcp_server.json")).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"enabled": False}

    def _mcp_server_config(self, pipe):
        script = Path(__file__).resolve().parent / "mcpserver" / "server.py"
        return json.dumps({"mcpServers": {"1xaioffice": {"command": self._python_executable(),
                                                         "args": [str(script), "--pipe", pipe]}}},
                          ensure_ascii=False, indent=2)

    def _mcp_clients(self):
        import server as mcpserver
        try:
            data = json.loads(Path(mcpserver.clients_path()).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"clients": {}, "pending": {}}
        return {"clients": data.get("clients") or {}, "pending": data.get("pending") or {}}

    def _approve_pending_clients(self):
        """Trợ lý nào đã gõ cửa mà chưa được trả lời thì hỏi người dùng ngay ở đây."""
        import server as mcpserver
        data = self._mcp_clients()
        if not data["pending"]:
            return
        for name in sorted(data["pending"]):
            data["clients"][name] = "allow" if self.ask(self.t["mcpsrv_pair"].format(name=name)) else "deny"
        self._write_json(mcpserver.clients_path(), {"clients": data["clients"], "pending": {}})

    @staticmethod
    def _write_json(path, data):
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
        """(danh sách công cụ, lỗi). Mở máy chủ, hỏi công cụ, rồi tắt ngay.

        Máy chủ ở xa đi qua Agent Host, vì mọi kết nối mạng phải đi một đường và thẻ đăng nhập chỉ tiến trình
        đó được chạm vào. Máy chủ chạy bằng lệnh trên máy thì mở thẳng như trước.
        """
        if server.get("transport") == "http" or server.get("url"):
            return self._mcp_list_remote(server)
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent / "agenthost"))
        import mcpclient
        try:
            with mcpclient.StdioServer(server["command"], server.get("args") or [],
                                       env=server.get("env") or {}, cwd=server.get("cwd")) as mcp:
                return mcp.list_tools(), None
        except mcpclient.McpError as exc:
            return [], str(exc)

    def _mcp_list_remote(self, server, after_login=False):
        """Hỏi công cụ của một máy chủ MCP ở xa; máy chủ đòi đăng nhập thì mời người dùng đăng nhập rồi hỏi lại."""
        result = self._agent_host({"action": "mcp_list", "server": server}, timeout=60)
        if result.get("ok"):
            return result.get("tools") or [], None
        if result.get("code") != "mcp_login" or after_login:
            return [], result.get("error", "?")
        if not self.ask(self.t["mcp_login_ask"].format(id=server.get("id", "?"))):
            return [], result.get("error", "?")
        done = self._agent_host({"action": "mcp_login", "server": server,
                                 "challenge": result.get("challenge"), "timeout": 300}, timeout=330)
        if not done.get("ok"):
            self.message(self.t["mcp_login_failed"].format(id=server.get("id", "?"),
                                                           error=done.get("error", "?")))
            return [], done.get("error", "?")
        self.message(self.t["mcp_login_ok"].format(id=server.get("id", "?"), state=done.get("state", "")))
        return self._mcp_list_remote(server, after_login=True)

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
                    if server.get("transport") == "http" or server.get("url"):
                        where = {"transport": "http", "url": server["url"], "id": server.get("id", "")}
                    else:
                        where = {"command": server["command"], "args": server.get("args") or [],
                                 "env": server.get("env") or {}, "cwd": server.get("cwd")}
                    out.append(dict(tool, server=where))
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
            # Người dùng văn phòng không đi viết providers.json: mời mở thẳng màn hình Tài khoản AI, gắn xong
            # thì làm tiếp đúng việc họ vừa bấm.
            if not self.ask(self.t["ai_no_account"], default_yes=True):
                return None
            self.cmd_AiAccounts(None, False)
            try:
                config = aiconfig.load(path)
            except aiconfig.ConfigError:
                return None
            if not config.get("providers"):
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

    def cmd_AiAccounts(self, doc, is_writer):
        """Gắn tài khoản AI: khoá API của nhiều hãng, hoặc đăng nhập OAuth (trình duyệt / mã thiết bị).

        Khoá và thẻ KHÔNG bao giờ nằm trong providers.json: tệp đó chỉ giữ tên mục trong kho bí mật của máy.
        """
        from vn1x import aiconfig, aiproviders
        path = self._ai_config_path()
        try:
            config = aiconfig.load(path)
        except aiconfig.ConfigError as exc:
            self.message(self.t["ai_bad_config"].format(list=str(exc), path=path))
            return
        preset = self._pick_preset(config)
        if preset is None:
            return
        values = self._ask_preset_fields(preset)
        if values is None:
            return
        entry = aiproviders.fill(preset, values)
        if preset["auth"] == "key" and not self._take_api_key(preset, entry["secret_ref"]):
            return
        if preset["auth"] == "oauth":
            if preset.get("client_secret") and not self._take_client_secret(preset, entry):
                return
            if not self._sign_in(entry):
                return
        model = self._pick_model(preset, entry)
        if not model:
            self.message(self.t["acct_nothing"])
            return
        entry["models"] = [model] + [m for m in entry.get("models", []) if m != model]
        role = None if (config.get("roles") or {}).get(aiconfig.DEFAULT_ROLE) else aiconfig.DEFAULT_ROLE
        aiconfig.save(path, aiconfig.put_provider(config, entry, role=role))
        self.message(self.t["acct_saved"].format(id=entry["id"], model=model, file=path))

    @staticmethod
    def _scripted(key):
        """Câu trả lời dựng sẵn cho bước kiểm tự động trên app thật, nơi không bấm được vào hộp thoại.

        Lúc chạy thật không có biến môi trường này, nên mọi câu đều do người dùng trả lời.
        """
        path = os.environ.get("ONEX_ACCOUNT_ANSWERS_PATH")
        if path and Path(path).is_file():
            try:
                return json.loads(Path(path).read_text(encoding="utf-8")).get(key)
            except ValueError:
                return None
        return os.environ.get("ONEX_ACCOUNT_" + key.upper())

    def _pick_preset(self, config):
        """Nhà cung cấp người dùng chọn trong danh mục, hoặc None khi thoát."""
        from vn1x import aiconfig, aiproviders
        current = "\n".join(
            f"- {p.get('id')} ({aiconfig.auth_mode(p)}, {', '.join(p.get('models') or []) or 'chưa chọn mô hình'})"
            for p in config.get("providers") or []) or "(chưa có)"
        ordered = aiproviders.free_first()      # hãng có gói miễn phí lên đầu, để người mới không phải trả tiền
        catalogue = "\n".join(f"{i}. {aiproviders.summary(preset)}" for i, preset in enumerate(ordered, 1))
        wanted = self._scripted("preset")
        if not wanted:
            self.message(self.t["acct_overview"].format(current=current, catalogue=catalogue))
            wanted = self._ask_text(self.t["acct_title"], self.t["acct_pick"])
        if not wanted:
            return None
        wanted = wanted.strip()
        if wanted.isdigit() and 1 <= int(wanted) <= len(ordered):
            return ordered[int(wanted) - 1]
        preset = aiproviders.BY_ID.get(wanted)
        if preset is None:
            self.message(self.t["acct_unknown"].format(name=wanted))
        return preset

    def _ask_preset_fields(self, preset):
        """Những thứ nhà cung cấp này còn đòi (client_id, tenant, địa chỉ...). None khi người dùng huỷ."""
        given = self._scripted("fields") or {}
        values = dict(given)
        for field in preset.get("needs") or []:
            if given.get(field):
                values[field] = given[field]
                continue
            answer = self._ask_text(self.t["acct_title"],
                                    self.t["acct_field"].format(label=preset["note"],
                                                                field=FIELD_LABELS.get(field, field)))
            if not answer:
                return None
            values[field] = answer.strip()
        return values

    def _take_api_key(self, preset, ref):
        """Nhận khoá API và đưa thẳng vào kho bí mật của máy. Không ghi ra tệp, không hiện lại."""
        key = self._scripted("secret")
        if key is None and preset.get("key_url") and self.ask(
                self.t["acct_open_key_page"].format(label=preset["label"], url=preset["key_url"]), default_yes=True):
            # Người dùng tự đăng nhập và tự tạo khoá trên trang của hãng; app chỉ mở trang, không đụng vào đó.
            self._open_url(preset["key_url"])
        if key is None:
            key = self._ask_text(self.t["acct_title"],
                                 self.t["acct_key"].format(label=preset["label"], ref=ref), secret=True)
        if not key:
            return False
        if not self._store_secret(ref, key.strip()):
            self.message(self.t["acct_key_failed"])
            return False
        return True

    def _open_blank(self, factory):
        """Tài liệu trống: ngay trong cửa sổ hiện tại nếu đó là Start Center, không thì một cửa sổ mới."""
        current = self.frame.getController().getModel() if self.frame else None
        if current is None and self.frame is not None:
            self.frame.loadComponentFromURL(factory, "_self", 0, ())
        else:
            desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
            desktop.loadComponentFromURL(factory, "_blank", 0, ())

    def _open_url(self, url):
        """Mở trang trong trình duyệt mặc định của máy (thường là Chrome), ở một thẻ mới."""
        try:
            shell = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.system.SystemShellExecute", self.ctx)
            shell.execute(url, "", 1)        # 1 = URIS_ONLY: chỉ mở địa chỉ, không chạy tệp
            return True
        except Exception:                   # noqa: BLE001 - không mở được thì người dùng vẫn tự gõ địa chỉ
            self.message(self.t["acct_open_failed"].format(url=url))
            return False

    def _take_client_secret(self, preset, entry):
        """Nhận client secret của ứng dụng OAuth và cất vào kho bí mật. Google đòi nó cả với ứng dụng Desktop."""
        from vn1x import aiproviders
        ref = entry["oauth"]["client_secret_ref"]
        value = self._scripted("client_secret")
        if value is None:
            value = self._ask_text(self.t["acct_title"],
                                   self.t["acct_client_secret"].format(label=preset["label"]), secret=True)
        if not value:
            return False
        if not self._store_secret(ref, value.strip()):
            self.message(self.t["acct_key_failed"])
            return False
        return True

    @staticmethod
    def _store_secret(ref, value):
        """Ghi một bí mật vào Keychain qua ĐẦU VÀO CHUẨN, nên giá trị không nằm trong tham số dòng lệnh."""
        import subprocess
        override = os.environ.get("ONEX_SECRET_STORE_FOR_TEST")
        if override:
            store = {}
            if Path(override).is_file():
                try:
                    store = json.loads(Path(override).read_text(encoding="utf-8") or "{}")
                except ValueError:
                    store = {}
            store[ref] = value
            Path(override).write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
            return True
        # Qua `security -i`: giá trị không nằm trong tham số dòng lệnh, và không bị cắt ở 128 ký tự như khi
        # `security` hỏi trên bàn phím. Khoá API của nhiều hãng dài hơn 128 ký tự.
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent / "agenthost"))
        import oauthflow
        return oauthflow.keychain_write(ref, value)

    def _sign_in(self, entry):
        """Đăng nhập OAuth: trình duyệt trên máy này, hoặc mã ngắn gõ ở máy khác."""
        mode = self._scripted("login")
        browser = mode != "device" if mode else self.ask(
            self.t["acct_oauth_how"].format(label=entry["id"]))
        if browser:
            result = self._agent_host({"action": "login", "provider": entry, "timeout": 300}, timeout=330)
        else:
            started = self._agent_host({"action": "device_start", "provider": entry}, timeout=60)
            if not started.get("ok"):
                self.message(self.t["acct_login_failed"].format(error=started.get("error", "?")))
                return False
            self.message(self.t["acct_device"].format(url=started.get("url", ""),
                                                      code=started.get("user_code", "")))
            result = self._agent_host({"action": "device_poll", "provider": entry,
                                       "device_code": started["device_code"],
                                       "interval": started.get("interval", 5), "timeout": 300}, timeout=330)
        if not result.get("ok"):
            self.message(self.t["acct_login_failed"].format(error=result.get("error", "?")))
            return False
        # Nhà cung cấp cấp client_id cho riêng máy này ở lần đăng nhập đầu; giữ lại để lần sau khỏi đăng ký lại.
        if result.get("issued_client_id"):
            entry["oauth"]["client_id"] = result["issued_client_id"]
        self.message(self.t["acct_login_ok"].format(state=result.get("state", "")))
        return True

    def _pick_model(self, preset, entry):
        """Tên mô hình sẽ dùng. Hỏi nhà cung cấp trước để người dùng khỏi gõ tay, hỏi không được thì gõ tay."""
        chosen = self._scripted("model")
        if chosen:
            return chosen.strip()
        models = list(entry.get("models") or [])
        if preset.get("can_list_models"):
            listed = self._agent_host({"action": "models", "provider": entry}, timeout=60)
            if listed.get("ok") and listed.get("models"):
                models = listed["models"]
        if not models:
            answer = self._ask_text(self.t["acct_title"], self.t["acct_model_free"])
            return (answer or "").strip()
        answer = self._ask_text(self.t["acct_title"],
                                self.t["acct_model_ask"].format(models=", ".join(models[:20])))
        return (answer or "").strip() or models[0]

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

    def _agent_host(self, request, timeout=120):
        """Gọi tiến trình Agent Host. Mọi kết nối mạng đi qua đây, không đi thẳng từ trong tài liệu."""
        import subprocess
        host = Path(__file__).resolve().parent / "agenthost" / "host.py"
        if not host.is_file():
            return {"ok": False, "error": f"không thấy Agent Host tại {host}"}
        try:
            done = subprocess.run([self._python_executable(), "-I", str(host)],
                                  input=json.dumps(request), capture_output=True, text=True, timeout=timeout)
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

    def _ask_text(self, title, prompt, secret=False):
        """Hộp nhập một dòng. `secret=True` thì che chữ (dùng cho khoá API). Trả về None khi huỷ."""
        if os.environ.get("ONEX_TOOLS_SILENT") == "1" or self.frame is None:
            return ""
        smgr = self.ctx.ServiceManager
        model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", self.ctx)
        # Lời nhắc dài nhất (dán khoá API) chiếm 4-5 dòng, nên chừa 56 đơn vị cho nhãn.
        model.Width, model.Height, model.Title = 260, 112, title
        label = model.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
        label.PositionX, label.PositionY, label.Width, label.Height, label.MultiLine = 8, 8, 244, 56, True
        label.Label = prompt
        model.insertByName("lbl", label)
        edit = model.createInstance("com.sun.star.awt.UnoControlEditModel")
        edit.PositionX, edit.PositionY, edit.Width, edit.Height = 8, 68, 244, 16
        if secret:
            edit.EchoChar = ord("*")
        model.insertByName("q", edit)
        for name, text, kind, pos in (("ok", "OK", 1, 0), ("cancel", self.t["cancel"], 2, 1)):
            button = model.createInstance("com.sun.star.awt.UnoControlButtonModel")
            button.PositionX, button.PositionY = model.Width - (pos + 1) * 60, 92
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
        doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(path), "_blank", 0, tuple(args))
        self._tidy_csv(doc)
        self.message(self.t["csv_done"].format(name=os.path.basename(path)))

    def _tidy_csv(self, doc):
        """Giãn cột cho vừa chữ, và nếu dòng đầu là tiêu đề thì tô đậm rồi ghim lại.

        Mở CSV ra mà cột nào cũng hẹp, phải tự kéo từng cái, là việc máy làm được thay người. Sửa xong đặt lại
        cờ "chưa sửa đổi": người dùng chỉ mở ra xem, đóng lại không nên bị hỏi có lưu không.
        """
        from vn1x import csvsafe
        if doc is None or not hasattr(doc, "getSheets"):
            return
        try:
            sheet = doc.getSheets().getByIndex(0)
            cursor = sheet.createCursor()
            cursor.gotoEndOfUsedArea(False)
            area = cursor.getRangeAddress()
            if area.EndColumn < 0 or area.EndRow < 0:
                return
            columns = sheet.getColumns()
            for index in range(area.EndColumn + 1):
                columns.getByIndex(index).OptimalWidth = True

            def row_text(row):
                return [sheet.getCellByPosition(col, row).getString() for col in range(area.EndColumn + 1)]

            if area.EndRow >= 1 and csvsafe.looks_like_header(row_text(0), row_text(1)):
                header = sheet.getCellRangeByPosition(0, 0, area.EndColumn, 0)
                header.CharWeight = BOLD_WEIGHT
                controller = doc.getCurrentController()
                if hasattr(controller, "freezeAtPosition"):
                    controller.freezeAtPosition(0, 1)
            doc.setModified(False)
        except Exception:  # noqa: BLE001 - dọn dẹp cho đẹp mắt, hỏng thì tệp vẫn mở bình thường
            return

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

    def cmd_Nd30Document(self, doc_type=None):
        # ONEX_TOOLS_ND30_FIELDS (JSON) bypasses the dialog for automated tests.
        raw = os.environ.get("ONEX_TOOLS_ND30_FIELDS")
        if raw:
            fields = json.loads(raw)
            if fields.get("date"):
                fields["date"] = datetime.date.fromisoformat(fields["date"])
        else:
            from vn1x import nd30_dialog
            parent = self.frame.getContainerWindow() if self.frame else None
            fields = nd30_dialog.run(self.ctx, parent, "vi" if self.t is TEXTS["vi"] else "en", doc_type)
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
        elif current is None and self.frame is not None:
            # Gọi từ Start Center: mở Writer ngay trong cửa sổ đó, như bấm "Document", không bật thêm cửa sổ.
            doc = self.frame.loadComponentFromURL("private:factory/swriter", "_self", 0, ())
        else:
            desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
            doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
        nd30_writer.fill(doc, spec)
        # Loại có hiệu lực pháp lý giữa các bên thì nhắc một lần, ở hộp thoại chứ không trong văn bản.
        warning = nd30.template_warning(fields.get("type", "")) if not fields.get("body") else ""
        if warning:
            self.message(warning)

    def ask(self, text, default_yes=False):
        """Hỏi Có/Không. Khi chạy tự động (ONEX_TOOLS_SILENT) thì coi như Có, để bước kiểm chạy được phần sửa.

        `default_yes` cho những lời mời người dùng vừa tự bấm tới (mở trang lấy khoá, gắn tài khoản): Enter là Có.
        Câu hỏi có thể làm thay đổi tài liệu giữ mặc định Không.
        """
        if os.environ.get("ONEX_TOOLS_SILENT") == "1" or self.frame is None:
            return os.environ.get("ONEX_TOOLS_CHECK_FIX") == "1"
        from com.sun.star.awt.MessageBoxType import QUERYBOX
        toolkit = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        buttons = 3 | (0x40000 if default_yes else 0)   # BUTTONS_YES_NO, DEFAULT_BUTTON_YES
        box = toolkit.createMessageBox(self.frame.getContainerWindow(), QUERYBOX, buttons, self.t["title"], text)
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


# Thẻ trên dải "Bắt đầu tài liệu mới" của Start Center (bản vá 0004). Nhãn nằm ở GenericCommands.xcu.
START_CARD_TYPES = {"NewCongVan": "cong_van", "NewToTrinh": "to_trinh", "NewQuyetDinh": "quyet_dinh",
                    "NewBienBan": "bien_ban"}
START_CARD_BLANK = {"NewTextDocument": "private:factory/swriter", "NewSpreadsheet": "private:factory/scalc",
                    "NewPresentation": "private:factory/simpress"}

MCP_EXAMPLE = json.dumps({
    "mcpServers": {
        "giay-to": {"command": "python3", "args": ["/duong/dan/toi/may_chu_mcp.py"], "env": {}},
    },
}, ensure_ascii=False, indent=2)

AI_EXAMPLE = json.dumps({
    "providers": [
        {"id": "claude", "type": "anthropic", "secret_ref": "1xaioffice/anthropic",
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
        """Hàm bảng tính của 1xAIoffice: =DOCSO(số; ["lẻ"|"linh"]), =DOCTIEN(số tiền; [đơn vị, mặc định "đồng"]),
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


MCP_ACCEPTOR_IMPL = "org.1xaioffice.tools.McpAcceptor"
_ACCEPTING = set()        # tên pipe đang nghe, để không mở hai lần trong một phiên


def _start_acceptor(ctx, pipe):
    """Mở cửa cho máy chủ MCP nối vào phiên này, qua một UNO pipe cục bộ.

    Pipe là socket của riêng người dùng trên máy này, KHÔNG phải cổng mạng: không máy nào khác với tới được.
    Chỉ chạy khi người dùng đã bật máy chủ MCP (mặc định tắt). Lỗi ở đây không được làm hỏng phiên làm việc.
    """
    import threading
    if pipe in _ACCEPTING:
        return
    _ACCEPTING.add(pipe)

    class Provider(unohelper.Base, XInstanceProvider):
        def getInstance(self, name):      # noqa: N802 - tên theo UNO
            if name in ("StarOffice.ComponentContext", "StarOffice.ServiceManager"):
                return ctx if name.endswith("ComponentContext") else ctx.ServiceManager
            return ctx.ServiceManager.createInstanceWithContext(name, ctx)

    def listen():
        try:
            acceptor = ctx.ServiceManager.createInstanceWithContext("com.sun.star.connection.Acceptor", ctx)
            factory = ctx.ServiceManager.createInstanceWithContext("com.sun.star.bridge.BridgeFactory", ctx)
            while pipe in _ACCEPTING:
                connection = acceptor.accept(f"pipe,name={pipe}")
                if connection is None:
                    break
                factory.createBridge("", "urp", connection, Provider())
        except Exception:  # noqa: BLE001 - cửa không mở được thì thôi, phiên làm việc vẫn chạy bình thường
            _ACCEPTING.discard(pipe)

    threading.Thread(target=listen, daemon=True).start()


class McpAcceptor(unohelper.Base, XJob):
    """Mở lại cửa MCP khi khởi động, nhưng CHỈ khi người dùng đã bật (mcp_server.json, mặc định tắt)."""

    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, args):
        try:
            subst = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.util.PathSubstitution", self.ctx)
            base = Path(uno.fileUrlToSystemPath(subst.substituteVariables("$(userurl)", True)))
            state = json.loads((base / "mcp_server.json").read_text(encoding="utf-8"))
            if state.get("enabled") and state.get("pipe"):
                _start_acceptor(self.ctx, state["pipe"])
        except Exception:  # noqa: BLE001 - chưa bật, chưa có tệp, hay tệp hỏng: im lặng bỏ qua
            pass
        return ()


GUIDES_IMPL = "org.1xaioffice.tools.GuideSeeder"


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


WARNER_IMPL = "org.1xaioffice.tools.XlsxWarner"
ADDIN_MARK = "ORG.ONEXVN.TOOLS."          # công thức của add-in hiện ra dưới tên đầy đủ này
RISKY_EXT = (".xlsx", ".xls", ".xlsm", ".csv")


def _addin_formulas(doc):
    """Tên các hàm của 1xAIoffice đang dùng trong bảng tính, không trùng lặp."""
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
    """Sau khi lưu bảng tính sang định dạng Excel, nhắc rằng hàm riêng của 1xAIoffice không tính lại được ở Excel.
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


# ---------------------------------------------------------------- thanh bên AI
# Một mục "AI" trên dải thẻ thanh bên phải (Sidebar.xcu, Factories.xcu). AI chỉ hiện ở đây khi người dùng mở nó,
# không chen vào Start Center. Panel dựng từ dialogs/AiPanel.xdl; mỗi nút gọi đúng lệnh vnd.1x.tools như ribbon.
PANEL_FACTORY_IMPL = "org.1xaioffice.tools.PanelFactory"
PANEL_ROWS = [("status", "text"), ("AiAsk", "btn"), ("AiRewrite", "btn"), ("AiSkill", "btn"), ("sep1", "line"),
              ("Nd30Document", "btn"), ("Nd30Check", "btn"), ("sep2", "line"), ("McpTools", "btn"),
              ("AiAccounts", "btn")]
PANEL_WRITER_ONLY = {"AiRewrite", "Nd30Document", "Nd30Check", "sep1"}

try:
    from com.sun.star.ui import XUIElementFactory, XUIElement, XToolPanel, XSidebarPanel
    from com.sun.star.awt import XContainerWindowEventHandler
except ImportError:  # chạy ngoài office (kiểm logic): không có thanh bên
    XUIElementFactory = None


def _command_label(ctx, module, command):
    """Nhãn ngắn (Label, như trên ribbon) của một lệnh trong bảng mô tả lệnh, theo ngôn ngữ giao diện. Thanh bên hẹp,
    nhãn dài kiểu menu bị cắt mất đầu chữ."""
    try:
        desc = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.UICommandDescription", ctx)
        props = {p.Name: p.Value for p in desc.getByName(module).getByName(command)}
        return (props.get("Label") or props.get("PopupLabel") or "").replace("~", "")
    except Exception:  # noqa: BLE001
        return ""


if XUIElementFactory is not None:
    class AiPanel(unohelper.Base, XToolPanel, XSidebarPanel, XContainerWindowEventHandler):
        def __init__(self, ctx, frame, parent):
            self.ctx, self.frame = ctx, frame
            self.t = TEXTS[_ui_lang(ctx)]
            info = ctx.getValueByName("/singletons/com.sun.star.deployment.PackageInformationProvider")
            url = info.getPackageLocation("org.1xaioffice.tools") + "/dialogs/AiPanel.xdl"
            provider = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.ContainerWindowProvider", ctx)
            self.window = provider.createContainerWindow(url, "", parent, self)
            manager = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.ModuleManager", ctx)
            try:
                self.module = manager.identify(frame)
            except Exception:  # noqa: BLE001
                self.module = "com.sun.star.text.TextDocument"
            self.writer = self.module == "com.sun.star.text.TextDocument"
            for name, kind in PANEL_ROWS:
                control = self.window.getControl(name)
                if control is None:
                    continue
                if not self.writer and name in PANEL_WRITER_ONLY:
                    control.setVisible(False)
                elif kind == "btn":
                    control.getModel().Label = _command_label(ctx, self.module, "vnd.1x.tools:" + name) or name
            self.refresh()
            self.window.setVisible(True)
            self.height = 0

        def refresh(self):
            from vn1x import aiconfig, aipanel
            try:
                subst = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.util.PathSubstitution", self.ctx)
                profile = uno.fileUrlToSystemPath(subst.substituteVariables("$(userurl)", True))
                config = aiconfig.load(os.environ.get("ONEX_AI_CONFIG_PATH") or str(Path(profile) / aiconfig.FILENAME))
            except Exception:  # noqa: BLE001 - tệp hỏng thì coi như chưa gắn
                config = {}
            status = self.window.getControl("status")
            if status is not None:
                status.getModel().Label = aipanel.status(config, self.t)

        def layout(self, width):
            """Xếp các dòng theo bề rộng thanh bên (pixel); trả về chiều cao cần."""
            pad, y = 8, 8
            for name, kind in PANEL_ROWS:
                control = self.window.getControl(name)
                if control is None or (not self.writer and name in PANEL_WRITER_ONLY):
                    continue
                h = {"text": 64, "line": 10, "btn": 30}[kind]
                control.setPosSize(pad, y, max(width - 2 * pad, 120), h, 15)
                y += h + (4 if kind == "btn" else 2)
            return y + pad

        # XContainerWindowEventHandler
        def callHandlerMethod(self, window, event, method):
            if method != "onClick":
                return False
            name = event.Source.getModel().Name
            helper = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.DispatchHelper", self.ctx)
            helper.executeDispatch(self.frame, "vnd.1x.tools:" + name, "", 0, ())
            self.refresh()                      # vừa gắn tài khoản thì dòng trạng thái đổi ngay
            return True

        def getSupportedMethodNames(self):
            return ("onClick",)

        # XToolPanel
        def getWindow(self):
            return self.window

        def createAccessible(self, parent):
            return self.window.getAccessibleContext()

        # XSidebarPanel
        def getHeightForWidth(self, width):
            h = self.layout(width)
            size = uno.createUnoStruct("com.sun.star.ui.LayoutSize")
            size.Minimum = size.Maximum = size.Preferred = h
            return size

        def getMinimalWidth(self):
            return 180

    class AiPanelElement(unohelper.Base, XUIElement):
        def __init__(self, url, frame, panel):
            self.ResourceURL, self.Frame, self.panel = url, frame, panel
            self.Type = 7                       # com.sun.star.ui.UIElementType.TOOLPANEL

        def getRealInterface(self):
            return self.panel

    class PanelFactory(unohelper.Base, XUIElementFactory, XServiceInfo):
        def __init__(self, ctx, *args):
            self.ctx = ctx

        def createUIElement(self, url, args):
            values = {a.Name: a.Value for a in args}
            frame, parent = values.get("Frame"), values.get("ParentWindow")
            if not url.endswith("/AiPanel") or frame is None or parent is None:
                return None
            return AiPanelElement(url, frame, AiPanel(self.ctx, frame, parent))

        def getImplementationName(self):
            return PANEL_FACTORY_IMPL

        def supportsService(self, name):
            return name == "com.sun.star.ui.UIElementFactory"

        def getSupportedServiceNames(self):
            return ("com.sun.star.ui.UIElementFactory",)


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(Handler, IMPL, ("com.sun.star.frame.ProtocolHandler",))
g_ImplementationHelper.addImplementation(GuideSeeder, GUIDES_IMPL, ("com.sun.star.task.Job",))
g_ImplementationHelper.addImplementation(XlsxWarner, WARNER_IMPL, ("com.sun.star.task.Job",))
g_ImplementationHelper.addImplementation(McpAcceptor, MCP_ACCEPTOR_IMPL, ("com.sun.star.task.Job",))
if XVnSheetFunctions is not None:
    g_ImplementationHelper.addImplementation(SheetFunctions, SHEET_IMPL, ("com.sun.star.sheet.AddIn",))
if XUIElementFactory is not None:
    g_ImplementationHelper.addImplementation(PanelFactory, PANEL_FACTORY_IMPL, ("com.sun.star.ui.UIElementFactory",))
