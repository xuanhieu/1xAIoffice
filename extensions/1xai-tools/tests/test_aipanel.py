# SPDX-License-Identifier: MPL-2.0
"""Dòng trạng thái của thanh bên AI."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pythonpath"))
from vn1x import aipanel  # noqa: E402

T = {"panel_no_ai": "Chưa gắn tài khoản AI.", "panel_ai": "Đang dùng: {name}"}


class StatusTests(unittest.TestCase):
    def test_no_account_invites_the_user(self):
        self.assertEqual(aipanel.status({}, T), "Chưa gắn tài khoản AI.")
        self.assertEqual(aipanel.status(None, T), "Chưa gắn tài khoản AI.")

    def test_shows_the_provider_and_model_in_use(self):
        cfg = {"providers": [{"id": "groq", "models": ["llama-3.3-70b"]}]}
        self.assertEqual(aipanel.status(cfg, T), "Đang dùng: groq · llama-3.3-70b")

    def test_a_provider_without_a_model_still_reads_well(self):
        self.assertEqual(aipanel.status({"providers": [{"id": "ollama"}]}, T), "Đang dùng: ollama")


if __name__ == "__main__":
    unittest.main()
