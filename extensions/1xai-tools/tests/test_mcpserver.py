# SPDX-License-Identifier: MPL-2.0
"""1xAIoffice làm máy chủ MCP: giao thức, ghép đôi, và cư xử khi không có phiên nào đang chạy."""
import io
import os
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
        self.assertEqual(answer["result"]["serverInfo"]["name"], "1xAIoffice")

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
        answers = talk([hello(), {"jsonrpc": "2.0", "id": 2, "method": "khong/co/phuong/thuc/nay"}],
                       clients_file=self.missing)
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
        self.assertIn("1xAIoffice", result["content"][0]["text"])


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
        self.assertEqual(answers[0]["result"]["serverInfo"]["name"], "1xAIoffice")
        self.assertIn("doc.read", [t["name"] for t in answers[1]["result"]["tools"]])


if __name__ == "__main__":
    unittest.main()


class ResourceAndPromptTests(unittest.TestCase):
    """resources/* và prompts/* của máy chủ MCP, với một backend giả."""

    class FakeBackend:
        def __init__(self):
            self.read = []

        def resources(self):
            return [{"id": "doc1", "title": "Tờ trình", "kind": "doc", "sheets": []},
                    {"id": "doc2", "title": "Sổ lương", "kind": "sheet", "sheets": ["Sheet1"]}]

        def read_resource(self, uri):
            self.read.append(uri)
            return "# Tờ trình" if "doc/" in uri else "ho_ten,luong"

    def server(self, paired_name=None):
        import tempfile
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"clients": {paired_name: "allow"} if paired_name else {}, "pending": {}}, handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        srv = server.Server(backend=self.FakeBackend(), clients_file=handle.name)
        srv.handle("initialize", {"clientInfo": {"name": "Trợ lý Thử"}})
        return srv

    def test_initialize_announces_resources_and_prompts(self):
        srv = self.server()
        caps = srv.handle("initialize", {"clientInfo": {"name": "x"}})["capabilities"]
        self.assertIn("resources", caps)
        self.assertIn("prompts", caps)

    def test_an_unpaired_assistant_may_see_the_list_of_documents(self):
        """Tên tài liệu thì cho xem, như tools/list; nội dung mới phải xin phép."""
        srv = self.server()
        uris = [r["uri"] for r in srv.handle("resources/list", {})["resources"]]
        self.assertEqual(uris, ["1x://doc/doc1", "1x://sheet/doc2/Sheet1"])

    def test_an_unpaired_assistant_cannot_read_a_document(self):
        srv = self.server()
        with self.assertRaises(server.Unpaired):
            srv.handle("resources/read", {"uri": "1x://doc/doc1"})
        self.assertEqual(srv.backend.read, [], "không được chạm vào tài liệu khi chưa được phép")

    def test_a_paired_assistant_reads_markdown_and_csv(self):
        srv = self.server(paired_name="Trợ lý Thử")
        out = srv.handle("resources/read", {"uri": "1x://doc/doc1"})["contents"][0]
        self.assertEqual(out["mimeType"], "text/markdown")
        self.assertEqual(out["text"], "# Tờ trình")
        out = srv.handle("resources/read", {"uri": "1x://sheet/doc2/Sheet1"})["contents"][0]
        self.assertEqual(out["mimeType"], "text/csv")

    def user_skill(self):
        """Một skill do người dùng tự cài, chép từ một skill đi kèm rồi đổi tên."""
        import shutil, tempfile
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home, True)
        dest = home / "skill-cua-toi"
        shutil.copytree(server.BUNDLED_SKILLS / "soan-van-ban-nd30", dest)
        md = dest / "SKILL.md"
        md.write_text(md.read_text(encoding="utf-8").replace("name: soan-van-ban-nd30", "name: skill-cua-toi"),
                      encoding="utf-8")
        os.environ["ONEX_SKILLS_PATH"] = str(home)
        self.addCleanup(os.environ.pop, "ONEX_SKILLS_PATH", None)

    def test_bundled_skills_are_never_offered_to_outside_assistants(self):
        self.user_skill()
        names = [p["name"] for p in self.server().handle("prompts/list", {})["prompts"]]
        self.assertNotIn("soan-van-ban-nd30", names)
        self.assertIn("skill-cua-toi", names)

    def test_even_a_paired_assistant_cannot_pull_a_bundled_skill(self):
        self.user_skill()
        srv = self.server(paired_name="Trợ lý Thử")
        with self.assertRaises(RuntimeError):
            srv.handle("prompts/get", {"name": "soan-van-ban-nd30"})

    def test_an_unpaired_assistant_cannot_read_a_skill_body(self):
        self.user_skill()
        srv = self.server()
        with self.assertRaises(server.Unpaired):
            srv.handle("prompts/get", {"name": "skill-cua-toi"})

    def test_a_paired_assistant_gets_the_user_skill_body_and_its_question(self):
        self.user_skill()
        srv = self.server(paired_name="Trợ lý Thử")
        out = srv.handle("prompts/get", {"name": "skill-cua-toi", "arguments": {"viec": "soạn công văn"}})
        self.assertIn("soạn công văn", out["messages"][0]["content"]["text"])

    def test_asking_for_a_skill_that_does_not_exist_says_so(self):
        srv = self.server(paired_name="Trợ lý Thử")
        with self.assertRaises(RuntimeError):
            srv.handle("prompts/get", {"name": "khong-co-skill-nay"})

    def test_a_bad_resource_address_is_refused(self):
        srv = self.server(paired_name="Trợ lý Thử")
        with self.assertRaises(Exception):
            srv.handle("resources/read", {"uri": "https://example.com"})
