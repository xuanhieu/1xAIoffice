# SPDX-License-Identifier: MPL-2.0
"""MCP client tối giản qua stdio, chỉ dùng thư viện chuẩn.

MCP (Model Context Protocol) là JSON-RPC 2.0 chạy trên stdin/stdout của một tiến trình con. Ở đây tự viết phần đủ
dùng — initialize, tools/list, tools/call — thay vì vendor SDK chính thức, vì thêm phụ thuộc phải tải gói về kho và
chủ dự án chưa duyệt (xem plans/reports/buildnotes-261114-0051-ai-platform-mcp.md).

Hai nguyên tắc an toàn, theo ai-platform-design.md mục 7:

1. **Kết quả của công cụ là DỮ LIỆU, không phải lệnh.** Hàm ở đây chỉ trả chữ về cho người gọi; không có đường nào
   để một máy chủ MCP bảo 1xVnOffice chạy thêm việc gì. Chống prompt injection nằm ở chỗ đó.
2. **Không công cụ nào chạy khi chưa được cho phép.** Việc hỏi quyền nằm ở lớp trên (permissions.py); client này
   chỉ gọi khi đã được bảo là gọi.

Ngoài ra client tự bảo vệ trước máy chủ MCP cư xử tệ: hạn giờ cho từng lượt, cắt kết quả quá lớn, và luôn tắt tiến
trình con khi xong.
"""
import json
import os
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "1xVnOffice", "version": "0.1.0"}
MAX_RESULT_CHARS = 20000      # chống máy chủ trả kết quả khổng lồ làm tốn token của người dùng
DEFAULT_TIMEOUT = 30


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import mcphttp  # noqa: E402


class McpError(RuntimeError):
    """Máy chủ MCP lỗi, trả sai giao thức, hoặc quá giờ."""


def _clip(text):
    if len(text) <= MAX_RESULT_CHARS:
        return text, False
    return text[:MAX_RESULT_CHARS] + "\n…(kết quả đã bị cắt bớt)", True


class StdioServer:
    """Một máy chủ MCP chạy như tiến trình con, nói JSON-RPC qua stdin/stdout."""

    def __init__(self, command, args=(), env=None, cwd=None, timeout=DEFAULT_TIMEOUT):
        self.command, self.args = command, list(args)
        self.env, self.cwd, self.timeout = env or {}, cwd, timeout
        self.process = None
        self._next_id = 0
        self._lock = threading.Lock()
        self._dead = False

    # --- vòng đời ---
    def start(self):
        environ = dict(os.environ)
        environ.update(self.env)
        try:
            self.process = subprocess.Popen([self.command] + self.args, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                            text=True, encoding="utf-8", bufsize=1,
                                            env=environ, cwd=self.cwd)
        except OSError as exc:
            raise McpError(f"không chạy được máy chủ MCP {self.command!r}: {exc}") from None
        info = self.request("initialize", {"protocolVersion": PROTOCOL_VERSION,
                                           "capabilities": {}, "clientInfo": CLIENT_INFO})
        self.notify("notifications/initialized")
        return info

    def stop(self):
        if self.process is None:
            return
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        self.process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        return False

    # --- giao thức ---
    def _send(self, payload):
        if self._dead:
            raise McpError("kết nối MCP đã hỏng ở lượt trước, hãy chạy lại máy chủ")
        if self.process is None or self.process.poll() is not None:
            raise McpError("máy chủ MCP đã dừng")
        try:
            self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise McpError(f"mất kết nối tới máy chủ MCP: {exc}") from None

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def request(self, method, params=None):
        with self._lock:
            self._next_id += 1
            message_id = self._next_id
            self._send({"jsonrpc": "2.0", "id": message_id, "method": method, "params": params or {}})
            return self._await(message_id)

    def _await(self, message_id):
        """Đọc tới khi gặp trả lời đúng id. Thông báo và yêu cầu ngược từ máy chủ đều bị bỏ qua."""
        result = {}
        error = {}
        done = threading.Event()

        def reader():
            try:
                while True:
                    line = (self.process.stdout.readline() or "").strip()
                    if not line:
                        if self.process.poll() is not None:
                            break          # máy chủ đã thoát
                        continue
                    try:
                        message = json.loads(line)
                    except ValueError:
                        continue          # dòng rác (máy chủ in log ra stdout) thì bỏ qua
                    if message.get("id") != message_id:
                        continue
                    if "error" in message:
                        error.update(message["error"] if isinstance(message["error"], dict) else {"message": str(message["error"])})
                    else:
                        result.update({"value": message.get("result")})
                    break
            finally:
                done.set()

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        if not done.wait(self.timeout):
            self._dead = True              # luồng đọc còn kẹt, không dùng lại kết nối này nữa
            raise McpError(f"máy chủ MCP không trả lời trong {self.timeout} giây")
        if error:
            raise McpError(f"máy chủ MCP báo lỗi: {error.get('message', error)}")
        if "value" not in result:
            raise McpError("máy chủ MCP đóng kết nối trước khi trả lời")
        return result["value"]

    # --- việc dùng thật ---
    def list_tools(self):
        """[{name, description, schema}] — mô tả do máy chủ khai, dùng để hiện cho người dùng xem trước khi cho phép."""
        data = self.request("tools/list")
        out = []
        for tool in (data or {}).get("tools", []):
            out.append({"name": tool.get("name", ""),
                        "description": " ".join((tool.get("description") or "").split())[:400],
                        "schema": tool.get("inputSchema") or {}})
        return [tool for tool in out if tool["name"]]

    def call_tool(self, name, arguments=None):
        """(chữ kết quả, có bị cắt không). Kết quả là DỮ LIỆU để đưa lại cho mô hình, không phải lệnh để chạy."""
        data = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        parts = []
        for block in (data or {}).get("content", []):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            else:
                parts.append(f"[{block.get('type', 'nội dung')} không phải chữ, đã bỏ qua]")
        text = "\n".join(parts).strip() or "(công cụ không trả nội dung nào)"
        if (data or {}).get("isError"):
            text = "Công cụ báo lỗi: " + text
        return _clip(text)


class HttpServer(StdioServer):
    """Máy chủ MCP ở xa, nối qua HTTP (chuẩn "Streamable HTTP").

    Cùng giao diện với StdioServer (list_tools, call_tool, dùng được trong `with`), nên phần gọi công cụ ở trên
    không cần biết máy chủ nằm ở đâu. Chỉ khác cách gửi: mỗi lời gọi là một POST, và câu trả lời có thể là một
    khối JSON hoặc một chuỗi sự kiện.

    Thẻ đăng nhập lấy từ kho bí mật của hệ điều hành ngay trước mỗi lần gọi; lớp này không giữ thẻ lâu và không
    bao giờ ghi thẻ ra đâu.
    """

    def __init__(self, url, token="", timeout=DEFAULT_TIMEOUT, session_id=""):
        self.url = url
        self.token = token
        self.timeout = timeout
        self.session_id = session_id
        self.next_id = 0
        self.started = False

    # StdioServer mở tiến trình con; ở đây không có gì để mở.
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        return None

    def _headers(self):
        headers = {"Content-Type": "application/json", "Accept": mcphttp.ACCEPT,
                   "MCP-Protocol-Version": mcphttp.PROTOCOL_VERSION, "User-Agent": mcphttp.USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _post(self, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout,
                                        context=ssl.create_default_context()) as reply:
                session = reply.headers.get("Mcp-Session-Id")
                if session:
                    self.session_id = session
                return reply.status, reply.headers.get("Content-Type", ""), \
                    reply.read().decode("utf-8", "replace"), reply.headers.get("WWW-Authenticate", "")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get("Content-Type", ""), exc.read().decode("utf-8", "replace"), \
                exc.headers.get("WWW-Authenticate", "")
        except urllib.error.URLError as exc:
            raise McpError(f"không nối được tới máy chủ MCP: {exc.reason}") from None

    def _ensure_started(self):
        if self.started:
            return
        self.next_id += 1
        status, kind, raw, challenge = self._post(mcphttp.request_body(
            "initialize", {"protocolVersion": mcphttp.PROTOCOL_VERSION, "capabilities": {},
                           "clientInfo": {"name": "1xVnOffice", "version": "0.1"}}, self.next_id))
        if status == 401:
            raise Unauthorized(challenge, self.url)
        if status >= 400:
            raise McpError(f"máy chủ MCP trả lỗi {status}: {raw[:200]}")
        mcphttp.result_or_raise(mcphttp.parse_reply(kind, raw))
        # Thông báo "đã xong phần bắt tay"; không có id vì không chờ trả lời.
        self._post(mcphttp.notification_body("notifications/initialized"))
        self.started = True

    def request(self, method, params=None):
        self._ensure_started()
        self.next_id += 1
        status, kind, raw, challenge = self._post(mcphttp.request_body(method, params, self.next_id))
        if status == 401:
            raise Unauthorized(challenge, self.url)
        if status >= 400:
            raise McpError(f"máy chủ MCP trả lỗi {status}: {raw[:200]}")
        return mcphttp.result_or_raise(mcphttp.parse_reply(kind, raw))


class Unauthorized(McpError):
    """Máy chủ đòi đăng nhập. Mang theo lời thách thức để lớp trên biết hỏi metadata ở đâu."""

    def __init__(self, challenge, url):
        self.challenge = mcphttp.parse_challenge(challenge)
        self.url = url
        super().__init__(f"máy chủ MCP {url} đòi đăng nhập")


def from_claude_desktop(config):
    """Đọc cấu hình kiểu claude_desktop_config.json thành danh sách máy chủ.

    Nhờ vậy người dùng chép thẳng cấu hình sẵn có vào 1xVnOffice. Nhận cả máy chủ chạy bằng lệnh (stdio) lẫn máy
    chủ ở xa khai bằng `url` (HTTP).
    """
    out = []
    for name, entry in (config.get("mcpServers") or {}).items():
        url = entry.get("url")
        if url and (entry.get("type") or "").lower() in ("http", "streamable-http", "sse", ""):
            out.append({"id": name, "url": url, "transport": "http"})
            continue
        command = entry.get("command")
        if not command:
            continue              # bản HTTP/SSE chưa hỗ trợ ở mốc này
        out.append({"id": name, "command": command, "args": list(entry.get("args") or []),
                    "env": dict(entry.get("env") or {}), "cwd": entry.get("cwd") or None})
    return out
