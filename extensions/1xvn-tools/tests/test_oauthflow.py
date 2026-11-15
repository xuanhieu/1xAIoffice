# SPDX-License-Identifier: MPL-2.0
"""Kiểm luồng đăng nhập OAuth của Agent Host trước một máy chủ GIẢ chạy trên 127.0.0.1.

Không ra Internet, không chạm Keychain thật (ONEX_OAUTH_STORE_FOR_TEST trỏ kho thẻ sang một tệp tạm).
"""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agenthost"))
sys.path.insert(0, str(ROOT / "pythonpath"))

import oauthflow
from vn1x import oauth


class FakeProvider(BaseHTTPRequestHandler):
    """Máy chủ đăng nhập giả: cấp mã thiết bị, đổi mã lấy thẻ, gia hạn thẻ."""

    def do_POST(self):                                    # noqa: N802
        form = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
        if self.path == "/device":
            return self._send({"device_code": "ma-thiet-bi", "user_code": "ABCD-1234",
                               "verification_uri": "https://dangnhap.vd/nhapma", "interval": 0,
                               "expires_in": 600})
        grant = (form.get("grant_type") or [""])[0]
        if grant == "authorization_code":
            if not form.get("code_verifier"):
                return self._send({"error": "invalid_request", "error_description": "thiếu PKCE"}, 400)
            return self._send({"access_token": "the-truy-cap", "refresh_token": "the-gia-han",
                               "expires_in": 3600, "token_type": "Bearer"})
        if grant == "refresh_token":
            if form.get("refresh_token") != ["the-gia-han"]:
                return self._send({"error": "invalid_grant"}, 400)
            return self._send({"access_token": "the-moi", "expires_in": 3600})     # cố ý KHÔNG gửi lại refresh
        if grant.endswith("device_code"):
            self.server.polls += 1
            if self.server.polls < 2:
                return self._send({"error": "authorization_pending"}, 400)
            return self._send({"access_token": "the-cua-thiet-bi", "refresh_token": "r", "expires_in": 3600})
        return self._send({"error": "unsupported_grant_type"}, 400)

    def _send(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), FakeProvider)
        self.server.polls = 0
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{self.server.server_port}"
        self.config = {"authorize_url": base + "/auth", "token_url": base + "/token",
                       "device_url": base + "/device", "client_id": "1xaioffice-test",
                       "scopes": ["openid"]}
        self.store = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        self.store.write("{}")
        self.store.close()
        os.environ["ONEX_OAUTH_STORE_FOR_TEST"] = self.store.name
        self.addCleanup(os.environ.pop, "ONEX_OAUTH_STORE_FOR_TEST", None)
        self.addCleanup(os.unlink, self.store.name)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def _open_browser(self, url):
        """Thay cho trình duyệt thật: gọi thẳng địa chỉ trả về như nhà cung cấp sẽ làm."""
        query = parse_qs(urlparse(url).query)
        redirect = query["redirect_uri"][0] + f"?code=ma-uy-quyen&state={query['state'][0]}"
        threading.Thread(target=lambda: urllib.request.urlopen(redirect, timeout=5).read(), daemon=True).start()
        return True

    def test_browser_login_stores_the_token_and_reports_without_showing_it(self):
        oauthflow.webbrowser.open = self._open_browser
        state = oauthflow.login_browser(self.config, "test/tai-khoan", timeout=10)
        self.assertNotIn("the-truy-cap", state)
        stored = oauthflow.read_bundle("test/tai-khoan")
        self.assertEqual(stored["access_token"], "the-truy-cap")
        self.assertEqual(stored["refresh_token"], "the-gia-han")

    def test_a_redirect_with_the_wrong_state_is_refused(self):
        def wrong_state(url):
            redirect = parse_qs(urlparse(url).query)["redirect_uri"][0] + "?code=x&state=cua-trang-la"
            threading.Thread(target=lambda: urllib.request.urlopen(redirect, timeout=5).read(),
                             daemon=True).start()
            return True
        oauthflow.webbrowser.open = wrong_state
        with self.assertRaises(oauth.OAuthError):
            oauthflow.login_browser(self.config, "test/tai-khoan", timeout=10)
        self.assertEqual(oauthflow.read_bundle("test/tai-khoan"), {})

    def test_a_browser_that_will_not_open_says_so_instead_of_hanging(self):
        oauthflow.webbrowser.open = lambda url: False
        with self.assertRaises(oauthflow.FlowError) as caught:
            oauthflow.login_browser(self.config, "test/tai-khoan", timeout=2)
        self.assertIn("mã thiết bị", str(caught.exception))

    def test_device_login_waits_for_the_user_then_stores_the_token(self):
        started = oauthflow.device_start(self.config)
        self.assertEqual(started["user_code"], "ABCD-1234")
        state = oauthflow.device_poll(self.config, "test/thiet-bi", started["device_code"],
                                      interval=0, timeout=10)
        self.assertNotIn("the-cua-thiet-bi", state)
        self.assertEqual(self.server.polls, 2, "lượt hỏi đầu phải chờ người dùng đồng ý")
        self.assertEqual(oauthflow.read_bundle("test/thiet-bi")["access_token"], "the-cua-thiet-bi")

    def test_an_expired_token_is_renewed_and_the_refresh_token_is_kept(self):
        ref = "test/gia-han"
        oauthflow.write_bundle(ref, {"access_token": "cu", "refresh_token": "the-gia-han",
                                     "expires_at": time.time() - 10})
        provider = {"id": "x", "auth": "oauth", "secret_ref": ref, "oauth": self.config}
        self.assertEqual(oauthflow.access_token(provider), "the-moi")
        stored = oauthflow.read_bundle(ref)
        self.assertEqual(stored["refresh_token"], "the-gia-han")

    def test_a_token_still_in_date_is_used_as_is(self):
        ref = "test/con-han"
        oauthflow.write_bundle(ref, {"access_token": "dang-dung", "expires_at": time.time() + 3600})
        provider = {"id": "x", "auth": "oauth", "secret_ref": ref, "oauth": self.config}
        self.assertEqual(oauthflow.access_token(provider), "dang-dung")

    def test_not_signed_in_tells_the_user_where_to_sign_in(self):
        provider = {"id": "chua-dang-nhap", "auth": "oauth", "secret_ref": "test/trong",
                    "oauth": self.config}
        with self.assertRaises(oauthflow.FlowError) as caught:
            oauthflow.access_token(provider)
        self.assertIn("Tài khoản AI", str(caught.exception))

    def test_an_expired_token_with_no_way_to_renew_asks_for_a_new_sign_in(self):
        ref = "test/het-han"
        oauthflow.write_bundle(ref, {"access_token": "cu", "expires_at": time.time() - 10})
        provider = {"id": "x", "auth": "oauth", "secret_ref": ref, "oauth": self.config}
        with self.assertRaises(oauthflow.FlowError) as caught:
            oauthflow.access_token(provider)
        self.assertIn("đăng nhập lại", str(caught.exception))

    def test_forgetting_an_account_clears_the_token(self):
        oauthflow.write_bundle("test/quen", {"access_token": "t"})
        oauthflow.forget("test/quen")
        self.assertEqual(oauthflow.read_bundle("test/quen"), {})


if __name__ == "__main__":
    unittest.main()


class ClientSecretTests(unittest.TestCase):
    """Google cấp client secret cho cả ứng dụng Desktop và đòi nó ở bước đổi thẻ, dù đã có PKCE."""

    def setUp(self):
        self.store = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        self.store.write(json.dumps({"1xaioffice/vertex/client_secret": "bi-mat-cua-ung-dung"}))
        self.store.close()
        os.environ["ONEX_SECRET_STORE_FOR_TEST"] = self.store.name
        self.addCleanup(os.environ.pop, "ONEX_SECRET_STORE_FOR_TEST", None)
        self.addCleanup(os.unlink, self.store.name)

    def test_the_secret_is_fetched_from_the_store_at_the_moment_it_is_needed(self):
        config = oauthflow.with_client_secret({"client_id": "c", "token_url": "https://x",
                                               "client_secret_ref": "1xaioffice/vertex/client_secret"})
        self.assertEqual(config["client_secret"], "bi-mat-cua-ung-dung")

    def test_a_provider_without_a_secret_is_left_alone(self):
        config = {"client_id": "c", "token_url": "https://x"}
        self.assertIs(oauthflow.with_client_secret(config), config)

    def test_a_missing_secret_says_where_to_put_it_back(self):
        with self.assertRaises(oauthflow.FlowError) as caught:
            oauthflow.with_client_secret({"client_secret_ref": "khong-co-that"})
        self.assertIn("Tài khoản AI", str(caught.exception))


class DynamicRegistrationTests(unittest.TestCase):
    """Đăng ký động kiểu "Sign in with ChatGPT": lần đầu gửi client_id dựng sẵn, máy chủ cấp lại client_id thật."""

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            form = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
            self.server.exchanges.append(form)
            body = json.dumps({"access_token": "the-cua-goi", "refresh_token": "r",
                               "expires_in": 3600}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            return

    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), self.Provider)
        self.server.exchanges = []
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{self.server.server_port}"
        self.config = {"authorize_url": base + "/auth", "token_url": base + "/token",
                       "client_id": oauth.DYNAMIC_CLIENT, "dynamic_client": True,
                       "redirect_path": "/auth/callback", "app_name": "1xAIoffice",
                       "resource": "https://api.openai.com/v1", "scopes": ["openid"]}
        store = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        store.write("{}")
        store.close()
        os.environ["ONEX_OAUTH_STORE_FOR_TEST"] = store.name
        ids = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
        ids.close()
        os.unlink(ids.name)
        os.environ["ONEX_HOST_ID_PATH"] = ids.name
        self.addCleanup(os.environ.pop, "ONEX_OAUTH_STORE_FOR_TEST", None)
        self.addCleanup(os.environ.pop, "ONEX_HOST_ID_PATH", None)
        self.addCleanup(os.unlink, store.name)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.seen_url = []

    def browser(self, issued="oaiapp_da_cap"):
        def open_it(url):
            self.seen_url.append(url)
            query = parse_qs(urlparse(url).query)
            back = query["redirect_uri"][0] + f"?code=ma&state={query['state'][0]}"
            if issued:
                back += f"&client_id={issued}"
            threading.Thread(target=lambda: urllib.request.urlopen(back, timeout=5).read(), daemon=True).start()
            return True
        return open_it

    def test_the_first_login_registers_and_keeps_the_issued_id(self):
        oauthflow.webbrowser.open = self.browser()
        state, issued = oauthflow.login_browser(self.config, "test/chatgpt", timeout=10)
        self.assertEqual(issued, "oaiapp_da_cap")
        self.assertNotIn("the-cua-goi", state)
        self.assertEqual(self.server.exchanges[0]["client_id"], ["oaiapp_da_cap"],
                         "phải đổi mã bằng client_id vừa được cấp, không phải mã dựng sẵn")

    def test_the_authorize_url_names_this_machine_and_this_app(self):
        oauthflow.webbrowser.open = self.browser()
        oauthflow.login_browser(self.config, "test/chatgpt", timeout=10)
        query = parse_qs(urlparse(self.seen_url[0]).query)
        self.assertEqual(query["agent_name_hint"], ["1xAIoffice"])
        self.assertTrue(query["ext_agent_host_id"][0])
        self.assertEqual(query["resource"], ["https://api.openai.com/v1"])
        self.assertTrue(query["redirect_uri"][0].endswith("/auth/callback"))

    def test_the_machine_id_stays_the_same_between_logins(self):
        first = oauthflow.host_id()
        self.assertEqual(first, oauthflow.host_id())
        self.assertNotIn(first, "")

    def test_a_registration_that_hands_back_no_id_is_refused(self):
        """Không có client_id thì lần sau không đăng nhập lại được; dừng còn hơn lưu một đăng ký hỏng."""
        oauthflow.webbrowser.open = self.browser(issued="")
        with self.assertRaises(oauthflow.FlowError) as caught:
            oauthflow.login_browser(self.config, "test/chatgpt", timeout=10)
        self.assertIn("đăng ký chưa xong", str(caught.exception))

    def test_the_exchange_carries_the_resource_the_api_needs(self):
        oauthflow.webbrowser.open = self.browser()
        oauthflow.login_browser(self.config, "test/chatgpt", timeout=10)
        self.assertEqual(self.server.exchanges[0]["resource"], ["https://api.openai.com/v1"])


class LongSecretTests(unittest.TestCase):
    """Khoá và thẻ dài hơn 128 ký tự phải lưu được nguyên vẹn.

    Bản cũ đưa giá trị qua chỗ nhập bàn phím của `security`, mà chỗ đó chỉ giữ 128 ký tự: gói thẻ OAuth bị cắt
    cụt mà không báo gì, lưu xong tưởng xong, lúc dùng mới thấy hỏng. Đã xảy ra thật khi nối vào một máy chủ
    MCP ở xa.
    """

    REF = "1xaioffice-test-dai"

    def tearDown(self):
        import subprocess
        subprocess.run(["security", "delete-generic-password", "-s", self.REF],
                       capture_output=True, timeout=10)

    def test_a_token_bundle_longer_than_the_old_limit_survives(self):
        bundle = {"access_token": "a" * 500, "refresh_token": "b" * 500, "expires_at": 1.0,
                  "scope": "mcp:tools"}
        oauthflow.write_bundle(self.REF, bundle)
        got = oauthflow.read_bundle(self.REF)
        self.assertEqual(got, bundle)
        self.assertGreater(len(got["access_token"]), 128)

    def test_a_value_with_quotes_and_spaces_survives(self):
        oauthflow.write_bundle(self.REF, {"access_token": 'co "nhay" và khoảng trắng', "expires_at": 1.0})
        self.assertEqual(oauthflow.read_bundle(self.REF)["access_token"], 'co "nhay" và khoảng trắng')

    def test_a_plain_long_secret_survives_too(self):
        """Khoá API của nhiều hãng dài hơn 128 ký tự."""
        key = "sk-" + "z" * 200
        self.assertTrue(oauthflow.keychain_write(self.REF, key))
        self.assertEqual(oauthflow.read_secret(self.REF), key)

    def test_an_item_written_the_old_way_is_still_readable(self):
        """Người dùng đã lưu thẻ từ bản trước thì không được mất."""
        import json as _json
        oauthflow.keychain_write(self.REF, _json.dumps({"access_token": "cu", "expires_at": 2.0}))
        self.assertEqual(oauthflow.read_bundle(self.REF)["access_token"], "cu")


class RenameMigrationTests(unittest.TestCase):
    """Đổi tên sản phẩm thì tiền tố mục trong Keychain đổi theo, nhưng không ai phải đăng nhập lại.

    Thẻ hub và khoá API đã lưu dưới tên cũ phải đọc được nguyên vẹn, và được chép sang tên mới ngay lần
    đọc đầu tiên để lần sau không phải dò nữa.
    """

    SUFFIX = "kiem-doi-ten"
    NEW = oauthflow.SECRET_PREFIX + SUFFIX
    OLD = oauthflow.OLD_SECRET_PREFIX + SUFFIX

    def tearDown(self):
        import subprocess
        for ref in (self.NEW, self.OLD):
            subprocess.run(["security", "delete-generic-password", "-s", ref],
                           capture_output=True, timeout=10)

    def test_a_token_stored_under_the_old_name_is_still_found(self):
        oauthflow.write_bundle(self.OLD, {"access_token": "the-cu", "expires_at": 9.0})
        self.assertEqual(oauthflow.read_bundle(self.NEW)["access_token"], "the-cu")

    def test_reading_it_once_copies_it_to_the_new_name(self):
        oauthflow.write_bundle(self.OLD, {"access_token": "the-cu", "expires_at": 9.0})
        oauthflow.read_bundle(self.NEW)
        self.assertTrue(oauthflow._keychain_find(self.NEW), "phải có mục dưới tên mới sau lần đọc đầu")

    def test_the_new_name_wins_when_both_exist(self):
        oauthflow.write_bundle(self.OLD, {"access_token": "the-cu", "expires_at": 9.0})
        oauthflow.write_bundle(self.NEW, {"access_token": "the-moi", "expires_at": 9.0})
        self.assertEqual(oauthflow.read_bundle(self.NEW)["access_token"], "the-moi")

    def test_an_unrelated_name_does_not_fall_back(self):
        """Chỉ mục mang đúng tiền tố mới mới được dò sang tên cũ."""
        self.assertEqual(oauthflow._keychain_read("khong-co-tien-to-nay"), "")

    def test_a_host_id_made_under_the_old_name_is_kept(self):
        """Đổi mã máy là nhà cung cấp coi đây là máy lạ, phải đăng nhập lại — nên giữ nguyên mã cũ."""
        with tempfile.TemporaryDirectory() as home:
            legacy = Path(home) / oauthflow.OLD_CONFIG_DIR / "host-id"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("ma-may-cu\n", encoding="utf-8")
            fresh = Path(home) / "1xaioffice" / "host-id"
            os.environ["ONEX_HOST_ID_PATH"] = str(fresh)
            try:
                self.assertEqual(oauthflow.host_id(), "ma-may-cu")
                self.assertEqual(fresh.read_text(encoding="utf-8").strip(), "ma-may-cu")
            finally:
                os.environ.pop("ONEX_HOST_ID_PATH", None)
