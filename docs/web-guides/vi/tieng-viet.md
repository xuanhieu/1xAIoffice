---
title: 1xAIoffice: chuyển mã TCVN3, VNI sang Unicode
description: Chuyển chữ TCVN3 (.VnTime), VNI, VIQR sang Unicode; chuẩn hoá Unicode; bỏ dấu; đổi dấu thanh kiểu cũ (hòa) và kiểu mới (hoà).
headline: Chuyển mã và chuẩn hoá tiếng Việt
lead: Chọn đoạn chữ (hoặc không chọn để làm cả tài liệu), bấm lệnh chuyển mã hợp với nguồn: TCVN3, VNI, VIQR. Mỗi lần chuyển là một bước hoàn tác.
order: 8
---

Văn bản cũ gõ bằng phông .VnTime (TCVN3), VNI hay kiểu VIQR (a', e^) mở ra bị lỗi dấu. Chọn đoạn cần sửa, hoặc không chọn gì để làm cả tài liệu, rồi bấm lệnh chuyển mã tương ứng; 1xAIoffice đổi sang Unicode và báo đã đổi bao nhiêu đoạn.

## Các lệnh

- **Chuyển mã TCVN3:** chữ gõ bằng phông .Vn… sang Unicode. Khi không chọn gì, app chỉ đổi phần chữ dùng phông .Vn… và đặt lại phông Times New Roman.
- **Chuyển VNI, Chuyển VIQR:** chữ kiểu VNI hoặc VIQR sang Unicode.
- **Chuẩn hoá Unicode:** đưa về một dạng Unicode thống nhất (NFC), gộp khoảng trắng thừa, sửa khoảng cách quanh dấu câu. Nên chạy trước khi tìm kiếm, sắp xếp hay so sánh.
- **Bỏ dấu:** "Tiếng Việt" thành "Tieng Viet", dùng cho tên tệp, mã, email.
- **Dấu kiểu cũ / Dấu kiểu mới:** đổi giữa hòa, khỏe, thủy và hoà, khoẻ, thuỷ. Chỉ đổi các vần oa, oe, uy.

## Tìm ở đâu

Thẻ AI trên ribbon (nút nhỏ), menu Tiếng Việt trên thanh menu. Hai lệnh đổi kiểu dấu chỉ có trong menu Tiếng Việt.

## Các bước {#cac-buoc}

1. **Chọn phần cần đổi.** Trong 1xDoc, không chọn gì là làm cả tài liệu. Trong 1xSheet, app đổi các ô chữ trong vùng chọn.
2. **Bấm lệnh hợp với nguồn chữ.**
3. **Kiểm lại.** Sai thì Cmd+Z một lần là về như cũ.

## Không làm gì {#gioi-han}

- VNI và VIQR: dấu chỉ được đổi khi gõ ngay sau nguyên âm của nó; kiểu gõ dấu ở cuối chữ không được nhận.
- Chuẩn hoá Unicode không đổi kiểu dấu thanh; dùng lệnh Dấu kiểu cũ hoặc Dấu kiểu mới.
