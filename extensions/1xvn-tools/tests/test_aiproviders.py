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
                    self.assertIn("client_id", preset.get("needs") or [],
                                  "mục OAuth phải hỏi client_id của chính người dùng")

    def test_ids_are_unique(self):
        ids = [preset["id"] for preset in aiproviders.PRESETS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_secret_value_ships_with_the_app(self):
        """1xVnOffice không nhúng bí mật của ai cả: người dùng mang khoá và ứng dụng OAuth của họ.

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
        self.assertEqual(entry["oauth"]["client_secret_ref"], "1xvnoffice/vertex/client_secret")
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
        self.assertEqual(entry["secret_ref"], "1xvnoffice/openai")
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
