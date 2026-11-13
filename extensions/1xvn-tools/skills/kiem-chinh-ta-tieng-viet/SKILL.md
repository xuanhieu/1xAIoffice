---
name: kiem-chinh-ta-tieng-viet
description: Rà lỗi chính tả, dấu câu và cách đặt dấu thanh trong văn bản tiếng Việt, nêu từng chỗ kèm sửa đề nghị.
version: 1.0.0
apps: [doc]
tools: [doc.read, doc.replace, vn.normalize]
permissions: {network: [], process: false}
---
# Kiểm lỗi chính tả và ngữ pháp tiếng Việt

Rà theo đúng thứ tự này và báo **từng chỗ một**, mỗi chỗ gồm: chữ sai, chữ đề nghị, và lý do một câu.

1. Lỗi gõ và lỗi chính tả thường gặp: l/n, ch/tr, s/x, d/gi/r, dấu hỏi và dấu ngã.
2. Viết hoa: đầu câu, tên riêng, tên cơ quan, tên văn bản. Không viết hoa tuỳ tiện giữa câu.
3. Dấu câu và khoảng trắng: không có khoảng trắng trước dấu phẩy và dấu chấm, có một khoảng trắng sau; dấu ngoặc đóng mở đủ đôi.
4. Chữ chưa chuẩn Unicode, hoặc còn ở bảng mã cũ. Gặp thì nhắc dùng lệnh **Chuẩn hoá tiếng Việt** hoặc **Chuyển mã TCVN3** trên menu Tiếng Việt.
5. Cách đặt dấu thanh kiểu cũ và kiểu mới (`hòa` / `hoà`): **không phải lỗi**, chỉ báo khi trong cùng một văn bản dùng lẫn cả hai kiểu.

Không sửa giọng văn, không rút gọn câu của người viết, không đổi thuật ngữ. Chỉ sửa cái sai.
