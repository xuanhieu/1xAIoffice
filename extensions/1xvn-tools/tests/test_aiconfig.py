# SPDX-License-Identifier: MPL-2.0
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import aiconfig  # noqa: E402

CLAUDE = {"id": "claude", "type": "anthropic", "secret_ref": "1xvnoffice/anthropic",
          "models": ["claude-sonnet-5-5", "claude-haiku-5-5"]}
LOCAL = {"id": "local", "type": "ollama", "base_url": "http://127.0.0.1:11434/v1", "models": ["qwen3:8b"]}


class LoadSaveTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "providers.json"

    def test_missing_file_gives_empty_config(self):
        config = aiconfig.load(self.path)
        self.assertEqual(config["providers"], [])
        self.assertIn("max_output_tokens", config["limits"])

    def test_round_trip(self):
        config = aiconfig.add_provider(aiconfig.load(self.path), "claude", "anthropic",
                                       CLAUDE["models"], secret_ref=CLAUDE["secret_ref"], role="soan_thao")
        aiconfig.save(self.path, config)
        again = aiconfig.load(self.path)
        self.assertEqual(again["providers"][0]["id"], "claude")
        self.assertEqual(again["roles"]["soan_thao"], "claude/claude-sonnet-5-5")

    def test_refuses_to_write_an_api_key(self):
        config = {"providers": [dict(CLAUDE, api_key="sk-that-la-bi-mat")]}
        with self.assertRaises(aiconfig.ConfigError) as caught:
            aiconfig.save(self.path, config)
        self.assertNotIn("sk-that-la-bi-mat", str(caught.exception))

    def test_broken_json_is_reported(self):
        self.path.write_text("{khong phai json", encoding="utf-8")
        with self.assertRaises(aiconfig.ConfigError):
            aiconfig.load(self.path)

    def test_saved_file_never_holds_the_key(self):
        aiconfig.save(self.path, {"providers": [CLAUDE], "roles": {}})
        self.assertNotIn("sk-", self.path.read_text(encoding="utf-8"))
        self.assertIn("secret_ref", json.loads(self.path.read_text(encoding="utf-8"))["providers"][0])


class ProblemTests(unittest.TestCase):
    def test_good_config_has_no_problem(self):
        config = {"providers": [CLAUDE, LOCAL], "roles": {"soan_thao": "claude/claude-haiku-5-5",
                                                          "cuc_bo": "local/qwen3:8b"}}
        self.assertEqual(aiconfig.problems(config), [])

    def test_catches_bad_entries(self):
        config = {"providers": [{"id": "x", "type": "openai", "models": []},
                                {"id": "x", "type": "khong-biet", "models": ["m"], "secret_ref": "r"},
                                dict(LOCAL, secret_ref="thua")],
                  "roles": {"soan_thao": "khong-co/m"}}
        found = " | ".join(aiconfig.problems(config))
        for expected in ("thiếu secret_ref", "chưa khai báo mô hình", "id bị trùng",
                         "không hỗ trợ", "không cần khoá", "không thấy nhà cung cấp"):
            with self.subTest(expected=expected):
                self.assertIn(expected, found)


class KeyRequirementTests(unittest.TestCase):
    def test_cloud_openai_needs_a_key(self):
        found = aiconfig.problems({"providers": [{"id": "x", "type": "openai", "models": ["m"]}]})
        self.assertTrue(any("secret_ref" in p for p in found))

    def test_self_hosted_openai_does_not(self):
        local = {"id": "noibo", "type": "openai", "base_url": "https://ai.coquan.gov.vn/v1", "models": ["vn-llm"]}
        self.assertEqual(aiconfig.problems({"providers": [local]}), [])

    def test_anthropic_always_needs_a_key(self):
        entry = {"id": "c", "type": "anthropic", "base_url": "https://proxy.noi.bo/v1", "models": ["m"]}
        self.assertTrue(any("secret_ref" in p for p in aiconfig.problems({"providers": [entry]})))


class ResolveTests(unittest.TestCase):
    def test_role_points_at_provider_and_model(self):
        config = {"providers": [CLAUDE, LOCAL], "roles": {"nhanh": "claude/claude-haiku-5-5"}}
        provider, model = aiconfig.resolve(config, "nhanh")
        self.assertEqual((provider["id"], model), ("claude", "claude-haiku-5-5"))

    def test_unset_role_falls_back_to_first_provider(self):
        provider, model = aiconfig.resolve({"providers": [LOCAL, CLAUDE]}, "soan_thao")
        self.assertEqual((provider["id"], model), ("local", "qwen3:8b"))

    def test_errors(self):
        with self.assertRaises(aiconfig.ConfigError):
            aiconfig.resolve({"providers": []})
        with self.assertRaises(aiconfig.ConfigError):
            aiconfig.resolve({"providers": [CLAUDE], "roles": {"r": "claude/mo-hinh-la"}}, "r")

    def test_provider_without_model_in_role(self):
        provider, model = aiconfig.resolve({"providers": [CLAUDE], "roles": {"r": "claude"}}, "r")
        self.assertEqual(model, "claude-sonnet-5-5")
        self.assertEqual(provider["type"], "anthropic")


if __name__ == "__main__":
    unittest.main()


class AuthModeTests(unittest.TestCase):
    OAUTH = {"id": "cong", "type": "openai", "models": ["m"], "auth": "oauth",
             "base_url": "https://ai.coquan.gov.vn/v1", "secret_ref": "1xvnoffice/cong",
             "oauth": {"authorize_url": "https://sso/a", "token_url": "https://sso/t", "client_id": "c"}}

    def test_a_signed_in_provider_is_a_valid_configuration(self):
        self.assertEqual(aiconfig.problems({"providers": [self.OAUTH]}), [])
        self.assertEqual(aiconfig.auth_mode(self.OAUTH), "oauth")

    def test_an_oauth_provider_without_its_addresses_is_caught(self):
        entry = dict(self.OAUTH, oauth={"client_id": "c"})
        found = " | ".join(aiconfig.problems({"providers": [entry]}))
        self.assertIn("token_url", found)

    def test_a_token_written_into_the_file_is_refused(self):
        """Thẻ phải nằm trong kho bí mật của máy, không nằm trong providers.json."""
        entry = dict(self.OAUTH, oauth=dict(self.OAUTH["oauth"], refresh_token="dung-ghi-vao-day"))
        found = " | ".join(aiconfig.problems({"providers": [entry]}))
        self.assertIn("kho bí mật", found)

    def test_saving_a_token_into_the_file_is_refused(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json") as handle:
            with self.assertRaises(aiconfig.ConfigError):
                aiconfig.save(handle.name, {"providers": [{"id": "x", "access_token": "the"}]})

    def test_an_unknown_auth_mode_is_named(self):
        found = " | ".join(aiconfig.problems({"providers": [{"id": "x", "type": "openai", "models": ["m"],
                                                             "auth": "bang-gi-do"}]}))
        self.assertIn("bang-gi-do", found)

    def test_an_oauth_block_without_the_oauth_mode_is_caught(self):
        entry = {"id": "x", "type": "openai", "models": ["m"], "auth": "key", "secret_ref": "r",
                 "oauth": {"client_id": "c"}}
        self.assertTrue(any("oauth" in p for p in aiconfig.problems({"providers": [entry]})))


class PutAndRemoveTests(unittest.TestCase):
    ENTRY = {"id": "moi", "type": "openai", "auth": "key", "secret_ref": "r", "models": ["m1", "m2"]}

    def test_adding_a_provider_can_also_set_the_role(self):
        config = aiconfig.put_provider(aiconfig.EMPTY, self.ENTRY, role="soan_thao")
        self.assertEqual(config["roles"]["soan_thao"], "moi/m1")
        self.assertEqual(aiconfig.resolve(config)[1], "m1")

    def test_adding_the_same_id_twice_replaces_it(self):
        config = aiconfig.put_provider(aiconfig.EMPTY, self.ENTRY)
        config = aiconfig.put_provider(config, dict(self.ENTRY, models=["khac"]))
        self.assertEqual(len(config["providers"]), 1)
        self.assertEqual(config["providers"][0]["models"], ["khac"])

    def test_the_original_configuration_is_not_changed(self):
        before = {"providers": [], "roles": {}}
        aiconfig.put_provider(before, self.ENTRY, role="nhanh")
        self.assertEqual(before, {"providers": [], "roles": {}})

    def test_removing_a_provider_also_drops_the_roles_pointing_at_it(self):
        config = aiconfig.put_provider(aiconfig.EMPTY, self.ENTRY, role="soan_thao")
        config = aiconfig.remove_provider(config, "moi")
        self.assertEqual(config["providers"], [])
        self.assertEqual(config["roles"], {})
