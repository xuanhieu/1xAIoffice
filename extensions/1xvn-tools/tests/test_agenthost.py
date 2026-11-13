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
        }
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
