#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Sinh toàn bộ nhận diện 1xAIoffice từ branding/tokens.json.

Kết quả:
  branding/out/shell/{logo,logo_inverted,logo-sc,logo-sc_inverted,about}.svg   -> App/Contents/Resources/shell/
  branding/out/{intro,intro-highres}.png, main.icns                            -> App/Contents/Resources/
  branding/out/mark.svg, mark-1024.png                                         (tài liệu, trang tải)
  config/1x-theme.xcd                                                          (theme giao diện, bước "config")

Dùng: scripts/brand/make-brand.py --font <NotoSans-Bold.ttf> --font-regular <NotoSans-Regular.ttf>
PNG được vẽ bằng Chrome headless (cần --use-mock-keychain --password-store=basic để macOS không hỏi Keychain).
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ttf_outline import Font, text_path  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TOKENS = json.loads((REPO / "branding" / "tokens.json").read_text(encoding="utf-8"))
B, APPS = TOKENS["brand"], TOKENS["apps"]
OUT = REPO / "branding" / "out"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _orbit_points(cx, cy, rx, ry, rot_deg, angles_deg):
    import math
    th = math.radians(rot_deg)
    out = []
    for a in angles_deg:
        t = math.radians(a)
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * math.cos(th) - y * math.sin(th), cy + x * math.sin(th) + y * math.cos(th)))
    return out


# Hình nét trắng trên ô vệ tinh 24x24 (Doc: trang chữ, Sheet: bảng, Slide: màn chiếu).
SAT_GLYPHS = {
    "doc": '<path d="M7.5 8h9M7.5 12h9M7.5 16h5.5"/>',
    "sheet": '<rect x="6.5" y="6.5" width="11" height="11" rx="1.2"/><path d="M6.5 12h11M12 6.5v11"/>',
    "slide": '<rect x="5.5" y="7" width="13" height="8.5" rx="1.4"/><path d="M12 15.5V18.5M9 18.5h6"/>',
}


def mark_group(x, y, size, uid):
    """Biểu tượng "tất cả trong một": số 1 ở giữa, vòng quỹ đạo nghiêng và ba vệ tinh Doc (xanh dương), Sheet (xanh lá),
    Slide (cam) quay quanh. Nửa trước của vòng đi qua phía trước số 1 để có chiều sâu. Hệ toạ độ gốc 256."""
    s = size / 256
    cx, cy, rx, ry, rot = 128, 130, 96, 36, -24
    sats = _orbit_points(cx, cy, rx, ry, rot, (205, -35, 65))
    kinds = (("doc", APPS["doc"]), ("sheet", APPS["sheet"]), ("slide", APPS["slide"]))
    badges = []
    for (px, py), (key, color) in zip(sats, kinds):
        badges.append(f"""<g transform="translate({px - 17:.2f} {py - 17:.2f}) scale(1.4167)">
      <rect x="0.5" y="0.5" width="23" height="23" rx="6.5" fill="{color}" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="1.3"/>
      <g fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{SAT_GLYPHS[key]}</g>
    </g>""")
    ring = f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate({rot} {cx} {cy})" fill="none"'
    front = (f'<path d="M{cx - rx} {cy} A{rx} {ry} 0 0 0 {cx + rx} {cy}" transform="rotate({rot} {cx} {cy})" '
             f'fill="none" stroke="url(#gold{uid})" stroke-width="3.2" stroke-linecap="round"/>')
    return f"""<defs>
  <linearGradient id="ink{uid}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{B['ink_top']}"/><stop offset="1" stop-color="{B['ink_bottom']}"/>
  </linearGradient>
  <linearGradient id="gold{uid}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{B['gold']}"/><stop offset="1" stop-color="{B['gold_deep']}"/>
  </linearGradient>
</defs>
<g transform="translate({x:.2f} {y:.2f}) scale({s:.5f})">
  <rect x="0" y="0" width="256" height="256" rx="60" fill="url(#ink{uid})"/>
  <rect x="1.5" y="1.5" width="253" height="253" rx="58.5" fill="none" stroke="#FFFFFF" stroke-opacity="0.10" stroke-width="3"/>
  {ring} stroke="{B['gold']}" stroke-opacity="0.38" stroke-width="3"/>
  <path d="M104 100 L132 80 L132 188" fill="none" stroke="{B['paper']}" stroke-width="25" stroke-linecap="round" stroke-linejoin="round"/>
  {front}
  {chr(10).join(badges)}
</g>"""


def svg(w, h, body, px_w=None, px_h=None):
    size = f' width="{px_w}" height="{px_h}"' if px_w else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h:.1f}"{size}>\n{body}\n</svg>\n')


def wordmark(bold, regular, x, baseline, size, fg, accent):
    """"1x" đậm màu nhấn + "AIoffice" thường. Trả về (svg, bề rộng)."""
    d1, w1 = text_path(bold, "1x", size, x, baseline, tracking=-0.01)
    d2, w2 = text_path(regular, "AIoffice", size, x + w1 + size * 0.02, baseline, tracking=-0.005)
    return (f'<path d="{d1}" fill="{accent}"/><path d="{d2}" fill="{fg}"/>', w1 + w2 + size * 0.02)


def logo(bold, regular, dark):
    fg = B["paper"] if dark else "#1C1D22"
    accent = B["gold"] if dark else B["gold_deep"]
    h = 100
    words, ww = wordmark(bold, regular, 112, 68, 50, fg, accent)
    w = 112 + ww + 6
    return svg(w, h, mark_group(4, 8, 84, "l") + "\n" + words, f"{w * 0.72:.1f}", f"{h * 0.72:.1f}")


def about_bg():
    """Nền hộp thoại About: tấm sơn mài với vòng cung vàng mảnh, không chữ."""
    w, h = 600, 400
    body = f"""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{B['ink_top']}"/><stop offset="1" stop-color="{B['ink_bottom']}"/>
  </linearGradient>
  <linearGradient id="arc" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{B['gold']}" stop-opacity="0"/><stop offset="0.5" stop-color="{B['gold']}" stop-opacity="0.75"/>
    <stop offset="1" stop-color="{B['gold']}" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect width="{w}" height="{h}" rx="24" fill="url(#bg)"/>
<g fill="none" stroke="url(#arc)" stroke-width="1.6">
  <path d="M-40 330 C 160 210, 420 210, 640 300"/>
  <path d="M-40 352 C 170 236, 430 236, 640 324" stroke-opacity="0.55"/>
  <path d="M-40 374 C 180 262, 440 262, 640 348" stroke-opacity="0.3"/>
</g>
{mark_group(236, 70, 128, 'a')}"""
    return svg(w, h, body)


def splash(bold, regular, w, h):
    words, ww = wordmark(bold, regular, 0, 0, h * 0.22, B["paper"], B["gold"])
    mark = h * 0.34
    total = mark + h * 0.06 + ww
    x0 = (w - total) / 2
    words_x = x0 + mark + h * 0.06
    words = words.replace('<path d="', f'<path transform="translate({words_x:.1f} {h * 0.5:.1f})" d="')
    body = f"""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{B['ink_top']}"/><stop offset="1" stop-color="{B['ink_bottom']}"/>
  </linearGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#bg)"/>
{mark_group(x0, h * 0.5 - mark * 0.72, mark, 's')}
{words}"""
    return svg(w, h, body, w, h)


def icon_svg(size=1024):
    """Icon app theo lưới macOS: phần thân 824/1024, có bóng mềm."""
    pad = size * 100 / 1024
    body = f"""<defs><filter id="sh" x="-20%" y="-20%" width="140%" height="140%">
  <feDropShadow dx="0" dy="{size * 0.012:.1f}" stdDeviation="{size * 0.018:.1f}" flood-color="#000" flood-opacity="0.35"/>
</filter></defs>
<g filter="url(#sh)">{mark_group(pad, pad, size - 2 * pad, 'i')}</g>"""
    return svg(size, size, body, size, size)


GLYPHS = {  # hình vẽ nét trắng trên ô 32x32
    "doc": '<path d="M10 11h12M10 15h12M10 19h12M10 23h7"/>',
    "sheet": '<rect x="9" y="9" width="14" height="14" rx="1.5"/><path d="M9 14h14M9 18.5h14M14 9v14"/>',
    "slide": '<rect x="8.5" y="9.5" width="15" height="10" rx="1.5"/><path d="M16 19.5v3.5M12.5 23h7"/>',
    "draw": '<path d="M10 22l2.5-.6L21.5 12.4a1.8 1.8 0 0 0-2.5-2.5L10 18.9z"/><path d="M17.5 11.4l3.1 3.1"/>',
    "formula": '<path d="M8.5 17h2.5l2.5 5 4-12h6"/><path d="M18.5 15.5l4 5M22.5 15.5l-4 5"/>',
    "base": '<ellipse cx="16" cy="11" rx="6.5" ry="2.5"/><path d="M9.5 11v10c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5V11M9.5 16c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5"/>',
}
NAV = {  # icon điều hướng: nét mảnh, không ô nền
    "folder": '<path d="M5 10.5a2 2 0 0 1 2-2h5l2.5 2.5H25a2 2 0 0 1 2 2V22a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z"/>',
    "recent": '<circle cx="16" cy="16" r="10"/><path d="M16 10.5V16l3.5 2.5"/>',
    "remote": '<path d="M10 23h12.5a5 5 0 0 0 .8-9.9A7 7 0 0 0 9.8 14 4.5 4.5 0 0 0 10 23z"/>',
    "templates": '<rect x="6" y="6" width="8.5" height="8.5" rx="2"/><rect x="17.5" y="6" width="8.5" height="8.5" rx="2"/><rect x="6" y="17.5" width="8.5" height="8.5" rx="2"/><rect x="17.5" y="17.5" width="8.5" height="8.5" rx="2"/>',
}
ICON_FILES = {  # đường dẫn trong icon theme -> (kiểu, khoá)
    "res/odt_32_8.svg": ("app", "doc"), "res/ods_32_8.svg": ("app", "sheet"), "res/odp_32_8.svg": ("app", "slide"),
    "res/odg_32_8.svg": ("app", "draw"), "res/odf_32_8.svg": ("app", "formula"), "res/odb_32_8.svg": ("app", "base"),
    "framework/res/folder_32.svg": ("nav", "folder"), "framework/res/recent-documents.svg": ("nav", "recent"),
    "framework/res/remote-documents.svg": ("nav", "remote"), "framework/res/templates_32.svg": ("nav", "templates"),
}
APP_COLOR = {"doc": "doc", "sheet": "sheet", "slide": "slide", "draw": "ai", "formula": "pdf", "base": "ai"}


def icon_file(kind, key):
    if kind == "nav":
        return svg(32, 32, f'<g fill="none" stroke="#C9CCD6" stroke-width="1.8" stroke-linecap="round" '
                           f'stroke-linejoin="round">{NAV[key]}</g>', 32, 32)
    c = APPS[APP_COLOR[key]]
    return svg(32, 32, f"""<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{c}"/><stop offset="1" stop-color="{c}" stop-opacity="0.82"/></linearGradient></defs>
<rect x="2" y="2" width="28" height="28" rx="7.5" fill="url(#g)"/>
<rect x="2.5" y="2.5" width="27" height="27" rx="7" fill="none" stroke="#FFFFFF" stroke-opacity="0.18"/>
<g fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{GLYPHS[key]}</g>""",
               32, 32)


ICON_FG = "#E3E5EB"  # màu nét icon lệnh trên nền than chì
# Cỡ icon lệnh của upstream -> cỡ Fluent gần nhất (nút lớn 32px dùng bản 28px để nét không quá đậm).
CMD_SIZES = {"cmd/sc_{}.svg": 16, "cmd/lc_{}.svg": 24, "cmd/32/{}.svg": 28}


def fluent_icons(fluent_dir):
    """Icon lệnh từ Fluent UI System Icons theo branding/fluent-map.json: {tên tệp trong theme: svg}, và danh sách
    lệnh không tìm được icon."""
    import re
    mapping = json.loads((REPO / "branding" / "fluent-map.json").read_text(encoding="utf-8"))
    out, missing = {}, []
    for cmd, names in mapping.items():
        if cmd.startswith("_"):
            continue
        for pattern, size in CMD_SIZES.items():
            src = next((Path(fluent_dir) / f"{n}_{sz}_regular.svg" for n in names for sz in (size, 20, 24)
                        if (Path(fluent_dir) / f"{n}_{sz}_regular.svg").is_file()), None)
            if src is None:
                missing.append(cmd)
                break
            text = src.read_text(encoding="utf-8")
            text = re.sub(r'<svg ', f'<svg fill="{ICON_FG}" ', text, count=1)
            text = re.sub(r'width="\d+" height="\d+"', f'width="{size}" height="{size}"', text, count=1)
            out[pattern.format(cmd)] = text
    # Icon của dải thẻ thanh bên (Sidebar.xcu trỏ thẳng tới các tệp này, không qua tên lệnh). Bản gốc là icon
    # màu kiểu cũ, nằm ngay mép phải nên rất dễ thấy lệch tông với phần còn lại.
    for path, name in SIDEBAR_DECKS.items():
        src = next((Path(fluent_dir) / f"{name}_{sz}_regular.svg" for sz in (24, 20)
                    if (Path(fluent_dir) / f"{name}_{sz}_regular.svg").is_file()), None)
        if src is None:
            missing.append(path)
            continue
        text = re.sub(r'<svg ', f'<svg fill="{ICON_FG}" ', src.read_text(encoding="utf-8"), count=1)
        out[path] = re.sub(r'width="\d+" height="\d+"', 'width="24" height="24"', text, count=1)
    # Lệnh của extension cũng vào theme, để nút trên thẻ AI và mục chuột phải có icon. framework
    # (CommandImageResolver.cxx) đổi "vnd.1x.tools:AiAsk" thành phần đường dẫn viết thường: "aiask".
    for cmd, name in ADDON_ICONS.items():
        for pattern, size in CMD_SIZES.items():
            src = next((Path(fluent_dir) / f"{name}_{sz}_regular.svg" for sz in (size, 20, 24)
                        if (Path(fluent_dir) / f"{name}_{sz}_regular.svg").is_file()), None)
            if src is None:
                missing.append(cmd)
                break
            text = re.sub(r'<svg ', f'<svg fill="{addon_fill(cmd, size)}" ', src.read_text(encoding="utf-8"), count=1)
            text = re.sub(r'width="\d+" height="\d+"', f'width="{size}" height="{size}"', text, count=1)
            out[pattern.format(cmd.lower())] = text
    return out, sorted(set(missing))


SIDEBAR_DECKS = {f"sfx2/res/symphony/sidebar-{k}-large.svg": v for k, v in {
    "property": "options", "style": "text_font_size", "gallery": "image_multiple", "navigator": "compass_northwest",
    "template": "document_multiple", "functions": "math_formula", "elements": "math_symbols",
    "transition": "slide_transition", "animation": "data_histogram", "a11y": "accessibility"}.items()}

# Icon cho lệnh của extension 1xai-tools (Addons.xcu trỏ tới bằng ImageSmallURL/ImageBigURL).
ADDON_ICONS = {"AiAccounts": "key", "AiAsk": "sparkle", "AiRewrite": "text_edit_style", "McpTools": "plug_connected",
               "McpServer": "server", "AiSkill": "hat_graduation", "Nd30Document": "document_ribbon",
               "Nd30Check": "document_checkmark", "NumberToWords": "number_symbol_square", "MoneyToWords": "money",
               "ConvertTCVN3": "arrow_swap", "ConvertVNI": "arrow_swap", "ConvertVIQR": "arrow_swap",
               "NormalizeUnicode": "text_grammar_wand", "RemoveDiacritics": "text_clear_formatting",
               "OpenCsvSafely": "document_table", "ToneStyleOld": "text_font", "ToneStyleNew": "text_font"}


# Nút LỚN trên thẻ AI tô màu theo nhóm (màu lấy từ branding/tokens.json), để mắt nhận ra nhóm ngay như cách WPS
# làm điểm nhấn; nút nhỏ và menu giữ đơn sắc. Lệnh không có trong bảng dùng ICON_FG.
ADDON_GROUP = {"AiAsk": "ai", "AiRewrite": "ai", "AiSkill": "ai", "Nd30Document": "pdf", "Nd30Check": "pdf",
               "McpTools": "doc", "McpServer": "doc", "AiAccounts": "doc", "OpenCsvSafely": "sheet"}


def addon_fill(cmd, size):
    return APPS[ADDON_GROUP[cmd]] if size > 16 and cmd in ADDON_GROUP else ICON_FG


def addon_icons(fluent_dir, out_dir):
    """Ghi icon 16px và 26px cho từng lệnh của extension vào extensions/1xai-tools/icons/."""
    import re
    out_dir.mkdir(parents=True, exist_ok=True)
    for cmd, name in ADDON_ICONS.items():
        for px, size in ((16, 16), (26, 24)):
            src = next((Path(fluent_dir) / f"{name}_{s}_regular.svg" for s in (size, 20, 24)
                        if (Path(fluent_dir) / f"{name}_{s}_regular.svg").is_file()), None)
            if src is None:
                raise SystemExit(f"thiếu icon Fluent cho {cmd}: {name}")
            text = re.sub(r"<svg ", f'<svg fill="{ICON_FG}" ', src.read_text(encoding="utf-8"), count=1)
            text = re.sub(r'width="\d+" height="\d+"', f'width="{px}" height="{px}"', text, count=1)
            (out_dir / f"{cmd}_{px}.svg").write_text(text, encoding="utf-8")


def icon_theme_zip(path, fluent_dir=None):
    """Icon theme "1x": chỉ chứa icon được thay; mọi icon khác upstream tự lấy từ colibre/colibre_dark."""
    import zipfile
    extra, missing = fluent_icons(fluent_dir) if fluent_dir else ({}, [])
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, (kind, key) in sorted(ICON_FILES.items()):
            z.writestr(name, icon_file(kind, key))
        for name, text in sorted(extra.items()):
            z.writestr(name, text)
    if fluent_dir:
        print(f"icon Fluent: {len(extra) // len(CMD_SIZES)} lệnh; không có icon: {', '.join(missing) or 'không'}")


def vietqr_svg():
    """Mã VietQR cho mục Ủng hộ tác giả, dựng từ branding/about.json. Mã tĩnh (không ghi sẵn số tiền) để người ủng hộ
    tự chọn mức. Kiểm lại bằng scripts/check-vietqr.sh."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import vietqr
    d = json.loads((REPO / "branding" / "about.json").read_text(encoding="utf-8"))["donate"]
    return vietqr.svg(d["bank_bin"], d["account"], purpose=d["purpose"], size=320, dark=B["ink_bottom"])


def theme_xcd():
    t = TOKENS["theme_dark"]
    ui = "\n".join(
        f'          <node oor:name="{k}"><prop oor:name="Color"><value>{int(v[1:], 16)}</value></prop></node>'
        f'  <!-- {v} -->' for k, v in t.items())
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- 1xAIoffice theme layer (MPL-2.0). GENERATED by scripts/brand/make-brand.py from branding/tokens.json; edit the
     tokens, not this file. Installed into the app's registry folder by scripts/build-macos.sh (step "config").
     Direction "Sơn mài": blue-tinted graphite surfaces, one cobalt accent; gold is reserved for the logo.
     Users can still switch to Automatic/Light/Dark in Tools > Options > Appearance. -->
<oor:data xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:oor="http://openoffice.org/2001/registry">
  <dependency file="main"/>
  <oor:component-data oor:package="org.openoffice.Office" oor:name="UI">
    <node oor:name="ColorScheme">
      <prop oor:name="CurrentColorScheme" oor:op="fuse"><value>1xAIoffice</value></prop>
      <node oor:name="ColorSchemes">
        <node oor:name="1xAIoffice" oor:op="replace">
{ui}
        </node>
      </node>
    </node>
  </oor:component-data>
  <!-- Theme on (1 = Enabled), dark application colors (2) so unset document-area colors use their dark variants;
       pages stay white (UseOnlyWhiteDocBackground). -->
  <oor:component-data oor:package="org.openoffice.Office" oor:name="Common">
    <node oor:name="Appearance">
      <prop oor:name="LibreOfficeTheme" oor:op="fuse"><value>1</value></prop>
      <prop oor:name="ApplicationAppearance" oor:op="fuse"><value>2</value></prop>
      <prop oor:name="UseOnlyWhiteDocBackground" oor:op="fuse"><value>true</value></prop>
    </node>
    <!-- Icon theme "1x" (images_1x.zip): only the replaced icons, the rest falls back to colibre_dark. -->
    <node oor:name="Misc">
      <prop oor:name="SymbolStyle" oor:op="fuse"><value>1x</value></prop>
      <prop oor:name="ShowDonation" oor:op="fuse"><value>false</value></prop>
      <!-- Ribbon background: 235/255 theme color, only a hint of the app's own color. -->
      <prop oor:name="NotebookbarColorTransparency" oor:op="fuse"><value>235</value></prop>
    </node>
    <!-- Recent documents area of the Start Center uses its own colors. -->
    <node oor:name="Help">
      <node oor:name="StartCenter">
        <prop oor:name="StartCenterThumbnailsBackgroundColor" oor:op="fuse"><value>{int(t["MenuBarColor"][1:], 16)}</value></prop>
        <prop oor:name="StartCenterThumbnailsTextColor" oor:op="fuse"><value>{int(t["WindowTextColor"][1:], 16)}</value></prop>
      </node>
    </node>
  </oor:component-data>
</oor:data>
"""


def render_png(svg_text, w, h, out, tmp):
    html = Path(tmp) / f"r{w}x{h}.html"
    html.write_text(f'<!doctype html><html><body style="margin:0;background:transparent">{svg_text}</body></html>',
                    encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--use-mock-keychain", "--password-store=basic", "--disable-gpu",
                    "--no-first-run", "--no-default-browser-check", f"--user-data-dir={tmp}/chrome",
                    "--hide-scrollbars", "--default-background-color=00000000", "--force-device-scale-factor=1",
                    f"--window-size={w},{h}", f"--screenshot={out}", html.as_uri()],
                   check=True, capture_output=True, timeout=60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True, help="Noto Sans Bold .ttf")
    ap.add_argument("--font-regular", required=True, help="Noto Sans Regular .ttf")
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--fluent", help="thư mục icons của gói @fluentui/svg-icons (MIT), cho icon lệnh trên ribbon")
    a = ap.parse_args()
    bold, regular = Font(a.font), Font(a.font_regular)
    (OUT / "shell").mkdir(parents=True, exist_ok=True)
    light, dark = logo(bold, regular, False), logo(bold, regular, True)
    for name, text in {"logo": light, "logo-sc": light, "logo_inverted": dark, "logo-sc_inverted": dark,
                       "about": about_bg()}.items():
        (OUT / "shell" / f"{name}.svg").write_text(text, encoding="utf-8")
    (OUT / "vietqr.svg").write_text(vietqr_svg(), encoding="utf-8")
    (OUT / "mark.svg").write_text(svg(256, 256, mark_group(0, 0, 256, "m")), encoding="utf-8")
    (REPO / "config" / "1x-theme.xcd").write_text(theme_xcd(), encoding="utf-8")
    icon_theme_zip(OUT / "images_1x.zip", a.fluent)
    if a.fluent:
        addon_icons(a.fluent, REPO / "extensions" / "1xai-tools" / "icons")
    if a.no_png:
        return
    with tempfile.TemporaryDirectory() as tmp:
        render_png(splash(bold, regular, 644, 199), 644, 199, OUT / "intro.png", tmp)
        render_png(splash(bold, regular, 990, 254), 990, 254, OUT / "intro-highres.png", tmp)
        render_png(icon_svg(1024), 1024, 1024, OUT / "mark-1024.png", tmp)
        iconset = Path(tmp) / "main.iconset"
        iconset.mkdir()
        for px in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                n = px * scale
                render_png(icon_svg(n), n, n, iconset / f"icon_{px}x{px}{'@2x' if scale == 2 else ''}.png", tmp)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(OUT / "main.icns")], check=True)
    print("branding/out và config/1x-theme.xcd đã sinh lại")


if __name__ == "__main__":
    main()
