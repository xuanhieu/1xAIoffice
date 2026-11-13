#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Sinh data/tcvn3.json từ bảng mã TCVN 5712:1993 của glibc (data/sources/glibc-TCVN5712-1.charmap).

Văn bản gõ bằng phông TCVN3 (.VnTime, .VnArial…) được Word và LibreOffice đọc như ký tự Windows-1252 của từng byte.
Vì vậy khoá của bảng là ký tự cp1252 ứng với byte (byte cp1252 không định nghĩa thì dùng Latin-1), giá trị là ký tự
Unicode mà TCVN 5712 gán cho byte đó. Chỉ lấy byte 0x80–0xFF: phông TCVN3 để nguyên vùng ASCII, còn vùng điều khiển
0x01–0x17 (chữ hoa có dấu của bản VN1) không gõ được trong phông TCVN3.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / "data/sources/glibc-TCVN5712-1.charmap"
OUT = HERE / "data/tcvn3.json"
LINE = re.compile(r"^<U([0-9A-F]{4,6})>\s+/x([0-9a-f]{2})\s")


def legacy_char(byte):
    try:
        return bytes([byte]).decode("cp1252")
    except UnicodeDecodeError:
        return bytes([byte]).decode("latin-1")


def main():
    table = {}
    for line in SRC.read_text(encoding="utf-8").splitlines():
        m = LINE.match(line)
        if not m:
            continue
        byte, uni = int(m.group(2), 16), chr(int(m.group(1), 16))
        if byte >= 0x80:
            key = legacy_char(byte)
            if key != uni:
                table[key] = uni
    OUT.write_text(json.dumps(dict(sorted(table.items())), ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"{len(table)} ký tự -> {OUT}")


if __name__ == "__main__":
    main()
