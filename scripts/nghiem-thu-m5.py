#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Nghiệm thu mốc M5: AI soạn một công văn, và công văn đó phải ĐẠT kiểm thể thức NĐ30.

Chạy bằng Python của chính app, nối vào một phiên 1xAIoffice đang mở qua UNO pipe. Xem scripts/nghiem-thu-m5.sh.

Khoá API không đi qua script này: app đọc nhà cung cấp từ providers.json của người dùng, còn giá trị khoá thì
chỉ tiến trình Agent Host lấy ra từ kho bí mật của hệ điều hành.

Dùng: nghiem-thu-m5.py <pipe> <tệp chứa câu trả lời của skill>
"""
import os
import sys
import time

import uno
from com.sun.star.beans import PropertyValue

def prop(name, value):
    item = PropertyValue()
    item.Name, item.Value = name, value
    return item


def connect(pipe):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            return resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
        except Exception:                      # noqa: BLE001 - app còn đang khởi động
            time.sleep(1)
    sys.exit("không nối được tới 1xAIoffice")


def main():
    pipe, answer_file = sys.argv[1], sys.argv[2]
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "extensions", "1xvn-tools", "pythonpath"))
    from vn1x import nd30, nd30_check, nd30_check_writer, nd30_writer

    ctx = connect(pipe)
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    helper = smgr.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)

    if os.path.exists(answer_file):
        os.remove(answer_file)

    print("1. Giao việc cho AI qua skill “soan-van-ban-nd30”…")
    draft = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, (prop("Hidden", False),))
    helper.executeDispatch(draft.getCurrentController().getFrame(), "vnd.1x.tools:AiSkill", "", 0, ())
    for _ in range(120):                       # mô hình thật có thể nghĩ lâu
        if os.path.exists(answer_file):
            break
        time.sleep(1)
    if not os.path.exists(answer_file):
        sys.exit("   KHÔNG ĐẠT: app không trả lời gì. Xem đã gắn nhà cung cấp AI chưa.")
    with open(answer_file, encoding="utf-8") as handle:
        answer = handle.read()
    body = [line.strip() for line in answer.splitlines()
            if line.strip() and not line.strip().startswith("—")]
    print(f"   AI trả về {len(body)} đoạn, {len(answer)} ký tự.")
    if not body:
        sys.exit("   KHÔNG ĐẠT: AI không trả về đoạn nội dung nào.")

    print("2. Dựng công văn theo thể thức NĐ30 từ nội dung AI viết…")
    import datetime
    spec = nd30.build({"type": "cong_van", "parent_org": "UBND thành phố Đà Nẵng",
                       "org": "Sở Khoa học và Công nghệ", "org_abbr": "SKHCN", "number": 1,
                       "place": "Đà Nẵng", "date": datetime.date.today(),
                       "summary": "phối hợp triển khai nhiệm vụ khoa học và công nghệ năm 2027",
                       "recipient_to": "Ủy ban nhân dân các quận, huyện", "body": body,
                       "signer_title": "Giám đốc", "signer_name": "Nguyễn Văn A",
                       "recipients": ["Như trên"], "archive_unit": "VP", "archive_copies": 2})
    draft.getText().setString("")
    nd30_writer.fill(draft, spec)

    print("3. Chạy kiểm thể thức NĐ30 lên chính văn bản vừa dựng…")
    issues = nd30_check.check(nd30_check_writer.describe(draft))
    if issues:
        for issue in issues:
            print(f"   - {issue.key}: {issue.message}")
        sys.exit("   KHÔNG ĐẠT: công văn không qua được kiểm thể thức.")
    print("   Không lỗi thể thức nào.")
    print("\nĐẠT: AI soạn được công văn và công văn đó qua được kiểm thể thức NĐ30.")
    print("Văn bản đang mở trên màn hình để bạn đọc nội dung — phần chất lượng câu chữ thì phải người đọc.")


main()
