# SPDX-License-Identifier: MPL-2.0
"""Kiểm MCP client bằng một máy chủ MCP giả chạy ngay trên máy, kể cả các máy chủ cư xử tệ."""
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "agenthost"))
import mcpclient  # noqa: E402

FAKE = str(HERE / "fakes" / "mcp_server.py")


def server(mode="ok", timeout=10):
    return mcpclient.StdioServer(sys.executable, [FAKE], env={"FAKE_MCP_MODE": mode}, timeout=timeout)


class HandshakeTests(unittest.TestCase):
    def test_initialize_and_list_tools(self):
        with server() as mcp:
            tools = mcp.list_tools()
        self.assertEqual([t["name"] for t in tools], ["tra_cuu_van_ban", "doi_don_vi"])
        self.assertIn("Tra cứu", tools[0]["description"])
        self.assertEqual(tools[0]["schema"]["required"], ["so_hieu"])

    def test_server_info_comes_back(self):
        mcp = server()
        try:
            info = mcp.start()
            self.assertEqual(info["serverInfo"]["name"], "may-chu-gia")
        finally:
            mcp.stop()

    def test_log_lines_on_stdout_are_ignored(self):
        with server("garbage") as mcp:
            self.assertTrue(mcp.list_tools())

    def test_missing_command_is_reported(self):
        with self.assertRaises(mcpclient.McpError):
            mcpclient.StdioServer("/khong/co/lenh/nay").start()


class CallTests(unittest.TestCase):
    def test_calls_a_tool_and_passes_arguments(self):
        with server() as mcp:
            text, cut = mcp.call_tool("tra_cuu_van_ban", {"so_hieu": "30/2020/NĐ-CP"})
        self.assertIn("30/2020/NĐ-CP", text)
        self.assertFalse(cut)

    def test_result_is_data_not_an_instruction(self):
        """Kết quả chứa câu ra lệnh vẫn chỉ là chữ trả về; client không có đường nào để chạy nó."""
        with server() as mcp:
            text, _ = mcp.call_tool("tra_cuu_van_ban", {"so_hieu": "1"})
        self.assertIn("xoá tài liệu", text)      # chữ được giữ nguyên để mô hình đọc
        self.assertIsInstance(text, str)         # và chỉ là chữ, không phải việc để làm

    def test_huge_result_is_clipped(self):
        with server("huge") as mcp:
            text, cut = mcp.call_tool("doi_don_vi", {})
        self.assertTrue(cut)
        self.assertLessEqual(len(text), mcpclient.MAX_RESULT_CHARS + 50)

    def test_tool_error_is_marked(self):
        with server("error") as mcp:
            text, _ = mcp.call_tool("tra_cuu_van_ban", {"so_hieu": "x"})
        self.assertTrue(text.startswith("Công cụ báo lỗi:"))

    def test_unknown_method_raises(self):
        with server() as mcp:
            with self.assertRaises(mcpclient.McpError):
                mcp.request("khong/co/phuong/thuc")


class BadBehaviourTests(unittest.TestCase):
    def test_slow_server_times_out_and_connection_is_not_reused(self):
        mcp = mcpclient.StdioServer(sys.executable, [FAKE], env={"FAKE_MCP_MODE": "slow"}, timeout=1)
        try:
            with self.assertRaises(mcpclient.McpError) as caught:
                mcp.start()
            self.assertIn("không trả lời", str(caught.exception))
            with self.assertRaises(mcpclient.McpError):
                mcp.request("tools/list")        # kết nối đã bị đánh dấu hỏng
        finally:
            mcp.stop()

    def test_server_that_dies_mid_call(self):
        with server("crash") as mcp:
            with self.assertRaises(mcpclient.McpError):
                mcp.call_tool("tra_cuu_van_ban", {"so_hieu": "1"})


class ImportTests(unittest.TestCase):
    def test_reads_claude_desktop_config(self):
        config = {"mcpServers": {"giay-to": {"command": "python3", "args": ["x.py"], "env": {"A": "1"}},
                                 "qua-http": {"url": "https://vi.du/mcp"}}}
        servers = mcpclient.from_claude_desktop(config)
        self.assertEqual([s["id"] for s in servers], ["giay-to", "qua-http"])
        self.assertEqual(servers[0]["args"], ["x.py"])
        self.assertEqual(servers[0]["env"], {"A": "1"})
        self.assertEqual(servers[1], {"id": "qua-http", "url": "https://vi.du/mcp", "transport": "http"})

    def test_a_remote_server_is_recognised_however_it_is_labelled(self):
        """Cấu hình sẵn có của người dùng ghi type là http, streamable-http, sse, hoặc không ghi gì."""
        for kind in ("http", "streamable-http", "sse", ""):
            with self.subTest(kind=kind):
                entry = {"url": "https://vi.du/mcp"}
                if kind:
                    entry["type"] = kind
                servers = mcpclient.from_claude_desktop({"mcpServers": {"xa": entry}})
                self.assertEqual(servers[0]["transport"], "http")

    def test_an_entry_with_neither_command_nor_url_is_skipped(self):
        self.assertEqual(mcpclient.from_claude_desktop({"mcpServers": {"rong": {}}}), [])

    def test_empty_config(self):
        self.assertEqual(mcpclient.from_claude_desktop({}), [])


if __name__ == "__main__":
    unittest.main()


class HttpServerTests(unittest.TestCase):
    """Lớp nối HTTP, nói chuyện với một máy chủ MCP giả chạy trên 127.0.0.1."""

    class Fake(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
            self.server.seen.append((body.get("method"), self.headers.get("Authorization"),
                                     self.headers.get("User-Agent")))
            if self.server.demand_login:
                self.send_response(401)
                self.send_header("WWW-Authenticate",
                                 'Bearer resource_metadata="https://may.chu/.well-known/'
                                 'oauth-protected-resource/mcp", scope="mcp:tools"')
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if "id" not in body:                       # thông báo thì không trả lời
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            results = {"initialize": {"protocolVersion": "2025-06-18", "capabilities": {},
                                      "serverInfo": {"name": "gia", "version": "1"}},
                       "tools/list": {"tools": [{"name": "tra_cuu", "description": "Tra cứu.",
                                                 "inputSchema": {"type": "object"}}]},
                       "tools/call": {"content": [{"type": "text", "text": "Kết quả tra cứu."}]}}
            payload = json.dumps({"jsonrpc": "2.0", "id": body["id"],
                                  "result": results.get(body.get("method"), {})}).encode()
            self.send_response(200)
            self.send_header("Content-Type", self.server.reply_type)
            if self.server.reply_type.startswith("text/event-stream"):
                payload = b"data: " + payload + b"\n\n"
            self.send_header("Mcp-Session-Id", "phien-1")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            return

    def start(self, reply_type="application/json", demand_login=False):
        srv = HTTPServer(("127.0.0.1", 0), self.Fake)
        srv.seen, srv.reply_type, srv.demand_login = [], reply_type, demand_login
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return srv, f"http://127.0.0.1:{srv.server_port}/mcp"

    def test_it_lists_and_calls_tools_like_the_stdio_one(self):
        srv, url = self.start()
        with mcpclient.HttpServer(url, token="the") as mcp:
            tools = mcp.list_tools()
            text, cut = mcp.call_tool("tra_cuu", {"so_hieu": "30"})
        self.assertEqual([t["name"] for t in tools], ["tra_cuu"])
        self.assertEqual(text, "Kết quả tra cứu.")
        self.assertFalse(cut)

    def test_it_shakes_hands_before_anything_else(self):
        srv, url = self.start()
        with mcpclient.HttpServer(url) as mcp:
            mcp.list_tools()
        methods = [m for m, _, _ in srv.seen]
        self.assertEqual(methods[:3], ["initialize", "notifications/initialized", "tools/list"])

    def test_it_sends_the_token_and_names_itself(self):
        srv, url = self.start()
        with mcpclient.HttpServer(url, token="the-cua-toi") as mcp:
            mcp.list_tools()
        _, auth, agent = srv.seen[0]
        self.assertEqual(auth, "Bearer the-cua-toi")
        self.assertTrue(agent.startswith("1xVnOffice/"))

    def test_a_server_that_answers_with_an_event_stream_works_too(self):
        srv, url = self.start(reply_type="text/event-stream")
        with mcpclient.HttpServer(url) as mcp:
            self.assertEqual([t["name"] for t in mcp.list_tools()], ["tra_cuu"])

    def test_being_asked_to_sign_in_carries_the_challenge_up(self):
        srv, url = self.start(demand_login=True)
        with self.assertRaises(mcpclient.Unauthorized) as caught:
            mcpclient.HttpServer(url).list_tools()
        self.assertEqual(caught.exception.challenge["scope"], "mcp:tools")
        self.assertEqual(caught.exception.url, url)

    def test_a_server_that_is_not_there_says_so_plainly(self):
        with self.assertRaises(mcpclient.McpError):
            mcpclient.HttpServer("http://127.0.0.1:1/mcp", timeout=2).list_tools()
