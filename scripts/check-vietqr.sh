#!/usr/bin/env bash
# Kiểm mã VietQR đi kèm sản phẩm: vẽ lại từ branding/about.json, chụp thành ảnh rồi GIẢI MÃ ảnh đó và so với chuỗi gốc.
# Một mã QR sai sẽ đưa tiền đi đâu không biết, nên mã chỉ được phát hành khi vòng kiểm này đạt.
# Cần macOS (CoreImage để giải mã) và Google Chrome (để chụp SVG). Chạy: scripts/check-vietqr.sh
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "Không thấy Google Chrome, bỏ qua kiểm ảnh."; exit 0; }
command -v swiftc >/dev/null || { echo "Không thấy swiftc, bỏ qua kiểm ảnh."; exit 0; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

want="$(python3 - "$REPO_ROOT" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts" / "brand"))
import vietqr
d = json.loads((root / "branding" / "about.json").read_text(encoding="utf-8"))["donate"]
print(vietqr.payload(d["bank_bin"], d["account"], purpose=d["purpose"]))
PY
)"
svg="$REPO_ROOT/branding/out/vietqr.svg"
[ -f "$svg" ] || { echo "Chưa có $svg: chạy scripts/brand/make-brand.py trước."; exit 1; }

{ printf '<!doctype html><body style="margin:0">'; cat "$svg"; } > "$tmp/qr.html"
"$CHROME" --headless=new --use-mock-keychain --password-store=basic --disable-gpu --no-first-run \
  --user-data-dir="$tmp/chrome" --hide-scrollbars --force-device-scale-factor=1 \
  --window-size=640,640 --screenshot="$tmp/qr.png" "$tmp/qr.html" >/dev/null 2>&1
swiftc -O "$REPO_ROOT/scripts/brand/qr-decode.swift" -o "$tmp/qr-decode" >/dev/null
got="$("$tmp/qr-decode" "$tmp/qr.png")"

if [ "$got" = "$want" ]; then
  echo "OK   mã VietQR giải mã lại đúng chuỗi gốc (${#want} ký tự)."
else
  echo "SAI  mã VietQR đọc ra khác chuỗi gốc."
  echo "  mong đợi: $want"
  echo "  đọc được: $got"
  exit 1
fi
