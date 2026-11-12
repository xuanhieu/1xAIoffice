#!/usr/bin/env bash
# Build 1xVnOffice for macOS from the locked LibreOffice tarballs.
# Usage: scripts/build-macos.sh <step>...   steps: preflight extract patch l10n configure build config sign smoke defaults all
set -euo pipefail
# shellcheck source=scripts/env.sh
source "$(dirname "$0")/env.sh"

MIN_FREE_GIB=80
NCPU="$(sysctl -n hw.ncpu)"
STAMP="$(date +%Y%m%d-%H%M%S)"
# configure and make run with a clean PATH: system directories plus a private folder that links only the tools the
# build needs. The tools come from a private Homebrew on the SSD (scripts/bootstrap-tools.sh), never /opt/homebrew,
# so nothing is installed on the internal disk. "make" there is GNU make >= 4.2 (macOS ships 3.81).
TOOLBIN="$ONEX_WORK/toolbin"
BREW_PREFIX="$ONEX_BREW"
BUILD_TOOLS="autoconf autoheader autom4te autoreconf autoscan autoupdate ifnames automake aclocal nasm gperf ninja"
# GNU gettext (msgfmt and friends) for the Vietnamese UI translations.
KEG_TOOLS_GETTEXT="gettext/bin/msgfmt gettext/bin/msgunfmt gettext/bin/msgcat gettext/bin/msguniq gettext/bin/xgettext"
# meson is deliberately left out: Homebrew meson needs its own Python, while configure runs it with
# /usr/bin/python3; without it, LibreOffice uses its bundled meson (only ninja is required).
# Keg-only formulae (not linked into bin/): macOS ships bison 2.3, too old for LibreOffice.
# flex is NOT taken from Homebrew: flex 2.6.10 generates code that breaks connectivity/source/parse/sqlflex.l
# ("use of undeclared identifier yy_fatal_error"); the system /usr/bin/flex 2.6.4 works.
KEG_TOOLS="$KEG_TOOLS_GETTEXT bison/bin/bison bison/bin/yacc"

setup_toolbin() {
  mkdir -p "$TOOLBIN"
  rm -f "$TOOLBIN"/*
  for t in $BUILD_TOOLS; do
    if [ -x "$BREW_PREFIX/bin/$t" ]; then ln -s "$BREW_PREFIX/bin/$t" "$TOOLBIN/$t"; fi
  done
  for k in $KEG_TOOLS; do
    if [ -x "$BREW_PREFIX/opt/$k" ]; then ln -s "$BREW_PREFIX/opt/$k" "$TOOLBIN/$(basename "$k")"; fi
  done
  # ccache: official prebuilt binary from scripts/bootstrap-tools.sh.
  if [ -x "$ONEX_TOOLS/bin/ccache" ]; then ln -s "$ONEX_TOOLS/bin/ccache" "$TOOLBIN/ccache"; fi
  [ -x "$BREW_PREFIX/opt/make/libexec/gnubin/make" ] || die "Thiếu GNU make (brew install make)."
  ln -s "$BREW_PREFIX/opt/make/libexec/gnubin/make" "$TOOLBIN/make"
  PATH="$TOOLBIN:/usr/bin:/bin:/usr/sbin:/sbin"
  # An empty default search directory keeps Homebrew libraries out of the build; the bundled libraries still use
  # their own PKG_CONFIG_PATH.
  mkdir -p "$ONEX_WORK/empty-pkgconfig"
  PKG_CONFIG_LIBDIR="$ONEX_WORK/empty-pkgconfig"
  export PATH PKG_CONFIG_LIBDIR
  MAKE_BIN="$TOOLBIN/make"
}
MAKE_BIN=""

step_preflight() {
  [ "$(uname -s)" = Darwin ] || die "Script này chỉ cho macOS."
  require_work_volume
  local free; free="$(free_gib "$ONEX_WORK")"
  [ "$free" -ge "$MIN_FREE_GIB" ] || die "Cần ≥ $MIN_FREE_GIB GiB trống trên $ONEX_WORK, hiện có $free GiB."
  xcode-select -p >/dev/null 2>&1 || die "Chưa có Xcode hoặc Command Line Tools."
  local missing=()
  for tool in autoconf automake nasm gmake gperf ninja pkg-config; do
    [ -x "$BREW_PREFIX/bin/$tool" ] || missing+=("$tool")
  done
  [ -x "$ONEX_TOOLS/bin/ccache" ] || warn "Chưa có ccache: build lại sẽ chậm (scripts/bootstrap-tools.sh)."
  [ ${#missing[@]} -eq 0 ] || die "Thiếu công cụ trong $BREW_PREFIX: ${missing[*]}. Chạy scripts/bootstrap-tools.sh"
  info "Máy: $(sysctl -n machdep.cpu.brand_string), $NCPU nhân, $(( $(sysctl -n hw.memsize) / 1073741824 )) GiB RAM; trống $free GiB trên $ONEX_WORK"
  setup_toolbin
  info "make: $MAKE_BIN ($("$MAKE_BIN" --version | head -1)); PATH sạch: $PATH"
}

step_extract() {
  local marker="$SRC_DIR/.1x-extracted"
  if [ -f "$marker" ]; then info "Đã giải nén: $SRC_DIR"; return; fi
  mkdir -p "$ONEX_WORK/src"
  for name in $(lock_get "' '.join(t['name'] for t in L['tarballs'])"); do
    local file="$TARBALL_DIR/$name"
    if [ ! -f "$file" ]; then
      case "$name" in *help*) warn "Không có $name, bỏ qua (tuỳ chọn)."; continue ;; esac
      die "Thiếu $file. Chạy scripts/fetch-source.sh trước."
    fi
    info "Giải nén $name"
    tar -xf "$file" -C "$ONEX_WORK/src"
  done
  touch "$marker"
}

step_patch() {
  local series="$REPO_ROOT/patches/libreoffice/series" marker="$SRC_DIR/.1x-patched"
  [ -d "$SRC_DIR" ] || die "Chưa có mã nguồn; chạy bước extract."
  : > "$marker.new"
  while IFS= read -r p; do
    case "$p" in ''|'#'*) continue ;; esac
    if grep -qxF "$p" "$marker" 2>/dev/null; then info "Đã áp: $p"; echo "$p" >> "$marker.new"; continue; fi
    info "Áp bản vá $p"
    patch -d "$SRC_DIR" -p1 --forward --batch -i "$REPO_ROOT/patches/libreoffice/$p"
    echo "$p" >> "$marker.new"
  done < "$series"
  mv "$marker.new" "$marker"
}

step_l10n() {
  # Merge the 1xVnOffice translation layer (l10n/) into the LibreOffice translations before building.
  [ -d "$SRC_DIR/translations/source" ] || die "Chưa có bản dịch; chạy bước extract."
  python3 "$REPO_ROOT/scripts/l10n-merge.py" --src "$SRC_DIR" --lang vi --strict
  # gbuild's MoTarget does not depend on its .po file, so a changed translation is never recompiled on its own.
  # Remove the compiled catalogue of every module the layer touches; make rebuilds and reinstalls it.
  local po_file module
  while IFS= read -r po_file; do
    module="$(basename "$(dirname "$po_file")")"
    rm -f "$SRC_DIR/workdir/MoTarget/${module}vi.mo"
  done < <(find "$REPO_ROOT/l10n/vi" -name messages.po)
}

step_configure() {
  setup_toolbin
  [ -d "$SRC_DIR" ] || die "Chưa có mã nguồn; chạy bước extract."
  {
    grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$REPO_ROOT/build-config/macos.conf"
    echo "--with-parallelism=$NCPU"
    echo "--with-external-tar=$EXTERNAL_TAR_DIR"
    # pkgconf is needed by the bundled meson to build harfbuzz. configure trusts a Homebrew pkg-config only at
    # /opt/homebrew/bin, or when it lists no packages; pkgconf >= 2 always lists its two virtual packages, so the
    # check is approved explicitly. PKG_CONFIG_LIBDIR (setup_toolbin) is empty, so no Homebrew library leaks in.
    echo "PKG_CONFIG=$BREW_PREFIX/bin/pkg-config"
    echo "--enable-bogus-pkg-config"
  } > "$SRC_DIR/autogen.input"
  info "autogen.input:"; sed 's/^/    /' "$SRC_DIR/autogen.input"
  (cd "$SRC_DIR" && ./autogen.sh) 2>&1 | tee "$LOG_DIR/configure-$STAMP.log"
}

step_build() {
  setup_toolbin
  [ -f "$SRC_DIR/config_host.mk" ] || die "Chưa configure."
  info "Bắt đầu build (log: $LOG_DIR/build-$STAMP.log). Lần đầu mất vài giờ."
  (cd "$SRC_DIR" && "$MAKE_BIN") 2>&1 | tee "$LOG_DIR/build-$STAMP.log"
}

# The bundle is named after the product (1xVnOffice.app); the newest one wins if an older name is still there.
# shellcheck disable=SC2012 # bundle names are fixed product names without spaces
app_path() { ls -dt "$SRC_DIR"/instdir/*.app 2>/dev/null | head -1; }

step_config() {
  local app; app="$(app_path)"; [ -n "$app" ] || die "Không thấy .app trong instdir."
  local dest="$app/Contents/Resources/registry"
  [ -d "$dest" ] || die "Không thấy thư mục registry trong $app."
  for f in "$REPO_ROOT"/config/*.xcd; do
    info "Cài cấu hình mặc định $(basename "$f")"
    cp "$f" "$dest/"
  done
}

step_sign() {
  local app; app="$(app_path)"; [ -n "$app" ] || die "Không thấy .app trong instdir."
  # Ad-hoc signature: enough to run on Apple Silicon. Developer ID and notarization come once there is revenue.
  info "Ký ad-hoc $app"
  codesign --force --deep --sign - "$app"
  codesign --verify --deep --strict "$app" && info "Chữ ký ad-hoc hợp lệ."
}

step_smoke() {
  local app; app="$(app_path)"; [ -n "$app" ] || die "Không thấy .app trong instdir."
  local tmp; tmp="$(mktemp -d "$ONEX_WORK/smoke.XXXXXX")"
  printf 'Xin chào 1xVnOffice — kiểm tra tiếng Việt: ăâđêôơư ẮẰẲẴẶ\n' > "$tmp/smoke.txt"
  "$app/Contents/MacOS/soffice" --headless -env:UserInstallation="file://$tmp/profile" \
    --convert-to pdf --outdir "$tmp" "$tmp/smoke.txt" >/dev/null 2>&1
  [ -s "$tmp/smoke.pdf" ] || die "Smoke test thất bại: không tạo được PDF."
  info "Smoke test đạt: $tmp/smoke.pdf"
}

step_defaults() {
  # Start a headless office with a fresh profile and check that config/1x-defaults.xcd took effect.
  local app; app="$(app_path)"; [ -n "$app" ] || die "Không thấy .app trong instdir."
  local profile; profile="$(mktemp -d "$ONEX_WORK/profile.XXXXXX")"
  local pipe="onex_defaults_$$"
  "$app/Contents/MacOS/soffice" --headless --norestore -env:UserInstallation="file://$profile" \
    "--accept=pipe,name=$pipe;urp;" >/dev/null 2>&1 &
  local pid=$!
  local rc=0
  "$app/Contents/Resources/python" "$REPO_ROOT/scripts/check-defaults.py" "$pipe" || rc=$?
  sleep 2; kill "$pid" 2>/dev/null || true
  rm -rf "$profile"
  [ "$rc" = 0 ] || die "Cấu hình mặc định chưa có hiệu lực."
  info "Cấu hình mặc định có hiệu lực."
}

[ $# -gt 0 ] || die "Cần ít nhất một bước: preflight extract patch l10n configure build config sign smoke defaults all"
for s in "$@"; do
  case "$s" in
    all) step_preflight; step_extract; step_patch; step_l10n; step_configure; step_build; step_config; step_sign; step_smoke; step_defaults ;;
    preflight|extract|patch|l10n|configure|build|config|sign|smoke|defaults) "step_$s" ;;
    *) die "Bước lạ: $s" ;;
  esac
done
