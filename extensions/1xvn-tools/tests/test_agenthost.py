# SPDX-License-Identifier: MPL-2.0
"""Kiểm Agent Host bằng một máy chủ HTTP giả chạy trên máy: không gọi ra Internet, không cần khoá thật."""
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

os.environ.setdefault("ONEX_AI_RETRY_SLEEP", "0")   # không chờ thật khi kiểm thử
HOST_PY = Path(__file__).resolve().parent.parent / "agenthost" / "host.py"
sys.path.insert(0, str(HOST_PY.parent))
import host  # noqa: E402

ANSWER = "Văn bản này là một tờ trình."
SEEN = []          # các yêu cầu máy chủ giả nhận được
BEHAVIOUR = {"status": 200, "shape": "openai"}


class FakeProvider(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or "{}")
        SEEN.append({"path": self.path, "headers": dict(self.headers), "body": body})
        status = BEHAVIOUR["status"]
        bodies = {
            "openai": {"choices": [{"message": {"content": ANSWER}}],
                       "usage": {"prompt_tokens": 12, "completion_tokens": 7}},
            "anthropic": {"content": [{"type": "text", "text": ANSWER}],
                          "usage": {"input_tokens": 12, "output_tokens": 7}},
            "gemini": {"candidates": [{"content": {"parts": [{"text": ANSWER}]}}],
                       "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 7}},
            "broken": {"khong": "dung dang"},
            "tool_then_text": None,      # đặt riêng bên dưới
            "always_tool": None,
        }
        if BEHAVIOUR["shape"] in ("tool_then_text", "always_tool"):
            first = BEHAVIOUR["shape"] == "always_tool" or len(SEEN) == 1   # SEEN đã có yêu cầu đang xử lý
            bodies[BEHAVIOUR["shape"]] = (
                {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "goi-1", "type": "function",
                     "function": {"name": "tra_cuu_van_ban", "arguments": "{\"so_hieu\": \"30/2020\"}"}}]}}]}
                if first else
                {"choices": [{"message": {"content": ANSWER}}], "usage": {"prompt_tokens": 12, "completion_tokens": 7}})
        payload = json.dumps(bodies[BEHAVIOUR["shape"]] if status < 400 else {"error": "hong"}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class HostTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeProvider)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/v1"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        SEEN.clear()
        BEHAVIOUR.update({"status": 200, "shape": "openai"})


class RequestShapeTests(unittest.TestCase):
    def test_openai_and_ollama(self):
        url, headers, body = host.build_request({"type": "openai"}, "gpt-x", [{"role": "user", "content": "xin chào"}],
                                                100, "sk-test")
        self.assertTrue(url.endswith("/chat/completions"))
        self.assertEqual(headers["Authorization"], "Bearer sk-test")
        self.assertEqual(body["max_tokens"], 100)
        url, headers, _ = host.build_request({"type": "ollama"}, "qwen3", [{"role": "user", "content": "a"}], 10, "")
        self.assertIn("11434", url)
        self.assertNotIn("Authorization", headers)      # máy chủ cục bộ không cần khoá

    def test_anthropic_separates_the_system_message(self):
        messages = [{"role": "system", "content": "Bạn là trợ lý."}, {"role": "user", "content": "xin chào"}]
        url, headers, body = host.build_request({"type": "anthropic"}, "claude", messages, 50, "sk-ant")
        self.assertTrue(url.endswith("/messages"))
        self.assertEqual(headers["x-api-key"], "sk-ant")
        self.assertEqual(body["system"], "Bạn là trợ lý.")
        self.assertEqual([m["role"] for m in body["messages"]], ["user"])

    def test_gemini_shape(self):
        url, headers, body = host.build_request({"type": "gemini"}, "gemini-x",
                                                [{"role": "user", "content": "xin chào"}], 50, "k")
        self.assertIn("gemini-x:generateContent", url)
        self.assertEqual(headers["x-goog-api-key"], "k")
        self.assertEqual(body["contents"][0]["parts"][0]["text"], "xin chào")

    def test_unknown_type(self):
        with self.assertRaises(ValueError):
            host.build_request({"type": "khong-biet"}, "m", [], 10, "")

    def test_custom_base_url_is_used(self):
        url, _, _ = host.build_request({"type": "openai", "base_url": "https://ai.coquan.gov.vn/v1/"},
                                       "vn-llm", [], 10, "k")
        self.assertEqual(url, "https://ai.coquan.gov.vn/v1/chat/completions")


class AnswerTests(unittest.TestCase):
    def test_each_shape(self):
        cases = {
            "openai": {"choices": [{"message": {"content": "xin chào"}}], "usage": {"prompt_tokens": 3}},
            "anthropic": {"content": [{"type": "text", "text": "xin chào"}], "usage": {"input_tokens": 3}},
            "gemini": {"candidates": [{"content": {"parts": [{"text": "xin chào"}]}}]},
        }
        for kind, data in cases.items():
            with self.subTest(kind=kind):
                text, usage = host.parse_answer(kind, data)
                self.assertEqual(text, "xin chào")
                self.assertIsInstance(usage, dict)

    def test_unreadable_answer(self):
        self.assertEqual(host.parse_answer("openai", {"khong": "dung"})[0], None)
        self.assertEqual(host.parse_answer("anthropic", {"content": []})[0], None)


class EndToEndTests(HostTestCase):
    def ask(self, kind, **extra):
        provider = {"type": kind, "base_url": self.base, **extra}
        return host.ask({"action": "ask", "provider": provider, "model": "m",
                         "messages": [{"role": "user", "content": "Đây là văn bản gì?"}], "timeout": 5})

    def test_openai_round_trip(self):
        out = self.ask("openai")
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["text"], ANSWER)
        self.assertEqual(out["usage"], {"input": 12, "output": 7})
        self.assertEqual(SEEN[0]["path"], "/v1/chat/completions")

    def test_anthropic_round_trip(self):
        BEHAVIOUR["shape"] = "anthropic"
        out = self.ask("anthropic")
        self.assertEqual(out["text"], ANSWER)
        self.assertEqual(SEEN[0]["path"], "/v1/messages")

    def test_gemini_round_trip(self):
        BEHAVIOUR["shape"] = "gemini"
        out = self.ask("gemini")
        self.assertEqual(out["text"], ANSWER)

    def test_errors_are_explained_in_vietnamese(self):
        for status, code, word in ((401, "auth", "Khoá API"), (429, "quota", "hạn mức"), (500, "server", "lỗi")):
            with self.subTest(status=status):
                BEHAVIOUR["status"] = status
                out = self.ask("openai")
                self.assertFalse(out["ok"])
                self.assertEqual(out["code"], code)
                self.assertIn(word, out["error"])

    def test_unreadable_answer_is_reported(self):
        BEHAVIOUR["shape"] = "broken"
        out = self.ask("openai")
        self.assertEqual(out["code"], "answer")

    def test_missing_secret_is_reported_before_any_call(self):
        out = host.ask({"action": "ask", "provider": {"type": "anthropic", "secret_ref": "khong-co-that"},
                        "model": "m", "messages": []})
        self.assertEqual(out["code"], "secret")
        self.assertEqual(SEEN, [])

    def test_runs_as_a_separate_process(self):
        request = {"action": "ask", "provider": {"type": "openai", "base_url": self.base},
                   "model": "m", "messages": [{"role": "user", "content": "chào"}], "timeout": 5}
        done = subprocess.run([sys.executable, "-I", str(HOST_PY)], input=json.dumps(request),
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["text"], ANSWER)

    def test_bad_input_to_the_process(self):
        done = subprocess.run([sys.executable, "-I", str(HOST_PY)], input="{khong phai json",
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(json.loads(done.stdout)["code"], "config")


if __name__ == "__main__":
    unittest.main()


class ToolLoopTests(HostTestCase):
    """Vòng gọi công cụ: mô hình xin dùng công cụ MCP, host chạy nó rồi đưa kết quả lại cho mô hình."""

    FAKE_MCP = str(Path(__file__).resolve().parent / "fakes" / "mcp_server.py")

    def tool(self, name="tra_cuu_van_ban", mode="ok"):
        return {"name": name, "description": "Tra cứu văn bản.", "schema": {"type": "object", "properties": {}},
                "server": {"command": sys.executable, "args": [self.FAKE_MCP], "env": {"FAKE_MCP_MODE": mode}}}

    def ask_with_tools(self, tools, **extra):
        provider = {"type": "openai", "base_url": self.base}
        return host.ask({"action": "ask", "provider": provider, "model": "m",
                         "messages": [{"role": "user", "content": "Nghị định 30 còn hiệu lực không?"}],
                         "tools": tools, "timeout": 10, **extra})

    def test_tools_are_declared_to_the_model(self):
        BEHAVIOUR["shape"] = "openai"
        self.ask_with_tools([self.tool()])
        declared = SEEN[0]["body"]["tools"]
        self.assertEqual(declared[0]["function"]["name"], "tra_cuu_van_ban")

    def test_no_tools_means_no_tools_field(self):
        self.ask_with_tools([])
        self.assertNotIn("tools", SEEN[0]["body"])

    def test_model_calls_a_tool_and_gets_the_result_back(self):
        BEHAVIOUR["shape"] = "tool_then_text"
        out = self.ask_with_tools([self.tool()])
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["steps"], [{"tool": "tra_cuu_van_ban", "ok": True}])
        # Lượt thứ hai phải mang kết quả công cụ trở lại cho mô hình.
        second = _json_dumps(SEEN[1]["body"])
        self.assertIn("còn hiệu lực", second)
        self.assertEqual(out["text"], ANSWER)

    def test_tool_loop_works_when_host_runs_as_its_own_isolated_process(self):
        """Cách app gọi thật: `python -I host.py`. Chế độ -I bỏ thư mục của script khỏi sys.path, nên nếu host.py
        không tự thêm lại thì `import mcpclient` hỏng và vòng gọi công cụ chết ngay ở bước đầu."""
        import subprocess
        BEHAVIOUR["shape"] = "tool_then_text"
        request = {"action": "ask", "provider": {"type": "openai", "base_url": self.base}, "model": "m",
                   "messages": [{"role": "user", "content": "Nghị định 30 còn hiệu lực không?"}],
                   "tools": [self.tool()], "timeout": 10}
        done = subprocess.run([sys.executable, "-I", str(Path(host.__file__).resolve())],
                              input=json.dumps(request), capture_output=True, text=True, timeout=60)
        self.assertEqual(done.stderr, "")
        out = json.loads(done.stdout or "{}")
        self.assertTrue(out.get("ok"), done.stdout + done.stderr)
        self.assertEqual(out.get("steps"), [{"tool": "tra_cuu_van_ban", "ok": True}])
        self.assertEqual(out.get("text"), ANSWER)

    def test_tool_result_is_data_even_when_it_contains_an_order(self):
        BEHAVIOUR["shape"] = "tool_then_text"
        out = self.ask_with_tools([self.tool()])
        second = _json_dumps(SEEN[1]["body"])
        self.assertIn("xoá tài liệu", second)      # câu ra lệnh chỉ nằm trong nội dung gửi cho mô hình
        self.assertEqual(out["steps"][0]["ok"], True)

    def test_tool_the_user_did_not_allow_is_refused(self):
        BEHAVIOUR["shape"] = "tool_then_text"
        out = self.ask_with_tools([])              # mô hình đòi công cụ nhưng danh sách cho phép rỗng
        self.assertTrue(out["ok"])
        self.assertEqual(out["steps"], [{"tool": "tra_cuu_van_ban", "ok": False}])
        self.assertIn("chưa được cho phép", _json_dumps(SEEN[1]["body"]))

    def test_broken_mcp_server_does_not_break_the_answer(self):
        BEHAVIOUR["shape"] = "tool_then_text"
        out = self.ask_with_tools([self.tool(mode="crash")])
        self.assertTrue(out["ok"])
        self.assertEqual(out["steps"][0]["ok"], False)

    def test_endless_tool_loop_is_stopped(self):
        BEHAVIOUR["shape"] = "always_tool"
        out = self.ask_with_tools([self.tool()])
        self.assertFalse(out["ok"])
        self.assertEqual(out["code"], "tool_steps")


def _json_dumps(value):
    return json.dumps(value, ensure_ascii=False)
