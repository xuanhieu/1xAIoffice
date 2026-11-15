# SPDX-License-Identifier: MPL-2.0
"""Kiểm lớp nối MCP qua HTTP: dò cách đăng nhập, hình dạng yêu cầu, đọc câu trả lời. Không chạm mạng thật."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))

from vn1x import mcphttp


class ChallengeTests(unittest.TestCase):
    REAL = ('Bearer resource_metadata="https://may.chu/.well-known/oauth-protected-resource/mcp", '
            'scope="mcp:tools"')

    def test_it_reads_the_header_a_real_server_sends(self):
        got = mcphttp.parse_challenge(self.REAL)
        self.assertEqual(got["resource_metadata"], "https://may.chu/.well-known/oauth-protected-resource/mcp")
        self.assertEqual(got["scope"], "mcp:tools")

    def test_a_missing_header_is_not_a_crash(self):
        self.assertEqual(mcphttp.parse_challenge(""), {})
        self.assertEqual(mcphttp.parse_challenge(None), {})

    def test_the_address_in_the_header_wins(self):
        urls = mcphttp.metadata_urls("https://may.chu/mcp", mcphttp.parse_challenge(self.REAL))
        self.assertEqual(urls, ["https://may.chu/.well-known/oauth-protected-resource/mcp"])

    def test_without_a_header_the_address_follows_the_rule_in_the_spec(self):
        """`.well-known` đặt TRƯỚC đường dẫn, không nối vào sau — nối sau là hỏi nhầm chỗ."""
        urls = mcphttp.metadata_urls("https://may.chu/mcp")
        self.assertEqual(urls[0], "https://may.chu/.well-known/oauth-protected-resource/mcp")
        self.assertEqual(urls[1], "https://may.chu/.well-known/oauth-protected-resource")


class ConfigTests(unittest.TestCase):
    RESOURCE = {"resource": "https://may.chu/mcp", "authorization_servers": ["https://may.chu"],
                "scopes_supported": ["mcp:tools"]}
    SERVER = {"authorization_endpoint": "https://may.chu/authorize", "token_endpoint": "https://may.chu/token",
              "registration_endpoint": "https://may.chu/register"}

    def test_both_well_known_names_are_tried(self):
        urls = mcphttp.authorization_server_urls(self.RESOURCE)
        self.assertIn("https://may.chu/.well-known/oauth-authorization-server", urls)
        self.assertIn("https://may.chu/.well-known/openid-configuration", urls)

    def test_the_config_carries_what_the_login_needs(self):
        config = mcphttp.oauth_config("https://may.chu/mcp", self.RESOURCE, self.SERVER)
        self.assertEqual(config["authorize_url"], "https://may.chu/authorize")
        self.assertEqual(config["token_url"], "https://may.chu/token")
        self.assertEqual(config["registration_url"], "https://may.chu/register")
        self.assertEqual(config["scopes"], ["mcp:tools"])
        self.assertEqual(config["resource"], "https://may.chu/mcp")

    def test_a_server_without_a_token_endpoint_is_refused(self):
        with self.assertRaises(mcphttp.HttpMcpError):
            mcphttp.oauth_config("https://may.chu/mcp", self.RESOURCE,
                                 {"authorization_endpoint": "https://may.chu/authorize"})

    def test_a_server_that_cannot_self_register_says_nothing_about_it(self):
        config = mcphttp.oauth_config("https://may.chu/mcp", self.RESOURCE,
                                      {k: v for k, v in self.SERVER.items() if k != "registration_endpoint"})
        self.assertNotIn("registration_url", config)

    def test_the_registration_asks_for_a_public_client(self):
        """Ứng dụng chạy trên máy người dùng không giữ nổi bí mật, nên phải đăng ký là client công khai."""
        body = mcphttp.registration_body("1xAIoffice", "http://127.0.0.1:1/callback", ["mcp:tools"])
        self.assertEqual(body["token_endpoint_auth_method"], "none")
        self.assertEqual(body["redirect_uris"], ["http://127.0.0.1:1/callback"])
        self.assertIn("refresh_token", body["grant_types"])


class MessageTests(unittest.TestCase):
    def test_a_notification_carries_no_id(self):
        """Gửi kèm id là bắt máy chủ trả lời một thứ mình không chờ."""
        self.assertNotIn("id", mcphttp.notification_body("notifications/initialized"))
        self.assertIn("id", mcphttp.request_body("tools/list"))

    def test_a_plain_json_reply_is_read(self):
        raw = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"tools": []}})
        self.assertEqual(mcphttp.result_or_raise(mcphttp.parse_reply("application/json", raw)), {"tools": []})

    def test_an_event_stream_reply_is_read_too(self):
        """Chuẩn cho phép máy chủ trả lời bằng chuỗi sự kiện; client phải đọc được cả hai dạng."""
        raw = ("event: message\n"
               'data: {"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"tra_cuu"}]}}\n\n')
        result = mcphttp.result_or_raise(mcphttp.parse_reply("text/event-stream", raw))
        self.assertEqual(result["tools"][0]["name"], "tra_cuu")

    def test_an_error_from_the_server_keeps_its_own_words(self):
        raw = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "chưa hỗ trợ"}})
        with self.assertRaises(mcphttp.HttpMcpError) as caught:
            mcphttp.result_or_raise(mcphttp.parse_reply("application/json", raw))
        self.assertIn("chưa hỗ trợ", str(caught.exception))

    def test_junk_instead_of_json_is_reported_not_swallowed(self):
        with self.assertRaises(mcphttp.HttpMcpError):
            mcphttp.parse_reply("application/json", "<html>lỗi cổng</html>")

    def test_an_event_stream_with_no_result_is_reported(self):
        with self.assertRaises(mcphttp.HttpMcpError):
            mcphttp.parse_reply("text/event-stream", "data: {\"jsonrpc\":\"2.0\"}\n")

    def test_the_user_agent_names_the_product_and_nothing_about_the_person(self):
        """Máy chủ sau Cloudflare trả 403 cho User-Agent mặc định của urllib, nên phải gửi tên sản phẩm."""
        self.assertTrue(mcphttp.USER_AGENT.startswith("1xAIoffice/"))
        self.assertNotIn("@", mcphttp.USER_AGENT)
