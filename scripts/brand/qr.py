# SPDX-License-Identifier: MPL-2.0
"""Vẽ mã QR (chế độ byte, phiên bản 1–10, mức sửa lỗi L/M) bằng Python thuần, không cần thư viện ngoài.

Đủ cho mã VietQR của 1xVnOffice (khoảng 110 byte, vừa phiên bản 7). Chuỗi dài hơn sức chứa phiên bản 10 thì báo lỗi
thay vì vẽ sai. Theo ISO/IEC 18004.

Mã vẽ ra LUÔN được kiểm bằng cách giải mã lại ảnh thật (scripts/brand/check-vietqr.sh): một mã QR sai sẽ đưa tiền đi
đâu không biết, nên không bao giờ phát hành mã chưa giải mã lại được đúng chuỗi gốc.
"""

# Tổng số từ mã (dữ liệu + sửa lỗi) của từng phiên bản.
TOTAL_CODEWORDS = {1: 26, 2: 44, 3: 70, 4: 100, 5: 134, 6: 172, 7: 196, 8: 242, 9: 292, 10: 346}
# phiên bản -> mức -> (số từ mã sửa lỗi mỗi khối, [(số khối, số từ mã dữ liệu mỗi khối), ...])
ECC = {
    1: {"L": (7, [(1, 19)]), "M": (10, [(1, 16)])},
    2: {"L": (10, [(1, 34)]), "M": (16, [(1, 28)])},
    3: {"L": (15, [(1, 55)]), "M": (26, [(1, 44)])},
    4: {"L": (20, [(1, 80)]), "M": (18, [(2, 32)])},
    5: {"L": (26, [(1, 108)]), "M": (24, [(2, 43)])},
    6: {"L": (18, [(2, 68)]), "M": (16, [(4, 27)])},
    7: {"L": (20, [(2, 78)]), "M": (18, [(4, 31)])},
    8: {"L": (24, [(2, 97)]), "M": (22, [(2, 38), (2, 39)])},
    9: {"L": (30, [(2, 116)]), "M": (22, [(3, 36), (2, 37)])},
    10: {"L": (18, [(2, 68), (2, 69)]), "M": (26, [(4, 43), (1, 44)])},
}
# Toạ độ tâm các ô định vị phụ (alignment) theo phiên bản.
ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
         7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
ECL_BITS = {"L": 1, "M": 0}
MASKS = (lambda x, y: (x + y) % 2 == 0,
         lambda x, y: y % 2 == 0,
         lambda x, y: x % 3 == 0,
         lambda x, y: (x + y) % 3 == 0,
         lambda x, y: (x // 3 + y // 2) % 2 == 0,
         lambda x, y: x * y % 2 + x * y % 3 == 0,
         lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
         lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0)

for _v, _levels in ECC.items():  # bảng tự kiểm: tổng từ mã phải khớp
    for _l, (_ec, _groups) in _levels.items():
        assert sum(c * (d + _ec) for c, d in _groups) == TOTAL_CODEWORDS[_v], f"bảng sai ở {_v}{_l}"

# --- GF(256), đa thức 0x11D ---
_EXP, _LOG, _x = [0] * 512, [0] * 256, 1
for _i in range(255):
    _EXP[_i], _LOG[_x] = _x, _i
    _x = (_x << 1) ^ (0x11D if _x & 0x80 else 0)
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _poly_mul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] ^= _mul(x, y)
    return out


def _ecc_words(data, n):
    """n từ mã sửa lỗi Reed–Solomon cho khối `data`."""
    gen = [1]
    for i in range(n):
        gen = _poly_mul(gen, [1, _EXP[i]])
    rem = list(data) + [0] * n
    for i in range(len(data)):
        factor = rem[i]
        if factor:
            for j, g in enumerate(gen):
                rem[i + j] ^= _mul(g, factor)
    return rem[len(data):]


def _data_capacity(version, level):
    return sum(count * size for count, size in ECC[version][level][1])


def choose_version(length, level):
    """Phiên bản nhỏ nhất chứa được `length` byte ở mức `level`."""
    for version in sorted(ECC):
        count_bits = 8 if version < 10 else 16
        if 4 + count_bits + length * 8 <= _data_capacity(version, level) * 8:
            return version
    raise ValueError(f"chuỗi dài {length} byte, vượt sức chứa phiên bản 10 mức {level}")


def _codewords(data, version, level):
    """Chuỗi từ mã đã thêm sửa lỗi và xen kẽ theo khối."""
    ec_count, groups = ECC[version][level]
    count_bits = 8 if version < 10 else 16
    total = _data_capacity(version, level)
    bits = f"0100{len(data):0{count_bits}b}" + "".join(f"{b:08b}" for b in data)
    bits += "0" * min(4, total * 8 - len(bits))   # dấu kết thúc
    bits += "0" * (-len(bits) % 8)                # cho tròn byte
    words = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    for k in range(total - len(words)):           # byte đệm xen kẽ 0xEC, 0x11
        words.append(0xEC if k % 2 == 0 else 0x11)
    blocks, pos = [], 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(words[pos:pos + size])
            pos += size
    eccs = [_ecc_words(b, ec_count) for b in blocks]
    out = []
    for i in range(max(len(b) for b in blocks)):
        out += [b[i] for b in blocks if i < len(b)]
    for i in range(ec_count):
        out += [e[i] for e in eccs]
    return out


def _bch(data, generator, steps):
    """Phần dư BCH của `data` dịch trái `steps` bit, chia cho `generator` (dùng cho thông tin định dạng và phiên bản)."""
    rem = data
    width = generator.bit_length() - 1
    for _ in range(steps):
        rem = (rem << 1) ^ ((rem >> (width - 1)) * generator)
    return rem & ((1 << width) - 1)


class _Code:
    def __init__(self, version, level):
        self.version, self.level = version, level
        self.size = n = version * 4 + 17
        self.cells = [[False] * n for _ in range(n)]
        self.fixed = [[False] * n for _ in range(n)]
        self._functions()

    def _put(self, x, y, value):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.cells[y][x] = value
            self.fixed[y][x] = True

    def _functions(self):
        n = self.size
        for i in range(n):                                   # hàng và cột định thì
            self._put(6, i, i % 2 == 0)
            self._put(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):      # ô định vị và viền trắng
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    dist = max(abs(dx), abs(dy))
                    self._put(cx + dx, cy + dy, dist != 2 and dist != 4)
        centers = ALIGN[self.version]
        for cy in centers:                                   # ô định vị phụ
            for cx in centers:
                if (cx, cy) in ((6, 6), (6, n - 7), (n - 7, 6)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self._put(cx + dx, cy + dy, max(abs(dx), abs(dy)) != 1)
        self._format(0)                                      # giữ chỗ cho thông tin định dạng
        self._version_info()

    def _format(self, mask):
        n = self.size
        data = (ECL_BITS[self.level] << 3) | mask
        bits = ((data << 10) | _bch(data, 0x537, 10)) ^ 0x5412
        def bit(i):
            return (bits >> i) & 1 == 1
        for i in range(6):
            self._put(8, i, bit(i))
        self._put(8, 7, bit(6))
        self._put(8, 8, bit(7))
        self._put(7, 8, bit(8))
        for i in range(9, 15):
            self._put(14 - i, 8, bit(i))
        for i in range(8):
            self._put(n - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self._put(8, n - 15 + i, bit(i))
        self._put(8, n - 8, True)                            # ô tối cố định

    def _version_info(self):
        if self.version < 7:
            return
        n = self.size
        bits = (self.version << 12) | _bch(self.version, 0x1F25, 12)
        for i in range(18):
            value = (bits >> i) & 1 == 1
            self._put(n - 11 + i % 3, i // 3, value)
            self._put(i // 3, n - 11 + i % 3, value)

    def place(self, words):
        bits = "".join(f"{w:08b}" for w in words)
        i, n = 0, self.size
        right = n - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(n):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = n - 1 - vert if upward else vert
                    if not self.fixed[y][x] and i < len(bits):
                        self.cells[y][x] = bits[i] == "1"
                        i += 1
            right -= 2

    def masked(self, mask):
        rule = MASKS[mask]
        out = [[self.cells[y][x] != (not self.fixed[y][x] and rule(x, y)) for x in range(self.size)]
               for y in range(self.size)]
        saved = [row[:] for row in self.cells]
        self._format(mask)                                   # thông tin định dạng theo đúng mặt nạ
        for y in range(self.size):
            for x in range(self.size):
                if self.fixed[y][x]:
                    out[y][x] = self.cells[y][x]
        self.cells = saved
        return out


def _penalty(m):
    n = len(m)
    score = 0
    lines = list(m) + [[m[y][x] for y in range(n)] for x in range(n)]
    for line in lines:
        run, prev = 1, line[0]
        for cell in line[1:]:
            run = run + 1 if cell == prev else 1
            prev = cell
            if run == 5:
                score += 3
            elif run > 5:
                score += 1
        text = "".join("1" if c else "0" for c in line)
        score += 40 * (text.count("10111010000") + text.count("00001011101"))
    for y in range(n - 1):
        for x in range(n - 1):
            if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                score += 3
    dark = sum(sum(1 for c in row if c) for row in m)
    return score + 10 * (abs(dark * 100 // (n * n) - 50) // 5)


def matrix(text, level="M"):
    """Ma trận True/False của mã QR cho `text`, chưa kèm viền trắng."""
    data = text.encode("utf-8")
    code = _Code(choose_version(len(data), level), level)
    code.place(_codewords(data, code.version, level))
    return min((_penalty(code.masked(k)), k, code.masked(k)) for k in range(8))[2]


def svg(text, level="M", size=256, quiet=4, dark="#111318", light="#FFFFFF"):
    """Mã QR dạng SVG vuông `size` px, viền trắng `quiet` ô."""
    m = matrix(text, level)
    n = len(m) + quiet * 2
    rects = "".join(f'<rect x="{x + quiet}" y="{y + quiet}" width="1" height="1"/>'
                    for y, row in enumerate(m) for x, cell in enumerate(row) if cell)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="{size}" height="{size}" '
            f'shape-rendering="crispEdges">\n<rect width="{n}" height="{n}" fill="{light}"/>\n'
            f'<g fill="{dark}">{rects}</g>\n</svg>\n')
