# SPDX-License-Identifier: MPL-2.0
"""Dựng chuỗi VietQR (chuẩn EMVCo của NAPAS) và vẽ thành mã QR, thuần Python.

Dùng cho mục "Ủng hộ tác giả" trong hướng dẫn đi kèm 1xVnOffice, để mã QR nằm sẵn trong tệp, không cần mạng và không
gửi số tài khoản tới dịch vụ bên ngoài mỗi lần build.

Chuỗi sinh ra được kiểm hai lớp: tests/test_vietqr.py so với một mã VietQR thật của chủ tài khoản, còn
scripts/brand/check-vietqr.sh vẽ ảnh rồi giải mã lại bằng CoreImage và so với chuỗi gốc.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qr  # noqa: E402

GUID = "A000000727"      # định danh NAPAS
SERVICE_TO_ACCOUNT = "QRIBFTTA"  # chuyển khoản tới số tài khoản
CURRENCY_VND = "704"
COUNTRY = "VN"


def _field(tag, value):
    if len(value) > 99:
        raise ValueError(f"trường {tag} dài {len(value)} ký tự, tối đa 99")
    return f"{tag}{len(value):02d}{value}"


def crc16(text):
    """CRC-16/CCITT-FALSE, viết hoa 4 chữ số hex, như VietQR yêu cầu."""
    crc = 0xFFFF
    for byte in text.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def payload(bank_bin, account, amount=None, purpose=""):
    """Chuỗi VietQR. `amount` là số đồng (bỏ trống = người chuyển tự nhập), `purpose` là nội dung chuyển khoản
    (không dấu, vì chuẩn chỉ nhận ASCII)."""
    if not bank_bin.isdigit() or not account.isdigit():
        raise ValueError("mã ngân hàng và số tài khoản phải là chữ số")
    if purpose and not purpose.isascii():
        raise ValueError("nội dung chuyển khoản phải không dấu")
    beneficiary = _field("00", bank_bin) + _field("01", account)
    merchant = _field("00", GUID) + _field("01", beneficiary) + _field("02", SERVICE_TO_ACCOUNT)
    out = _field("00", "01") + _field("01", "12" if amount else "11") + _field("38", merchant)
    out += _field("53", CURRENCY_VND)
    if amount:
        out += _field("54", str(int(amount)))
    out += _field("58", COUNTRY)
    if purpose:
        out += _field("62", _field("08", purpose))
    out += "6304"
    return out + crc16(out)


def svg(bank_bin, account, amount=None, purpose="", **kwargs):
    """Mã QR VietQR dạng SVG."""
    return qr.svg(payload(bank_bin, account, amount, purpose), **kwargs)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="In chuỗi VietQR, hoặc ghi ảnh SVG với --out")
    ap.add_argument("--bank", required=True, help="mã ngân hàng (MB Bank: 970422)")
    ap.add_argument("--account", required=True)
    ap.add_argument("--amount", type=int, default=None)
    ap.add_argument("--purpose", default="")
    ap.add_argument("--out", help="ghi mã QR dạng SVG vào tệp này")
    ap.add_argument("--size", type=int, default=256)
    a = ap.parse_args()
    text = payload(a.bank, a.account, a.amount, a.purpose)
    if a.out:
        Path(a.out).write_text(qr.svg(text, size=a.size), encoding="utf-8")
    print(text)
