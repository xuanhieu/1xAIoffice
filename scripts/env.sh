# Shared settings for the build scripts. Source it; do not run it.
# shellcheck shell=bash
# Variables here are used by the scripts that source this file.
# shellcheck disable=SC2034

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="$REPO_ROOT/upstream/source-lock.json"

# Everything large (tarballs, source tree, ccache, logs) lives outside the repo, on the external SSD by default.
ONEX_WORK="${ONEX_WORK:-/Volumes/SSD1Tb-Black-APFS/Developer/1xvnoffice-work}"
TARBALL_DIR="$ONEX_WORK/tarballs"
EXTERNAL_TAR_DIR="$ONEX_WORK/external-tarballs"
LOG_DIR="$ONEX_WORK/logs"
export CCACHE_DIR="${CCACHE_DIR:-$ONEX_WORK/ccache}"
export CCACHE_MAXSIZE="${CCACHE_MAXSIZE:-20G}"
# Private Homebrew on the SSD that holds every build tool (see scripts/bootstrap-tools.sh).
ONEX_BREW="${ONEX_BREW:-/Volumes/SSD1Tb-Black-APFS/Developer/homebrew-1x}"
# Standalone tools that Homebrew would otherwise build from source (ccache pulls in LLVM outside /opt/homebrew).
ONEX_TOOLS="$ONEX_WORK/tools"

lock_get() {  # lock_get <python expression on the parsed lock, bound to L>
  python3 -c "import json,sys; L=json.load(open(sys.argv[1])); print($1)" "$LOCK_FILE"
}

LO_VERSION="$(lock_get "L['version']")"
SRC_DIR="$ONEX_WORK/src/libreoffice-$LO_VERSION"

die()  { printf 'Lỗi: %s\n' "$*" >&2; exit 1; }
info() { printf '==> %s\n' "$*"; }
warn() { printf 'Cảnh báo: %s\n' "$*" >&2; }

require_work_volume() {
  case "$ONEX_WORK" in
    /Volumes/*)
      local vol; vol="/Volumes/$(printf '%s' "${ONEX_WORK#/Volumes/}" | cut -d/ -f1)"
      mount | grep -q " on $vol " || die "Ổ $vol chưa gắn. Không tạo thư mục trùng tên trên ổ trong."
      ;;
  esac
  mkdir -p "$TARBALL_DIR" "$EXTERNAL_TAR_DIR" "$LOG_DIR" "$CCACHE_DIR"
}

free_gib() { df -g "$1" | awk 'NR==2 {print $4}'; }
