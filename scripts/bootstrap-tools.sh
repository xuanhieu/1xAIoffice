#!/usr/bin/env bash
# Install every build tool into a private Homebrew on the SSD ($ONEX_BREW), leaving /opt/homebrew and the
# internal disk untouched. Safe to rerun: already installed formulae are skipped.
# Usage: scripts/bootstrap-tools.sh
set -euo pipefail
# shellcheck source=scripts/env.sh
source "$(dirname "$0")/env.sh"

FORMULAE="autoconf automake m4 bison gperf ninja make nasm pkgconf gettext sequoia-sqv"
# sqv verifies the OpenPGP signatures of the source tarballs. gnupg is not used: its test suite fails on the SSD
# because the socket path under the Homebrew temp folder is longer than macOS allows.
# ccache comes as the official prebuilt binary: outside /opt/homebrew, Homebrew would build LLVM from source for it.
CCACHE_VERSION="4.14.3"
CCACHE_SHA256="764dd2a8100ff83e6bbd7b9a1e2016cc401be34bee8a70ea99698186622c34d5"

require_work_volume
case "$ONEX_BREW" in /Volumes/*) ;; *) die "ONEX_BREW phải nằm trên ổ ngoài (/Volumes/...), hiện là $ONEX_BREW." ;; esac

if [ ! -x "$ONEX_BREW/bin/brew" ]; then
  info "Tạo Homebrew riêng tại $ONEX_BREW"
  git clone --depth 1 https://github.com/Homebrew/brew "$ONEX_BREW"
fi

# Cache and temp on the SSD too; no analytics, no automatic update of the shared /opt/homebrew.
export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_INSTALL_CLEANUP=1
export HOMEBREW_CACHE="$ONEX_BREW/.cache" HOMEBREW_TEMP="$ONEX_BREW/.tmp" HOMEBREW_LOGS="$ONEX_BREW/.logs"
mkdir -p "$HOMEBREW_CACHE" "$HOMEBREW_TEMP" "$HOMEBREW_LOGS"

# A prefix other than /opt/homebrew is Homebrew's "Tier 3": relocatable bottles are poured, the rest
# (make, pkgconf, gettext...) build from source. The first run takes 10-20 minutes.
info "Cài: $FORMULAE"
# shellcheck disable=SC2086
"$ONEX_BREW/bin/brew" install $FORMULAE

if [ "$("$ONEX_TOOLS/bin/ccache" --version 2>/dev/null | head -1)" != "ccache version $CCACHE_VERSION" ]; then
  info "Cài ccache $CCACHE_VERSION (bản dựng sẵn chính thức)"
  mkdir -p "$ONEX_TOOLS/bin" "$ONEX_TOOLS/dl"
  archive="$ONEX_TOOLS/dl/ccache-$CCACHE_VERSION-darwin.tar.gz"
  curl -fsSL -o "$archive" "https://github.com/ccache/ccache/releases/download/v$CCACHE_VERSION/ccache-$CCACHE_VERSION-darwin.tar.gz"
  [ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$CCACHE_SHA256" ] || die "ccache: SHA-256 không khớp."
  tar -xzf "$archive" -C "$ONEX_TOOLS/dl"
  cp "$ONEX_TOOLS/dl/ccache-$CCACHE_VERSION-darwin/ccache" "$ONEX_TOOLS/bin/ccache"
fi

# ShellCheck comes as the official prebuilt binary (the Homebrew formula would need the Haskell toolchain outside /opt/homebrew).
SHELLCHECK_VERSION="0.11.0"
SHELLCHECK_SHA256="339b930feb1ea764467013cc1f72d09cd6b869ebf1013296ba9055ab2ffbd26f"
if ! "$ONEX_TOOLS/bin/shellcheck" --version 2>/dev/null | grep -q "version: $SHELLCHECK_VERSION"; then
  info "Cài shellcheck $SHELLCHECK_VERSION (bản dựng sẵn chính thức)"
  mkdir -p "$ONEX_TOOLS/bin" "$ONEX_TOOLS/dl"
  archive="$ONEX_TOOLS/dl/shellcheck-v$SHELLCHECK_VERSION.darwin.aarch64.tar.gz"
  curl -fsSL -o "$archive" "https://github.com/koalaman/shellcheck/releases/download/v$SHELLCHECK_VERSION/shellcheck-v$SHELLCHECK_VERSION.darwin.aarch64.tar.gz"
  [ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$SHELLCHECK_SHA256" ] || die "shellcheck: SHA-256 không khớp."
  tar -xzf "$archive" -C "$ONEX_TOOLS/dl"
  cp "$ONEX_TOOLS/dl/shellcheck-v$SHELLCHECK_VERSION/shellcheck" "$ONEX_TOOLS/bin/shellcheck"
fi

info "Xong. Công cụ ở $ONEX_BREW/bin; đĩa dùng: $(du -sh "$ONEX_BREW" | cut -f1)"
