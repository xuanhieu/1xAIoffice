#!/usr/bin/env bash
# SPDX-License-Identifier: MPL-2.0
# Regenerate types/onexvn-tools.rdb from idl/ with unoidl-write from a 1xAIoffice build (SDK is built with the app).
# Usage: tools/build_rdb.sh <instdir>   e.g. $ONEX_WORK/src/libreoffice-26.8.3.1/instdir
set -euo pipefail
INST="${1:?instdir}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
APP="$(ls -d "$INST"/*.app | head -1)"
SDK="$(ls -d "$INST"/*_SDK | head -1)"
DYLD_LIBRARY_PATH="$APP/Contents/Frameworks" "$SDK/bin/unoidl-write" \
  "$APP/Contents/Resources/ure/share/misc/types.rdb" "$APP/Contents/Resources/types/offapi.rdb" \
  "$HERE/idl" "$HERE/types/onexvn-tools.rdb"
echo "types/onexvn-tools.rdb ($(wc -c < "$HERE/types/onexvn-tools.rdb") byte)"
