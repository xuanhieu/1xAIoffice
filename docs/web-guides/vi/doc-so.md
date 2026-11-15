---
title: 1xAIoffice: đọc số và số tiền thành chữ
description: Đổi số thành chữ tiếng Việt trong 1xDoc, 1xSheet và hàm DOCSO, DOCTIEN: 1.250.000 thành "Một triệu hai trăm năm mươi nghìn đồng".
headline: Đọc số và số tiền thành chữ
lead: Chọn số rồi bấm Đọc số tiền, hoặc gõ =DOCTIEN(E5) trong 1xSheet: 1.250.000 thành "Một triệu hai trăm năm mươi nghìn đồng".
order: 9
---

Chọn một số rồi bấm Đọc số hoặc Đọc số tiền; trong bảng tính có thêm hai hàm =DOCSO() và =DOCTIEN() tự cập nhật khi số đổi. Ví dụ =DOCTIEN(1250000) cho "Một triệu hai trăm năm mươi nghìn đồng".

## Trong 1xDoc

1. **Chọn số** trong văn bản. App hiểu các cách viết 1.250.000, 1,250,000.5, 12 500, có đ hoặc ₫ ở cuối, và số âm.
2. **Bấm Đọc số tiền** (hoặc Đọc số) trên thẻ AI hay menu Tiếng Việt. Số được thay bằng chữ.

## Trong 1xSheet

- **Bấm nút:** chọn các ô có số, bấm Đọc số tiền. Chữ được ghi vào ô trống bên phải mỗi số. Ô bên phải đã có dữ liệu thì app bỏ qua và báo số ô bỏ qua.
- **Dùng hàm:** `=DOCSO(số; "lẻ"|"linh")` đọc số, `=DOCTIEN(số tiền; đơn vị)` đọc số tiền, đơn vị mặc định là "đồng".

## Cách đọc {#cach-doc}

- 105 đọc là "một trăm lẻ năm" (DOCSO cho chọn "linh").
- Số thập phân đọc bằng "phẩy". Số tiền được làm tròn tới đơn vị, viết hoa chữ đầu, thêm "đồng" ở cuối.
- Đọc được tới 18 chữ số phần nguyên.

## Không làm gì {#gioi-han}

- DOCSO và DOCTIEN là hàm của 1xAIoffice. Lưu thành .xlsx thì Excel vẫn thấy chữ đã tính nhưng không tính lại được khi số đổi.
- Chưa đọc số bằng tiếng Anh hay đơn vị ngoại tệ có cách đọc riêng (ví dụ "đô la và xu").
