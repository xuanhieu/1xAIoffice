# SPDX-License-Identifier: MPL-2.0
"""Kiểm danh mục nhà cung cấp AI cài sẵn."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))

from vn1x import aiconfig, aiproviders


class CatalogueTests(unittest.TestCase):
    def test_every_entry_is_complete_and_usable(self):
        for preset in aiproviders.PRESETS:
            with self.subTest(preset["id"]):
                self.assertIn(preset["wire"], aiconfig.KINDS)
                self.assertIn(preset["auth"], aiconfig.AUTH_MODES)
                self.assertTrue(preset["label"] and preset["note"])
                if preset["auth"] == "oauth":
                    dynamic = (preset.get("oauth") or {}).get("dynamic_client")
                    self.assertTrue(dynamic or "client_id" in (preset.get("needs") or []),
                                    "mục OAuth phải hỏi client_id của người dùng, trừ khi nhà cung cấp cho "
                                    "ứng dụng tự đăng ký")

    def test_ids_are_unique(self):
        ids = [preset["id"] for preset in aiproviders.PRESETS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_secret_value_ships_with_the_app(self):
        """1xAIoffice không nhúng bí mật của ai cả: người dùng mang khoá và ứng dụng OAuth của họ.

        Mục Google có cờ `client_secret: True` — đó là CÂU HỎI "nhà cung cấp này có đòi client secret không",
        không phải giá trị secret.
        """
        for preset in aiproviders.PRESETS:
            with self.subTest(preset["id"]):
                self.assertIn(preset.get("client_secret", False), (True, False))
                self.assertNotIn("client_id", preset.get("oauth") or {})
                for field in ("api_key", "secret", "token"):
                    self.assertNotIn(field, preset)

    def test_a_provider_that_needs_a_client_secret_only_stores_its_name(self):
        entry = aiproviders.fill(aiproviders.get("vertex"), {"client_id": "c", "base_url": "https://x/v1"})
        self.assertEqual(entry["oauth"]["client_secret_ref"], "1xaioffice/vertex/client_secret")
        self.assertNotIn("client_secret", entry["oauth"])
        self.assertEqual(aiconfig.problems({"providers": [dict(entry, models=["m"])]}), [])

    def test_there_are_both_key_and_oauth_and_local_choices(self):
        for mode in ("key", "oauth", "none"):
            self.assertTrue(aiproviders.listing(mode), mode)

    def test_cloud_entries_point_at_https(self):
        for preset in aiproviders.PRESETS:
            if preset["base_url"] and preset["auth"] != "none":
                self.assertTrue(preset["base_url"].startswith("https://"), preset["id"])


class FillTests(unittest.TestCase):
    def test_a_simple_key_provider_needs_nothing_more(self):
        entry = aiproviders.fill(aiproviders.get("openai"), {})
        self.assertEqual(entry["auth"], "key")
        self.assertEqual(entry["secret_ref"], "1xaioffice/openai")
        self.assertEqual(aiconfig.problems({"providers": [dict(entry, models=["m"])]}), [])

    def test_a_local_provider_carries_no_secret_ref(self):
        entry = aiproviders.fill(aiproviders.get("ollama"), {})
        self.assertNotIn("secret_ref", entry)
        self.assertEqual(aiconfig.problems({"providers": [dict(entry, models=["m"])]}), [])

    def test_missing_fields_are_named(self):
        with self.assertRaises(ValueError) as caught:
            aiproviders.fill(aiproviders.get("azure"), {"client_id": "c"})
        self.assertIn("tenant", str(caught.exception))

    def test_the_tenant_is_put_into_the_microsoft_addresses(self):
        entry = aiproviders.fill(aiproviders.get("azure"),
                                 {"client_id": "c", "tenant": "co-quan", "base_url": "https://r/openai"})
        self.assertIn("co-quan", entry["oauth"]["token_url"])
        self.assertNotIn("{tenant}", entry["oauth"]["authorize_url"])
        self.assertEqual(aiconfig.problems({"providers": [dict(entry, models=["m"])]}), [])

    def test_an_internal_gateway_takes_the_addresses_of_the_organisation(self):
        entry = aiproviders.fill(aiproviders.get("oidc"),
                                 {"client_id": "c", "authorize_url": "https://sso.coquan.gov.vn/auth",
                                  "token_url": "https://sso.coquan.gov.vn/token",
                                  "base_url": "https://ai.coquan.gov.vn/v1"})
        self.assertEqual(entry["oauth"]["authorize_url"], "https://sso.coquan.gov.vn/auth")
        self.assertEqual(aiconfig.problems({"providers": [dict(entry, models=["m"])]}), [])

    def test_vertex_asks_for_the_vertex_model_path(self):
        entry = aiproviders.fill(aiproviders.get("vertex"),
                                 {"client_id": "c", "base_url": "https://x/v1"})
        self.assertEqual(entry["model_path"], "publishers/google/models")

    def test_filling_never_returns_a_key_or_a_token(self):
        entry = aiproviders.fill(aiproviders.get("anthropic"), {})
        for field in ("api_key", "access_token", "refresh_token", "client_secret"):
            self.assertNotIn(field, entry)


if __name__ == "__main__":
    unittest.main()


class ChatGptPlanTests(unittest.TestCase):
    """Mục "dùng gói ChatGPT": tự đăng ký, không hỏi khoá, không hỏi client_id."""

    def preset(self):
        return aiproviders.get("chatgpt")

    def test_it_asks_the_user_for_nothing(self):
        """Đó là điểm của cả tính năng: người dùng chỉ bấm đăng nhập."""
        self.assertEqual(self.preset().get("needs") or [], [])
        entry = aiproviders.fill(self.preset(), {})
        self.assertEqual(aiconfig.problems({"providers": [dict(entry, models=["gpt-x"])]}), [])

    def test_the_first_login_uses_the_registration_client_id(self):
        from vn1x import oauth
        entry = aiproviders.fill(self.preset(), {})
        self.assertEqual(entry["oauth"]["client_id"], oauth.DYNAMIC_CLIENT)
        self.assertTrue(entry["oauth"]["dynamic_client"])

    def test_it_asks_for_the_scope_that_spends_the_plan(self):
        scopes = self.preset()["oauth"]["scopes"]
        self.assertIn("chatgpt.tokens.use.direct", scopes)
        self.assertIn("offline_access", scopes)          # để tự gia hạn, khỏi bắt đăng nhập lại mỗi giờ

    def test_the_callback_path_is_the_one_openai_requires(self):
        self.assertEqual(self.preset()["oauth"]["redirect_path"], "/auth/callback")

    def test_it_carries_no_client_secret_anywhere(self):
        entry = aiproviders.fill(self.preset(), {})
        self.assertNotIn("client_secret", entry["oauth"])
        self.assertNotIn("client_secret_ref", entry["oauth"])

    def test_it_speaks_the_responses_api(self):
        self.assertEqual(self.preset()["wire"], "responses")
        self.assertEqual(aiproviders.fill(self.preset(), {})["base_url"], "https://api.openai.com/v1")

    def test_it_does_not_pretend_to_list_models(self):
        """Luồng này không có đường hỏi danh sách mô hình, nên app phải để người dùng tự gõ tên."""
        self.assertFalse(self.preset()["can_list_models"])


class FreeProviderTests(unittest.TestCase):
    """Người mới phải gắn được AI mà không trả tiền: hãng có gói miễn phí lên đầu, kèm trang lấy khoá."""

    def test_free_providers_come_first(self):
        ordered = aiproviders.free_first()
        flags = [bool(p.get("free")) for p in ordered]
        self.assertEqual(flags, sorted(flags, reverse=True))
        self.assertEqual(len(ordered), len(aiproviders.PRESETS))

    def test_every_free_provider_says_where_to_get_a_key(self):
        for preset in aiproviders.PRESETS:
            if preset.get("free"):
                self.assertTrue(preset.get("key_url", "").startswith("https://"), preset["id"])
                self.assertEqual(preset["auth"], "key", preset["id"])

    def test_the_catalogue_line_says_free(self):
        self.assertIn("miễn phí", aiproviders.summary(aiproviders.BY_ID["groq"]))
        self.assertNotIn("miễn phí", aiproviders.summary(aiproviders.BY_ID["openai"]))

    def test_groq_opens_the_page_the_owner_named(self):
        self.assertEqual(aiproviders.BY_ID["groq"]["key_url"], "https://console.groq.com/keys")
