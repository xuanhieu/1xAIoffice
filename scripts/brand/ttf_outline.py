# SPDX-License-Identifier: MPL-2.0
"""Đổi một dòng chữ thành đường SVG từ font TrueType (bảng glyf), thuần Python, không cần fontTools.

Dùng cho wordmark để logo hiện giống nhau trên mọi máy (trình vẽ SVG của upstream không chắc có font).
Hỗ trợ cmap format 4, glyph đơn và glyph ghép (chỉ dịch chuyển), không kerning.
"""
import struct


class Font:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        n = struct.unpack(">H", self.data[4:6])[0]
        self.tables = {}
        for i in range(n):
            tag, _, off, length = struct.unpack(">4sIII", self.data[12 + 16 * i:28 + 16 * i])
            self.tables[tag.decode("latin-1")] = (off, length)
        head = self._t("head")
        self.upm = struct.unpack(">H", self.data[head + 18:head + 20])[0]
        self.loca_long = struct.unpack(">h", self.data[head + 50:head + 52])[0] == 1
        maxp = self._t("maxp")
        self.num_glyphs = struct.unpack(">H", self.data[maxp + 4:maxp + 6])[0]
        hhea = self._t("hhea")
        self.ascent, self.descent = struct.unpack(">hh", self.data[hhea + 4:hhea + 8])
        self.num_hm = struct.unpack(">H", self.data[hhea + 34:hhea + 36])[0]
        self.cmap = self._cmap()

    def _t(self, tag):
        return self.tables[tag][0]

    def _cmap(self):
        base = self._t("cmap")
        n = struct.unpack(">H", self.data[base + 2:base + 4])[0]
        for i in range(n):
            pid, eid, off = struct.unpack(">HHI", self.data[base + 4 + 8 * i:base + 12 + 8 * i])
            sub = base + off
            if struct.unpack(">H", self.data[sub:sub + 2])[0] == 4 and pid in (0, 3):
                return self._cmap4(sub)
        raise ValueError("font không có cmap format 4")

    def _cmap4(self, sub):
        d = self.data
        segx2 = struct.unpack(">H", d[sub + 6:sub + 8])[0]
        ends = sub + 14
        starts = ends + segx2 + 2
        deltas = starts + segx2
        ranges = deltas + segx2
        out = {}
        for s in range(segx2 // 2):
            end, start = struct.unpack(">H", d[ends + 2 * s:ends + 2 * s + 2])[0], \
                struct.unpack(">H", d[starts + 2 * s:starts + 2 * s + 2])[0]
            delta = struct.unpack(">h", d[deltas + 2 * s:deltas + 2 * s + 2])[0]
            ro_pos = ranges + 2 * s
            ro = struct.unpack(">H", d[ro_pos:ro_pos + 2])[0]
            for c in range(start, min(end, 0xFFFE) + 1):
                if ro == 0:
                    g = (c + delta) & 0xFFFF
                else:
                    p = ro_pos + ro + 2 * (c - start)
                    g = struct.unpack(">H", d[p:p + 2])[0]
                    g = (g + delta) & 0xFFFF if g else 0
                out[c] = g
        return out

    def advance(self, gid):
        hmtx = self._t("hmtx")
        i = min(gid, self.num_hm - 1)
        return struct.unpack(">H", self.data[hmtx + 4 * i:hmtx + 4 * i + 2])[0]

    def _glyph_range(self, gid):
        loca = self._t("loca")
        if self.loca_long:
            a, b = struct.unpack(">II", self.data[loca + 4 * gid:loca + 4 * gid + 8])
        else:
            a, b = (x * 2 for x in struct.unpack(">HH", self.data[loca + 2 * gid:loca + 2 * gid + 4]))
        return self._t("glyf") + a, b - a

    def contours(self, gid, dx=0, dy=0):
        """Danh sách contour, mỗi contour là list (x, y, on_curve)."""
        off, length = self._glyph_range(gid)
        if length == 0:
            return []
        d = self.data
        nc = struct.unpack(">h", d[off:off + 2])[0]
        p = off + 10
        if nc < 0:  # glyph ghép
            out = []
            while True:
                flags, sub = struct.unpack(">HH", d[p:p + 4])
                p += 4
                if flags & 1:
                    a1, a2 = struct.unpack(">hh", d[p:p + 4]); p += 4
                else:
                    a1, a2 = struct.unpack(">bb", d[p:p + 2]); p += 2
                if flags & 0x8: p += 2
                elif flags & 0x40: p += 4
                elif flags & 0x80: p += 8
                out += self.contours(sub, dx + a1, dy + a2)
                if not flags & 0x20:
                    return out
        ends = struct.unpack(">%dH" % nc, d[p:p + 2 * nc]); p += 2 * nc
        ilen = struct.unpack(">H", d[p:p + 2])[0]; p += 2 + ilen
        npts = ends[-1] + 1
        flags = []
        while len(flags) < npts:
            f = d[p]; p += 1
            flags.append(f)
            if f & 8:
                r = d[p]; p += 1
                flags += [f] * r
        def coords(short_bit, same_bit):
            nonlocal p
            vals, v = [], 0
            for f in flags:
                if f & short_bit:
                    delta = d[p]; p += 1
                    v += delta if f & same_bit else -delta
                elif not f & same_bit:
                    v += struct.unpack(">h", d[p:p + 2])[0]; p += 2
                vals.append(v)
            return vals
        xs, ys = coords(2, 16), coords(4, 32)
        out, start = [], 0
        for e in ends:
            out.append([(xs[i] + dx, ys[i] + dy, bool(flags[i] & 1)) for i in range(start, e + 1)])
            start = e + 1
        return out


def _contour_path(pts, tf):
    if not pts:
        return ""
    # Bắt đầu từ một điểm on-curve (hoặc trung điểm nếu không có).
    if not pts[0][2]:
        if pts[-1][2]:
            pts = [pts[-1]] + pts[:-1]
        else:
            m = ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2, True)
            pts = [m] + pts
    x0, y0 = tf(pts[0][0], pts[0][1])
    s = [f"M{x0:.1f} {y0:.1f}"]
    i, n = 1, len(pts)
    seq = pts[1:] + [pts[0]]
    prev_off = None
    for x, y, on in seq:
        if on:
            X, Y = tf(x, y)
            if prev_off:
                cx, cy = tf(*prev_off)
                s.append(f"Q{cx:.1f} {cy:.1f} {X:.1f} {Y:.1f}")
            else:
                s.append(f"L{X:.1f} {Y:.1f}")
            prev_off = None
        else:
            if prev_off:
                mx, my = (prev_off[0] + x) / 2, (prev_off[1] + y) / 2
                cx, cy = tf(*prev_off)
                X, Y = tf(mx, my)
                s.append(f"Q{cx:.1f} {cy:.1f} {X:.1f} {Y:.1f}")
            prev_off = (x, y)
    s.append("Z")
    return "".join(s)


def text_path(font, text, size, x=0.0, baseline=0.0, tracking=0.0):
    """Trả về (chuỗi d của path SVG, bề rộng) cho `text` cỡ `size` px đặt ở (x, baseline)."""
    scale = size / font.upm
    parts, pen = [], 0.0
    for ch in text:
        gid = font.cmap.get(ord(ch), 0)
        ox = x + pen * scale
        tf = lambda gx, gy, ox=ox: (ox + gx * scale, baseline - gy * scale)
        for c in font.contours(gid):
            parts.append(_contour_path(c, tf))
        pen += font.advance(gid) + tracking * font.upm
    return "".join(parts), pen * scale
