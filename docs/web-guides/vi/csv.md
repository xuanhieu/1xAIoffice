---
title: 1xAIoffice: mở tệp CSV không lỗi font, không mất số 0
description: Mở CSV đúng UTF-8, giữ số 0 đầu, số CCCD, mã và ngày như trong tệp, không chạy công thức lạ. Tự đoán dấu phân cách, cố định dòng tiêu đề.
headline: Mở tệp CSV an toàn
lead: Bấm Mở CSV an toàn trong 1xSheet: tệp được đọc bằng UTF-8, mọi cột giữ dạng chữ, nên tiếng Việt không lỗi và số 0 đầu, số CCCD, ngày tháng còn nguyên.
order: 7
---

Mở CSV an toàn đọc tệp bằng UTF-8 và giữ mọi cột ở dạng chữ, nên tiếng Việt không bị lỗi font, số điện thoại không mất số 0 đầu, số CCCD không bị đổi thành dạng 1,2E+11, và ngày tháng còn đúng như trong tệp.

## Các bước {#cac-buoc}

1. **Bấm Mở CSV an toàn** trên thẻ AI của 1xSheet, hoặc menu Tiếng Việt ▸ Mở CSV an toàn.
2. **Chọn tệp** .csv hoặc .txt.
3. **Làm việc như bảng thường.** App tự đoán dấu phân cách (phẩy, chấm phẩy, tab, gạch đứng), co độ rộng cột, và nếu dòng đầu giống tiêu đề thì in đậm, cố định dòng đó.

Ô bắt đầu bằng dấu "=" được giữ là chữ, không chạy như công thức, nên tệp từ nguồn lạ không chèn được công thức vào bảng của bạn.

## Không làm gì {#gioi-han}

- Không đổi cột sang số hay ngày. Muốn tính toán trên một cột thì chuyển cột đó sang dạng số sau khi mở.
- Tệp không phải UTF-8 (ví dụ xuất từ phần mềm cũ dùng mã TCVN3) có thể hiện sai dấu; dùng [chuyển mã tiếng Việt](/office/tieng-viet) sau khi mở.
- Mở xong, đóng lại mà không sửa thì app không hỏi lưu. Muốn giữ bản bảng tính thì Lưu thành .xlsx hoặc .ods.
