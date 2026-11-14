# SPDX-License-Identifier: MPL-2.0
"""Kiểm logic OAuth: PKCE, hình dạng yêu cầu, hạn thẻ. Không chạm mạng, không chạm kho bí mật."""
import sys
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))

from vn1x import oauth

CONFIG = {"authorize_url": "https://dangnhap.vd/auth", "token_url": "https://dangnhap.vd/token",
          "device_url": "https://dangnhap.vd/device", "client_id": "ung-dung-1x",
          "scopes": ["openid", "offline_access"]}


class PkceTests(unittest.TestCase):
    def test_verifier_and_challenge_differ_and_are_url_safe(self):
        verifier, challenge = oauth.pkce_pair()
        self.assertNotEqual(verifier, challenge)
        self.assertGreaterEqual(len(verifier), 43)
        for value in (verifier, challenge):
            self.assertTrue(all(c.isalnum() or c in "-_" for c in value), value)

    def test_each_call_gives_a_new_pair(self):
        self.assertNotEqual(oauth.pkce_pair()[0], oauth.pkce_pair()[0])

    def test_state_tokens_are_not_reused(self):
        self.assertNotEqual(oauth.state_token(), oauth.state_token())


class AuthorizeUrlTests(unittest.TestCase):
    def test_carries_pkce_state_and_scopes(self):
        url = oauth.authorize_url(CONFIG, "http://127.0.0.1:5/cb", "thachthuc", "trangthai")
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["code_challenge"], ["thachthuc"])
        self.assertEqual(query["state"], ["trangthai"])
        self.assertEqual(query["scope"], ["openid offline_access"])
        self.assertEqual(query["redirect_uri"], ["http://127.0.0.1:5/cb"])

    def test_extra_params_of_a_provider_are_kept(self):
        config = dict(CONFIG, extra_auth_params={"access_type": "offline"})
        query = parse_qs(urlparse(oauth.authorize_url(config, "u", "c", "s")).query)
        self.assertEqual(query["access_type"], ["offline"])

    def test_missing_client_id_is_refused(self):
        with self.assertRaises(oauth.OAuthError):
            oauth.authorize_url({"authorize_url": "https://x"}, "u", "c", "s")


class RedirectTests(unittest.TestCase):
    def test_reads_the_code(self):
        self.assertEqual(oauth.parse_redirect("http://127.0.0.1:1/cb?code=abc&state=st", "st"), "abc")

    def test_a_different_state_is_refused(self):
        """Chống việc trang lạ ghép một lần đăng nhập không phải của người dùng."""
        with self.assertRaises(oauth.OAuthError):
            oauth.parse_redirect("http://127.0.0.1:1/cb?code=abc&state=la", "st")

    def test_a_refusal_from_the_provider_is_reported(self):
        with self.assertRaises(oauth.OAuthError) as caught:
            oauth.parse_redirect("http://127.0.0.1:1/cb?error=access_denied&state=st", "st")
        self.assertIn("từ chối", str(caught.exception))

    def test_no_code_is_refused(self):
        with self.assertRaises(oauth.OAuthError):
            oauth.parse_redirect("http://127.0.0.1:1/cb?state=st", "st")


class RequestShapeTests(unittest.TestCase):
    def test_token_request_sends_the_verifier_not_a_secret(self):
        url, headers, body = oauth.token_request(CONFIG, "ma", "nguoi-xac-minh", "http://127.0.0.1:1/cb")
        self.assertEqual(url, CONFIG["token_url"])
        self.assertEqual(headers["Content-Type"], "application/x-www-form-urlencoded")
        form = parse_qs(body)
        self.assertEqual(form["grant_type"], ["authorization_code"])
        self.assertEqual(form["code_verifier"], ["nguoi-xac-minh"])
        self.assertNotIn("client_secret", form)

    def test_client_secret_is_sent_only_when_the_provider_needs_one(self):
        form = parse_qs(oauth.token_request(dict(CONFIG, client_secret="bi-mat"), "m", "v", "u")[2])
        self.assertEqual(form["client_secret"], ["bi-mat"])

    def test_refresh_request(self):
        form = parse_qs(oauth.refresh_request(CONFIG, "the-gia-han")[2])
        self.assertEqual(form["grant_type"], ["refresh_token"])
        self.assertEqual(form["refresh_token"], ["the-gia-han"])

    def test_refresh_without_a_token_is_refused(self):
        with self.assertRaises(oauth.OAuthError):
            oauth.refresh_request(CONFIG, "")

    def test_device_requests(self):
        url, _, body = oauth.device_start_request(CONFIG)
        self.assertEqual(url, CONFIG["device_url"])
        self.assertEqual(parse_qs(body)["scope"], ["openid offline_access"])
        form = parse_qs(oauth.device_poll_request(CONFIG, "ma-thiet-bi")[2])
        self.assertEqual(form["grant_type"], ["urn:ietf:params:oauth:grant-type:device_code"])
        self.assertEqual(form["device_code"], ["ma-thiet-bi"])


class BundleTests(unittest.TestCase):
    def test_keeps_only_what_is_needed(self):
        got = oauth.bundle({"access_token": "t", "refresh_token": "r", "expires_in": 60,
                            "khong_can": "bo di"}, now=1000)
        self.assertEqual(got["expires_at"], 1060)
        self.assertNotIn("khong_can", got)

    def test_a_server_that_gives_no_token_is_an_error(self):
        with self.assertRaises(oauth.OAuthError):
            oauth.bundle({"error": "invalid_grant", "error_description": "mã hết hạn"})

    def test_a_missing_lifetime_falls_back_to_an_hour(self):
        self.assertEqual(oauth.bundle({"access_token": "t"}, now=0)["expires_at"], oauth.DEFAULT_EXPIRES_IN)

    def test_merge_keeps_the_old_refresh_token(self):
        """Google không gửi lại refresh token ở lần gia hạn; mất nó là người dùng phải đăng nhập lại."""
        merged = oauth.merge({"refresh_token": "cu"}, {"access_token": "moi"})
        self.assertEqual(merged["refresh_token"], "cu")

    def test_merge_prefers_a_new_refresh_token(self):
        merged = oauth.merge({"refresh_token": "cu"}, {"access_token": "moi", "refresh_token": "moi"})
        self.assertEqual(merged["refresh_token"], "moi")


class ExpiryTests(unittest.TestCase):
    def test_a_fresh_token_is_kept(self):
        self.assertFalse(oauth.needs_refresh({"access_token": "t", "expires_at": time.time() + 3600}))

    def test_a_token_about_to_expire_is_renewed_early(self):
        self.assertTrue(oauth.needs_refresh({"access_token": "t", "expires_at": time.time() + 30}))

    def test_no_token_means_refresh(self):
        self.assertTrue(oauth.needs_refresh({}))

    def test_header_refuses_when_not_signed_in(self):
        with self.assertRaises(oauth.OAuthError):
            oauth.header({})
        self.assertEqual(oauth.header({"access_token": "t"}), "Bearer t")

    def test_the_description_never_contains_the_token(self):
        text = oauth.redacted({"access_token": "BI-MAT-KHONG-DUOC-HIEN", "refresh_token": "CUNG-BI-MAT",
                               "expires_at": time.time() + 600})
        self.assertNotIn("BI-MAT", text)
        self.assertNotIn("CUNG-BI-MAT", text)
        self.assertIn("đăng nhập", text)


if __name__ == "__main__":
    unittest.main()
