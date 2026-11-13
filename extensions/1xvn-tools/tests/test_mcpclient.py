# SPDX-License-Identifier: MPL-2.0
"""Kiểm MCP client bằng một máy chủ MCP giả chạy ngay trên máy, kể cả các máy chủ cư xử tệ."""
import os
import sys
import unittest
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
        self.assertEqual([s["id"] for s in servers], ["giay-to"])   # bản HTTP chưa hỗ trợ, bỏ qua
        self.assertEqual(servers[0]["args"], ["x.py"])
        self.assertEqual(servers[0]["env"], {"A": "1"})

    def test_empty_config(self):
        self.assertEqual(mcpclient.from_claude_desktop({}), [])


if __name__ == "__main__":
    unittest.main()
