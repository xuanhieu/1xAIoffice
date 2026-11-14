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
                       "device_url": base + "/device", "client_id": "1xvnoffice-test",
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
        self.store.write(json.dumps({"1xvnoffice/vertex/client_secret": "bi-mat-cua-ung-dung"}))
        self.store.close()
        os.environ["ONEX_SECRET_STORE_FOR_TEST"] = self.store.name
        self.addCleanup(os.environ.pop, "ONEX_SECRET_STORE_FOR_TEST", None)
        self.addCleanup(os.unlink, self.store.name)

    def test_the_secret_is_fetched_from_the_store_at_the_moment_it_is_needed(self):
        config = oauthflow.with_client_secret({"client_id": "c", "token_url": "https://x",
                                               "client_secret_ref": "1xvnoffice/vertex/client_secret"})
        self.assertEqual(config["client_secret"], "bi-mat-cua-ung-dung")

    def test_a_provider_without_a_secret_is_left_alone(self):
        config = {"client_id": "c", "token_url": "https://x"}
        self.assertIs(oauthflow.with_client_secret(config), config)

    def test_a_missing_secret_says_where_to_put_it_back(self):
        with self.assertRaises(oauthflow.FlowError) as caught:
            oauthflow.with_client_secret({"client_secret_ref": "khong-co-that"})
        self.assertIn("Tài khoản AI", str(caught.exception))
