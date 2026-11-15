#!/usr/bin/env bash
# Nghiệm thu mốc M5 với nhà cung cấp AI THẬT của bạn.
# Cần: đã gắn tài khoản AI trong app (Tiếng Việt ▸ Tài khoản AI), tức có ~/Library/Application Support/
# 1xAIoffice/4/user/providers.json và khoá nằm trong Keychain.
# Script này KHÔNG đọc và KHÔNG in khoá; app tự lấy từ kho bí mật.
set -euo pipefail
# shellcheck source=scripts/env.sh
source "$(dirname "$0")/env.sh"

# shellcheck disable=SC2012 # bundle names are fixed product names without spaces
APP="$(ls -dt "$ONEX_WORK"/src/libreoffice-*/instdir/*.app 2>/dev/null | head -1)"
[ -n "$APP" ] || { echo "Chưa có bản dựng nào trong instdir."; exit 1; }
CONFIG="${ONEX_AI_CONFIG_PATH:-$HOME/Library/Application Support/1xAIoffice/4/user/providers.json}"
if [ ! -f "$CONFIG" ]; then
  echo "Chưa thấy cấu hình nhà cung cấp AI:"
  echo "  $CONFIG"
  echo
  echo "Mở 1xAIoffice, vào Tiếng Việt ▸ Tài khoản AI (khoá API hoặc đăng nhập), chọn nhà cung cấp"
  echo "rồi dán khoá vào hộp che chữ. Xong thì chạy lại lệnh này."
  exit 1
fi

PROFILE="$(mktemp -d "$ONEX_WORK/m5.XXXXXX")"
ANSWER="$PROFILE/tra-loi-skill.txt"
PIPE="m5_$$"
rm -f "/tmp/OSL_PIPE_$(id -u)_$PIPE"
echo "==> Dùng cấu hình nhà cung cấp: $CONFIG"
# Mở app CÓ GIAO DIỆN: soffice headless trên macOS không mở nổi tài liệu thứ hai trong một phiên.
ONEX_TOOLS_SILENT=1 ONEX_TOOLS_WARN_OUT="$ANSWER" \
  ONEX_AI_CONFIG_PATH="$CONFIG" \
  ONEX_SKILL_NAME="soan-van-ban-nd30" \
  ONEX_SKILL_QUESTION="Soạn công văn của Sở Khoa học và Công nghệ gửi Ủy ban nhân dân các quận, huyện, đề nghị phối hợp triển khai nhiệm vụ khoa học và công nghệ năm 2027. Chỉ viết phần nội dung, mỗi đoạn một dòng, không viết quốc hiệu hay nơi nhận." \
  "$APP/Contents/MacOS/soffice" --norestore -env:UserInstallation="file://$PROFILE" \
  "--accept=pipe,name=$PIPE;urp;" >/dev/null 2>&1 &
PID=$!
sleep 20
rc=0
"$APP/Contents/Resources/python" "$REPO_ROOT/scripts/nghiem-thu-m5.py" "$PIPE" "$ANSWER" || rc=$?
echo
echo "==> Cửa sổ 1xAIoffice đang mở để bạn đọc văn bản. Đóng xong thì nhấn Enter ở đây để dọn."
read -r _ || true
kill -9 "$PID" 2>/dev/null || true
rm -rf "$PROFILE" "/tmp/OSL_PIPE_$(id -u)_$PIPE"
exit "$rc"
