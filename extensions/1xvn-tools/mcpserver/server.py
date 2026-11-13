#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""1xVnOffice làm **máy chủ MCP**: Claude Desktop, Cursor hay trợ lý khác đọc và sửa tài liệu đang mở.

Theo ai-platform-design.md mục 8. Ở mốc này chỉ có bản **stdio**; bản HTTP nghe ở 127.0.0.1 kèm token để sau
(xem plans/reports/buildnotes-261114-0051-ai-platform-mcp.md, default #3 và mục "không mở cổng mạng nào").

Chạy: `python3 mcpserver/server.py --pipe <tên pipe>` — nối vào một phiên 1xVnOffice đang chạy qua UNO.
Không có phiên nào thì máy chủ vẫn trả lời tools/list, nhưng mọi lần gọi công cụ đều báo chưa có tài liệu.

Ba điều giữ cho an toàn:

1. **Ghép đôi.** Client lạ phải được người dùng cho phép một lần (`mcp_clients.json` trong hồ sơ người dùng).
   Chưa ghép đôi thì chỉ xem được danh sách công cụ, không gọi được gì.
2. **Công cụ ghi không tự sửa tài liệu.** Lớp UNO đưa chúng qua xem trước và một bước hoàn tác như lệnh AI
   trong app; client nhận về "đã áp dụng", "bị từ chối" hoặc "chờ người dùng".
3. **Lời của client là dữ liệu.** Máy chủ chỉ chạy đúng những công cụ trong bảng ở `vn1x/doctools.py`.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import doctools  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "1xVnOffice", "version": "0.1.0"}


class Unpaired(RuntimeError):
    """Client chưa được người dùng cho phép."""


def clients_path():
    override = os.environ.get("ONEX_MCP_CLIENTS_PATH")
    return override or str(Path.home() / ".config" / "1xvnoffice" / "mcp_clients.json")


def paired(name, path=None):
    """Client này đã được người dùng cho phép chưa. Tệp hỏng hay chưa có thì coi như CHƯA."""
    file = Path(path or clients_path())
    if not file.is_file():
        return False
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except ValueError:
        return False
    return (data.get("clients") or {}).get(name) == "allow"


def remember_pending(name, path=None):
    """Ghi lại client vừa xin phép, để 1xVnOffice hỏi người dùng ở lần mở lệnh Công cụ AI (MCP) tới.

    Chỉ ghi tên client; không bao giờ ghi nội dung yêu cầu. Tệp hỏng thì dựng lại từ đầu thay vì chết.
    """
    import time
    file = Path(path or clients_path())
    try:
        data = json.loads(file.read_text(encoding="utf-8")) if file.is_file() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("clients", {})
    pending = data.setdefault("pending", {})
    pending[name] = int(time.time())
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass                              # không ghi được thì thôi, không làm hỏng lời gọi


class Server:
    """Vòng đọc stdin, trả lời stdout. `backend` là lớp chạm vào tài liệu (None = chưa nối được phiên nào)."""

    def __init__(self, backend=None, clients_file=None, stdin=None, stdout=None):
        self.backend = backend
        self.clients_file = clients_file
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.client = ""

    # --- giao thức ---
    def send(self, message):
        self.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.stdout.flush()

    def run(self):
        for line in self.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue                 # dòng rác thì bỏ qua, không làm chết máy chủ
            if "id" not in message:
                continue                 # thông báo một chiều: không phải trả lời
            self.send(self.answer(message))

    def answer(self, message):
        method, params = message.get("method", ""), message.get("params") or {}
        try:
            result = self.handle(method, params)
        except Unpaired as exc:
            return {"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32001, "message": str(exc)}}
        except Exception as exc:         # noqa: BLE001 - lỗi một lời gọi không được làm chết máy chủ
            return {"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32603, "message": str(exc)}}
        return {"jsonrpc": "2.0", "id": message["id"], "result": result}

    def handle(self, method, params):
        if method == "initialize":
            self.client = ((params.get("clientInfo") or {}).get("name") or "").strip() or "(không tên)"
            return {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO}
        if method == "tools/list":
            return {"tools": doctools.declarations()}
        if method == "tools/call":
            return self.call_tool(params)
        if method == "ping":
            return {}
        raise RuntimeError(f"máy chủ chưa hỗ trợ {method!r}")

    def call_tool(self, params):
        if not paired(self.client, self.clients_file):
            remember_pending(self.client, self.clients_file)
            raise Unpaired(f"“{self.client}” chưa được phép điều khiển 1xVnOffice. "
                           "Mở 1xVnOffice, vào Tiếng Việt ▸ Công cụ AI (MCP) để cho phép.")
        if self.backend is None:
            return doctools.result("Chưa nối được vào phiên 1xVnOffice nào đang chạy. "
                                   "Hãy mở 1xVnOffice rồi thử lại.", is_error=True)
        return doctools.call(self.backend, params.get("name", ""), params.get("arguments") or {})


def connect(pipe):
    """Lớp UNO chạm vào tài liệu, hoặc None nếu không nối được phiên nào."""
    try:
        from bridge import OfficeBackend       # noqa: PLC0415 - chỉ cần khi chạy thật
        return OfficeBackend(pipe)
    except Exception:                          # noqa: BLE001 - không có office thì chạy ở chế độ rỗng
        return None


def main(argv=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    parser = argparse.ArgumentParser(description="MCP server của 1xVnOffice (stdio)")
    parser.add_argument("--pipe", default=os.environ.get("ONEX_MCP_PIPE", "1xvnoffice"),
                        help="tên UNO pipe của phiên 1xVnOffice đang chạy")
    args = parser.parse_args(argv)
    Server(backend=connect(args.pipe)).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
