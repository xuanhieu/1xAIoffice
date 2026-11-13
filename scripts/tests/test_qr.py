# SPDX-License-Identifier: MPL-2.0
"""Kiểm bộ vẽ mã QR và bộ dựng chuỗi VietQR (thuần Python, chạy được cả trên CI).

Phép kiểm mạnh nhất: chuỗi dựng ra phải trùng từng ký tự với một mã VietQR thật của chủ tài khoản, kể cả CRC.
Ảnh vẽ ra còn được giải mã lại bằng scripts/brand/check-vietqr.sh (chỉ chạy trên máy macOS có Chrome).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brand"))
import qr  # noqa: E402
import vietqr  # noqa: E402

# Mã VietQR thật của chủ tài khoản (50.000đ), đọc từ ảnh trang ủng hộ 1xag.com ngày 13/11/2026.
REAL = ("00020101021238540010A00000072701240006970422011091122334490208QRIBFTTA"
        "53037045405500005802VN62170813Ung ho 1xHieu630413D4")
BANK, ACCOUNT, PURPOSE = "970422", "9112233449", "Ung ho 1xHieu"


class VietQrTests(unittest.TestCase):
    def test_matches_real_code(self):
        self.assertEqual(vietqr.payload(BANK, ACCOUNT, 50000, PURPOSE), REAL)

    def test_crc(self):
        self.assertEqual(vietqr.crc16(REAL[:-4]), REAL[-4:])
        self.assertEqual(vietqr.crc16("123456789"), "29B1")  # vectơ chuẩn CRC-16/CCITT-FALSE

    def test_without_amount(self):
        out = vietqr.payload(BANK, ACCOUNT, purpose=PURPOSE)
        self.assertIn("010211", out)      # mã tĩnh: người chuyển tự nhập số tiền
        self.assertNotIn("5405", out)
        self.assertEqual(vietqr.crc16(out[:-4]), out[-4:])

    def test_rejects_bad_input(self):
        for args in ((("97O422", ACCOUNT), {}), ((BANK, "911-223"), {}), ((BANK, ACCOUNT), {"purpose": "Ủng hộ"})):
            with self.subTest(args=args), self.assertRaises(ValueError):
                vietqr.payload(*args[0], **args[1])


class QrTests(unittest.TestCase):
    def test_format_bits_match_standard(self):
        want = {("M", 0): "101010000010010", ("M", 5): "100000011001110",
                ("L", 0): "111011111000100", ("L", 7): "110100101110110"}
        for (level, mask), bits in want.items():
            data = (qr.ECL_BITS[level] << 3) | mask
            got = f"{((data << 10) | qr._bch(data, 0x537, 10)) ^ 0x5412:015b}"
            self.assertEqual(got, bits, f"{level}{mask}")

    def test_version_bits_match_standard(self):
        want = {7: "000111110010010100", 8: "001000010110111100",
                9: "001001101010011001", 10: "001010010011010011"}
        for version, bits in want.items():
            self.assertEqual(f"{(version << 12) | qr._bch(version, 0x1F25, 12):018b}", bits)

    def test_version_choice_and_size(self):
        self.assertEqual(qr.choose_version(len(REAL), "M"), 7)
        self.assertEqual(len(qr.matrix(REAL, "M")), 7 * 4 + 17)
        with self.assertRaises(ValueError):
            qr.choose_version(10_000, "M")

    def test_finder_patterns(self):
        m = qr.matrix("HELLO", "M")
        n = len(m)
        for ox, oy in ((0, 0), (n - 7, 0), (0, n - 7)):
            self.assertTrue(all(m[oy][ox + i] for i in range(7)))          # viền trên liền nét
            self.assertTrue(m[oy + 3][ox + 3])                              # lõi
            self.assertFalse(m[oy + 1][ox + 1])                             # vòng trắng

    def test_svg_is_square_and_quiet(self):
        out = qr.svg(REAL, size=300)
        n = len(qr.matrix(REAL, "M")) + 8
        self.assertIn(f'viewBox="0 0 {n} {n}"', out)
        self.assertIn('width="300" height="300"', out)


if __name__ == "__main__":
    unittest.main()
