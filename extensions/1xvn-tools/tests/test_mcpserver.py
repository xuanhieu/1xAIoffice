# SPDX-License-Identifier: MPL-2.0
"""1xVnOffice làm máy chủ MCP: giao thức, ghép đôi, và cư xử khi không có phiên nào đang chạy."""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcpserver"))
sys.path.insert(0, str(ROOT / "pythonpath"))
import server  # noqa: E402


class FakeBackend:
    def __init__(self):
        self.calls = []

    def docs_list_open(self):
        self.calls.append("docs.list_open")
        return "d1: Tờ trình (văn bản, chưa lưu)"


def talk(messages, backend=None, clients_file=None):
    """Gửi một loạt tin nhắn vào máy chủ, trả về danh sách trả lời."""
    lines = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in messages)
    out = io.StringIO()
    server.Server(backend=backend, clients_file=clients_file,
                  stdin=io.StringIO(lines), stdout=out).run()
    return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]


def hello(name="Claude Desktop"):
    return {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": server.PROTOCOL_VERSION, "clientInfo": {"name": name}}}


class ClientsFile(unittest.TestCase):
    def allow(self, *names):
        path = Path(self.dir.name) / "mcp_clients.json"
        path.write_text(json.dumps({"clients": {n: "allow" for n in names}}), encoding="utf-8")
        return str(path)

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.missing = str(Path(self.dir.name) / "khong-co.json")


class ProtocolTests(ClientsFile):
    def test_initialize_answers_with_the_protocol_version(self):
        answer = talk([hello()], clients_file=self.missing)[0]
        self.assertEqual(answer["result"]["protocolVersion"], server.PROTOCOL_VERSION)
        self.assertEqual(answer["result"]["serverInfo"]["name"], "1xVnOffice")

    def test_tools_list_works_before_pairing(self):
        # Client chưa được phép vẫn xem được có những công cụ gì; chỉ không gọi được.
        answers = talk([hello(), {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}], clients_file=self.missing)
        names = [t["name"] for t in answers[1]["result"]["tools"]]
        self.assertIn("docs.list_open", names)

    def test_notifications_get_no_answer(self):
        answers = talk([{"jsonrpc": "2.0", "method": "notifications/initialized"}], clients_file=self.missing)
        self.assertEqual(answers, [])

    def test_garbage_lines_do_not_kill_the_server(self):
        lines = "khong-phai-json\n" + json.dumps(hello()) + "\n"
        out = io.StringIO()
        server.Server(clients_file=self.missing, stdin=io.StringIO(lines), stdout=out).run()
        self.assertEqual(len(out.getvalue().strip().splitlines()), 1)

    def test_unknown_method_is_an_error_not_a_crash(self):
        answers = talk([hello(), {"jsonrpc": "2.0", "id": 2, "method": "resources/list"}], clients_file=self.missing)
        self.assertIn("error", answers[1])


class PairingTests(ClientsFile):
    def call(self):
        return {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "docs.list_open", "arguments": {}}}

    def test_an_unpaired_client_cannot_call_a_tool(self):
        backend = FakeBackend()
        answers = talk([hello(), self.call()], backend=backend, clients_file=self.missing)
        self.assertIn("error", answers[1])
        self.assertEqual(backend.calls, [])           # công cụ KHÔNG được chạy

    def test_a_paired_client_can(self):
        backend = FakeBackend()
        answers = talk([hello(), self.call()], backend=backend, clients_file=self.allow("Claude Desktop"))
        self.assertIn("Tờ trình", answers[1]["result"]["content"][0]["text"])
        self.assertEqual(backend.calls, ["docs.list_open"])

    def test_pairing_is_per_client_name(self):
        backend = FakeBackend()
        answers = talk([hello("Trợ lý lạ"), self.call()], backend=backend,
                       clients_file=self.allow("Claude Desktop"))
        self.assertIn("error", answers[1])
        self.assertEqual(backend.calls, [])

    def test_a_broken_clients_file_means_not_paired(self):
        path = Path(self.dir.name) / "hong.json"
        path.write_text("{khong phai json", encoding="utf-8")
        answers = talk([hello(), self.call()], backend=FakeBackend(), clients_file=str(path))
        self.assertIn("error", answers[1])

    def test_a_client_without_a_name_is_not_paired_by_accident(self):
        answers = talk([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, self.call()],
                       backend=FakeBackend(), clients_file=self.allow(""))
        self.assertIn("error", answers[1])


class NoSessionTests(ClientsFile):
    def test_without_a_running_office_the_client_is_told_so(self):
        answers = talk([hello(), {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": "docs.list_open", "arguments": {}}}],
                       backend=None, clients_file=self.allow("Claude Desktop"))
        result = answers[1]["result"]
        self.assertTrue(result["isError"])
        self.assertIn("1xVnOffice", result["content"][0]["text"])


class ProcessTests(ClientsFile):
    def test_the_server_runs_as_its_own_process_and_speaks_mcp(self):
        """Đúng cách Claude Desktop chạy nó: một tiến trình con, nói JSON-RPC qua stdio."""
        lines = "".join(json.dumps(m, ensure_ascii=False) + "\n"
                        for m in [hello(), {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
        done = subprocess.run([sys.executable, str(ROOT / "mcpserver" / "server.py"), "--pipe", "khong-co-phien"],
                              input=lines, capture_output=True, text=True, timeout=60,
                              env={"PATH": "/usr/bin:/bin", "ONEX_MCP_CLIENTS_PATH": self.missing})
        self.assertEqual(done.returncode, 0, done.stderr)
        answers = [json.loads(line) for line in done.stdout.splitlines() if line.strip()]
        self.assertEqual(answers[0]["result"]["serverInfo"]["name"], "1xVnOffice")
        self.assertIn("doc.read", [t["name"] for t in answers[1]["result"]["tools"]])


if __name__ == "__main__":
    unittest.main()
