#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Chụp ảnh app thật cho bộ hướng dẫn nhanh, bản tiếng Việt và tiếng Anh.

Mỗi ảnh là ảnh của ĐÚNG MỘT cửa sổ 1xAIoffice (agent-desktop screenshot --window-id), không bao giờ chụp màn hình
chung, nên không lọt nội dung của ứng dụng khác. Hồ sơ người dùng tạm cho mỗi ngôn ngữ; bản tiếng Việt đặt sẵn
UILocale=vi. Thẻ AI trên ribbon được cho lên trước tạm thời để ảnh thấy được nó, rồi trả lại tệp ribbon chuẩn.

Ra: docs/ui/guide-<ảnh>-<vi|en>.png  (start, writer, nd30, calc, impress, và hai ảnh cắt từ writer: ribbon,
sidebar; cắt bằng PIL ở đây vì Python đi kèm app không có PIL)
Dùng: scripts/guides/capture-shots.py --app <1xAIoffice.app>
"""
import argparse
import json
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "ui"
AD = str(Path.home() / ".local" / "bin" / "agent-desktop")
APP_NAME = "1xAIoffice"


def ad(*args):
    done = subprocess.run([AD, *args], capture_output=True, text=True, timeout=60)
    try:
        return json.loads(done.stdout or "{}")
    except ValueError:
        return {}


def windows():
    return ad("list-windows", "--app", APP_NAME).get("data") or []


def wait_window(match, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        for w in windows():
            if match(w):
                return w["id"]
        time.sleep(1.5)
    raise SystemExit(f"không thấy cửa sổ cần chụp ({timeout}s)")


def shoot(window_id, name, lang):
    out = OUT / f"guide-{name}-{lang}.png"
    ad("screenshot", "--app", APP_NAME, "--window-id", window_id, str(out))
    print("chụp", out.name)


def press(window_id, role, name):
    found = ad("find", "--app", APP_NAME, "--window-id", window_id, "--role", role, "--name", name)
    matches = (found.get("data") or {}).get("matches") or []
    if matches:
        ad("click", matches[0]["ref_id"])
        return True
    return False


def ai_tab_first(path):
    """Tạm cho thẻ AI đứng trước Home và mang ngữ cảnh chữ/ô, để tài liệu mở ra là thấy thẻ AI."""
    tree = ET.parse(path)
    root = tree.getroot()
    parent = {c: p for p in root.iter() for c in p}
    page = parent[next(o for o in root.iter("object") if o.get("id") == "1xAI Tab")]
    book = parent[page]
    kids = list(book)
    label = kids[kids.index(page) + 1]
    style = next(o for o in label.iter("object")).find("style")
    for ctx in ("context-Text", "context-DrawText", "context-Cell"):
        ET.SubElement(style, "class", name=ctx)
    home = next(o for o in root.iter("object") if o.get("class") == "sfxlo-PriorityHBox"
                and any(x.get("id") == "pmhbHome" for x in o.iter("object")))
    home_child = parent[home]
    book.remove(page)
    book.remove(label)
    at = list(book).index(home_child)
    book.insert(at, page)
    book.insert(at + 1, label)
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def run(app, lang):
    soffice = str(app / "Contents" / "MacOS" / "soffice")
    profile = Path(tempfile.mkdtemp(prefix="guideshots-"))
    if lang == "vi":
        (profile / "user").mkdir(parents=True)
        (profile / "user" / "registrymodifications.xcu").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
            'xmlns:xs="http://www.w3.org/2001/XMLSchema">\n'
            '<item oor:path="/org.openoffice.Office.Linguistic/General"><prop oor:name="UILocale" oor:op="fuse">'
            '<value>vi</value></prop></item>\n</oor:items>\n', encoding="utf-8")
    env = ["-env:UserInstallation=" + profile.as_uri()]
    procs = []
    try:
        procs.append(subprocess.Popen([soffice, *env], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(6)
        start = wait_window(lambda w: w["bounds"]["width"] > 1000)
        time.sleep(4)               # mục Gần đây được gieo hướng dẫn rồi Start Center vẽ lại
        start = wait_window(lambda w: w["bounds"]["width"] > 1000)
        shoot(start, "start", lang)

        subprocess.Popen([soffice, *env, "--writer"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        writer = wait_window(lambda w: w["title"].startswith(("Untitled", "Không tên")))
        time.sleep(3)
        press(writer, "checkbox", "AI")          # mở thanh bên AI
        time.sleep(2)
        shoot(writer, "writer", lang)
        nd30 = "Văn bản NĐ30" if lang == "vi" else "Decree 30 Document"
        if press(writer, "button", nd30):
            dialog = wait_window(lambda w: w["bounds"]["width"] < 1000 and w["title"])
            time.sleep(1.5)
            shoot(dialog, "nd30", lang)
            press(dialog, "button", "Huỷ" if lang == "vi" else "Cancel")
            time.sleep(1)

        subprocess.Popen([soffice, *env, "--calc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(6)
        calc = next(w["id"] for w in windows() if w["bounds"]["width"] > 1000 and w["id"] != writer)
        press(calc, "checkbox", "AI")
        time.sleep(2)
        shoot(calc, "calc", lang)

        subprocess.Popen([soffice, *env, "--impress"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(8)
        impress = next(w["id"] for w in windows() if w["bounds"]["width"] > 1000 and w["id"] not in (writer, calc))
        shoot(impress, "impress", lang)
    finally:
        subprocess.run(["pkill", "-f", f"soffice.*{profile.name}"], capture_output=True)
        time.sleep(2)
        shutil.rmtree(profile, ignore_errors=True)


def crops(lang):
    """Ảnh cận cảnh cho từng mục hướng dẫn: dải ribbon có thẻ AI, và thanh bên AI."""
    from PIL import Image
    src = OUT / f"guide-writer-{lang}.png"
    if not src.is_file():
        return
    im = Image.open(src)
    w, h = im.size
    im.crop((0, 0, w, int(h * 0.165))).save(OUT / f"guide-ribbon-{lang}.png")
    im.crop((int(w * 0.77), int(h * 0.09), w, int(h * 0.62))).save(OUT / f"guide-sidebar-{lang}.png")
    print("cắt", f"guide-ribbon-{lang}.png", f"guide-sidebar-{lang}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", help="1xAIoffice.app; bỏ trống khi chỉ cắt lại ảnh (--crop-only)")
    ap.add_argument("--crop-only", action="store_true")
    ap.add_argument("--lang", choices=["vi", "en"], action="append")
    a = ap.parse_args()
    if a.crop_only:
        for lang in a.lang or ["vi", "en"]:
            crops(lang)
        return
    app = Path(a.app)
    cfg = app / "Contents/Resources/config/soffice.cfg/modules"
    ribbons = [cfg / m / "ui" / "notebookbar.ui" for m in ("swriter", "scalc")]
    saved = {p: p.read_bytes() for p in ribbons}
    try:
        for p in ribbons:
            ai_tab_first(p)
        for lang in a.lang or ["vi", "en"]:
            run(app, lang)
            crops(lang)
    finally:
        for p, data in saved.items():     # trả lại ribbon chuẩn dù có lỗi
            p.write_bytes(data)


if __name__ == "__main__":
    main()
