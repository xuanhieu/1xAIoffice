#!/usr/bin/env bash
# Download the upstream tarballs named in upstream/source-lock.json and verify size, SHA-256 and OpenPGP signature (sqv).
# Usage: scripts/fetch-source.sh [--dry-run] [--skip-optional] [--allow-no-gpg]
set -euo pipefail
# shellcheck source=scripts/env.sh
source "$(dirname "$0")/env.sh"

DRY_RUN=0; SKIP_OPTIONAL=0; ALLOW_NO_GPG=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --skip-optional) SKIP_OPTIONAL=1 ;;
    --allow-no-gpg) ALLOW_NO_GPG=1 ;;
    *) die "Tham số lạ: $arg" ;;
  esac
done

BASE_URL="$(lock_get "L['baseUrl']")"
FPR="$(lock_get "L['signingKey']['fingerprint']")"
ENTRIES="$(lock_get "'\n'.join('%s %s %s %d' % (t['name'], t['sha256'], t['size'], t['required']) for t in L['tarballs'])")"

if [ "$DRY_RUN" = 1 ]; then
  info "Chạy thử: không tải gì. Thư mục đích: $TARBALL_DIR"
  while read -r name sha size required; do
    [ "$SKIP_OPTIONAL" = 1 ] && [ "$required" = 0 ] && continue
    printf '  %s  %s MB  %s/%s\n' "$name" "$((size / 1048576))" "$BASE_URL" "$name"
  done <<< "$ENTRIES"
  exit 0
fi

require_work_volume
[ "$(free_gib "$ONEX_WORK")" -ge 2 ] || die "Cần ít nhất 2 GiB trống trên $ONEX_WORK."

# Signatures are checked with sqv (Sequoia), from the private Homebrew on the SSD (scripts/bootstrap-tools.sh),
# against the upstream Build Team key kept in the repo. sqv prints the fingerprint of the key that made a good
# signature; it must equal the fingerprint in the lock file.
KEYRING="$REPO_ROOT/upstream/source-signing-key.asc"
SQV="$ONEX_BREW/bin/sqv"
HAVE_SQV=1
if [ ! -x "$SQV" ]; then
  HAVE_SQV=0
  [ "$ALLOW_NO_GPG" = 1 ] || die "Chưa có sqv (scripts/bootstrap-tools.sh). Dùng --allow-no-gpg chỉ khi chấp nhận bỏ kiểm chữ ký."
  warn "Bỏ qua kiểm chữ ký OpenPGP theo yêu cầu (--allow-no-gpg); vẫn kiểm SHA-256."
fi
[ -f "$KEYRING" ] || die "Thiếu khoá ký $KEYRING."

verify_sha() { [ "$(shasum -a 256 "$1" | awk '{print $1}')" = "$2" ]; }

while read -r name sha size required; do
  [ "$SKIP_OPTIONAL" = 1 ] && [ "$required" = 0 ] && continue
  dest="$TARBALL_DIR/$name"
  if [ -f "$dest" ] && verify_sha "$dest" "$sha"; then
    info "Đã có và khớp SHA-256: $name"
  else
    info "Tải $name ($((size / 1048576)) MB)"
    curl -fsSL --retry 3 --connect-timeout 20 -o "$dest.part" "$BASE_URL/$name"
    actual_size="$(stat -f %z "$dest.part")"
    [ "$actual_size" = "$size" ] || { rm -f "$dest.part"; die "$name: kích thước $actual_size, mong đợi $size."; }
    verify_sha "$dest.part" "$sha" || { rm -f "$dest.part"; die "$name: SHA-256 không khớp với lock."; }
    mv "$dest.part" "$dest"
  fi
  if [ "$HAVE_SQV" = 1 ]; then
    curl -fsSL --retry 3 -o "$dest.asc" "$BASE_URL/$name.asc"
    signer="$("$SQV" --keyring "$KEYRING" "$dest.asc" "$dest" 2>/dev/null || true)"
    [ "$signer" = "$FPR" ] || die "$name: chữ ký không hợp lệ hoặc không phải của khoá $FPR."
    info "Chữ ký OpenPGP hợp lệ: $name"
  fi
done <<< "$ENTRIES"

info "Xong. Tarball ở $TARBALL_DIR"
