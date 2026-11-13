# SPDX-License-Identifier: MPL-2.0
"""Lớp chạm vào tài liệu cho MCP server: nối vào một phiên 1xVnOffice đang chạy qua UNO.

Chạy trong tiến trình của máy chủ MCP, không trong tiến trình office, nên một client MCP cư xử tệ không làm sập
tài liệu người dùng đang mở.

Công cụ ghi đi qua **hộp hỏi hiện ngay trong app**: người dùng thấy sẽ sửa gì rồi mới quyết, và mọi thay đổi gom
trong một bước hoàn tác (Ctrl+Z một lần là trả lại như cũ). Biến ONEX_MCP_AUTO_APPLY=1 bỏ qua bước hỏi, chỉ dùng
cho bài kiểm tự động.
"""
import os
import sys
from pathlib import Path

import uno
from com.sun.star.awt.MessageBoxButtons import BUTTONS_YES_NO
from com.sun.star.awt.MessageBoxType import QUERYBOX

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import doctools, nd30_check, nd30_check_writer, vntext  # noqa: E402

WRITER = "com.sun.star.text.TextDocument"
CALC = "com.sun.star.sheet.SpreadsheetDocument"
DRAW = "com.sun.star.presentation.PresentationDocument"
KINDS = [(WRITER, "văn bản"), (CALC, "bảng tính"), (DRAW, "trình chiếu")]


class OfficeBackend:
    """Mỗi phương thức ứng với một công cụ trong vn1x/doctools.py (dấu chấm đổi thành gạch dưới)."""

    def __init__(self, pipe):
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        self.ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
        self.desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)

    # --- tìm tài liệu ---
    def _documents(self):
        out = []
        components = self.desktop.getComponents().createEnumeration()
        index = 0
        while components.hasMoreElements():
            component = components.nextElement()
            if not hasattr(component, "supportsService"):
                continue
            index += 1
            out.append((f"d{index}", component))
        return out

    def _find(self, doc_id):
        for name, component in self._documents():
            if name == doc_id:
                return component
        raise doctools.ToolError(f"không thấy tài liệu có mã {doc_id!r}; gọi docs.list_open để xem mã đúng")

    @staticmethod
    def _kind(component):
        for service, label in KINDS:
            if component.supportsService(service):
                return label
        return "khác"

    @staticmethod
    def _title(component):
        url = component.getURL() or ""
        return os.path.basename(uno.fileUrlToSystemPath(url)) if url.startswith("file://") else "(chưa đặt tên)"

    # --- hỏi người dùng trước khi ghi ---
    def _confirm(self, question):
        if os.environ.get("ONEX_MCP_AUTO_APPLY") == "1":
            return True
        toolkit = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        box = toolkit.createMessageBox(None, QUERYBOX, BUTTONS_YES_NO, "1xVnOffice", question)
        try:
            return box.execute() == 2      # 2 = YES
        finally:
            box.dispose()

    @staticmethod
    def _paragraphs(component):
        if not component.supportsService(WRITER):
            raise doctools.ToolError("công cụ này chỉ dùng được cho tài liệu văn bản")
        return list(component.getText().createEnumeration())

    # --- công cụ đọc ---
    def docs_list_open(self):
        lines = []
        for name, component in self._documents():
            saved = "đã lưu" if not getattr(component, "isModified", lambda: False)() else "chưa lưu"
            lines.append(f"{name}: {self._title(component)} ({self._kind(component)}, {saved})")
        return "\n".join(lines) or "Không có tài liệu nào đang mở."

    def doc_read(self, doc, cursor=0):
        component = self._find(doc)
        if component.supportsService(WRITER):
            text = component.getText().getString().replace("\r\n", "\n")
        elif component.supportsService(CALC):
            raise doctools.ToolError("đây là bảng tính; dùng sheet.read_range")
        else:
            raise doctools.ToolError("chỉ đọc được tài liệu văn bản ở mốc này")
        return doctools.page(text, cursor)

    def doc_outline(self, doc):
        component = self._find(doc)
        lines = []
        for index, para in enumerate(self._paragraphs(component)):
            if not hasattr(para, "ParaStyleName"):
                lines.append(f"[{index}] (bảng)")
                continue
            style = para.ParaStyleName or ""
            body = " ".join(para.getString().split())
            if style.startswith("Heading") or style.startswith("Tiêu đề"):
                lines.append(f"[{index}] {style}: {body[:120]}")
        return "\n".join(lines) or "Tài liệu không có tiêu đề nào."

    def doc_nd30_check(self, doc):
        component = self._find(doc)
        if not component.supportsService(WRITER):
            raise doctools.ToolError("kiểm thể thức NĐ30 chỉ dùng cho tài liệu văn bản")
        issues = nd30_check.check(nd30_check_writer.describe(component))
        if not issues:
            return "Không thấy lỗi thể thức nào đo được."
        return "\n".join(f"- {issue.message}" for issue in issues)

    def sheet_read_range(self, doc, range):      # noqa: A002 - tên tham số theo lược đồ MCP
        component = self._find(doc)
        if not component.supportsService(CALC):
            raise doctools.ToolError("công cụ này chỉ dùng cho bảng tính")
        name, _, cells = range.partition(".")
        if not cells:
            raise doctools.ToolError("vùng phải có dạng 'Sheet1.A1:D20'")
        sheets = component.getSheets()
        if not sheets.hasByName(name):
            raise doctools.ToolError(f"không có trang tính tên {name!r}")
        area = sheets.getByName(name).getCellRangeByName(cells)
        lines = []
        for row in area.getDataArray():
            lines.append("\t".join("" if value == "" else str(value) for value in row))
        return doctools.page("\n".join(lines))

    # --- công cụ ghi: luôn hỏi trước ---
    def doc_insert(self, doc, text, where="end", anchor=None):
        component = self._find(doc)
        paragraphs = self._paragraphs(component)
        preview = " ".join(text.split())[:300]
        if not self._confirm(f"Một trợ lý AI muốn chèn nội dung vào tài liệu:\n\n{preview}\n\nCho phép?"):
            return "Người dùng đã từ chối. Tài liệu không đổi."
        body = component.getText()
        with _undo(component, "MCP: chèn nội dung"):
            if where == "start":
                cursor = body.createTextCursorByRange(body.getStart())
                body.insertString(cursor, text + "\n", False)
            elif where == "after":
                if anchor is None or anchor >= len(paragraphs):
                    raise doctools.ToolError("mốc 'after' cần tham số anchor là số thứ tự đoạn có thật")
                cursor = body.createTextCursorByRange(paragraphs[anchor].getEnd())
                body.insertString(cursor, "\n" + text, False)
            else:
                cursor = body.createTextCursorByRange(body.getEnd())
                body.insertString(cursor, "\n" + text, False)
        return "Đã chèn. Người dùng bấm Ctrl+Z một lần là trả lại như cũ."

    def doc_replace(self, doc, anchor, text):
        component = self._find(doc)
        paragraphs = self._paragraphs(component)
        if anchor >= len(paragraphs):
            raise doctools.ToolError(f"tài liệu chỉ có {len(paragraphs)} đoạn")
        old = " ".join(paragraphs[anchor].getString().split())
        new = " ".join(text.split())
        if not self._confirm(f"Một trợ lý AI muốn thay một đoạn trong tài liệu.\n\n"
                             f"Trước:\n{old[:300]}\n\nSau:\n{new[:300]}\n\nCho phép?"):
            return "Người dùng đã từ chối. Tài liệu không đổi."
        with _undo(component, "MCP: thay đoạn"):
            paragraphs[anchor].setString(text)
        return "Đã thay. Người dùng bấm Ctrl+Z một lần là trả lại như cũ."

    def vn_convert_legacy(self, doc, kind):
        convert = {"tcvn3": vntext.tcvn3_to_unicode, "vni": vntext.vni_to_unicode,
                   "viqr": vntext.viqr_to_unicode}[kind]
        return self._rewrite(doc, convert, f"MCP: chuyển mã {kind.upper()}",
                             f"Một trợ lý AI muốn chuyển chữ {kind.upper()} trong tài liệu sang Unicode. Cho phép?")

    def vn_normalize(self, doc):
        return self._rewrite(doc, vntext.normalize_full, "MCP: chuẩn hoá chữ Việt",
                             "Một trợ lý AI muốn chuẩn hoá chữ Việt trong tài liệu (NFC, khoảng trắng). Cho phép?")

    def _rewrite(self, doc, func, title, question):
        component = self._find(doc)
        paragraphs = self._paragraphs(component)
        changed = [(para, func(para.getString())) for para in paragraphs if hasattr(para, "getString")]
        changed = [(para, new) for para, new in changed if new != para.getString()]
        if not changed:
            return "Không có gì để đổi."
        if not self._confirm(f"{question}\n\nSố đoạn sẽ đổi: {len(changed)}."):
            return "Người dùng đã từ chối. Tài liệu không đổi."
        with _undo(component, title):
            for para, new in changed:
                para.setString(new)
        return f"Đã đổi {len(changed)} đoạn. Người dùng bấm Ctrl+Z một lần là trả lại như cũ."


class _undo:
    """Gom mọi thay đổi vào MỘT bước hoàn tác."""

    def __init__(self, component, title):
        self.manager = getattr(component, "UndoManager", None)
        self.title = title

    def __enter__(self):
        if self.manager:
            self.manager.enterUndoContext(self.title)

    def __exit__(self, *exc):
        if self.manager:
            self.manager.leaveUndoContext()
        return False
