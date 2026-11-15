---
title: 1xAIoffice: hỏi AI và viết lại văn bản
description: Hỏi AI về tài liệu đang mở hoặc nhờ AI viết lại một đoạn trong 1xAIoffice. Hỏi không bao giờ sửa tài liệu; viết lại luôn cho xem trước và hoàn tác được.
headline: Hỏi AI và viết lại văn bản trong 1xAIoffice
lead: Bấm Hỏi AI để hỏi về đoạn đang chọn hoặc cả tài liệu, bấm Viết lại để AI soạn lại một đoạn. Hỏi chỉ đọc; Viết lại cho xem trước rồi mới áp dụng.
order: 1
---

Hỏi AI gửi đoạn bạn đang chọn (hoặc cả tài liệu nếu không chọn gì) cho tài khoản AI của bạn và hiện câu trả lời, không sửa gì trong tài liệu. Viết lại (chỉ có trong 1xDoc) cho bạn xem bản mới trước, bấm đồng ý mới thay, và một lần Cmd+Z là quay về.

## Tìm ở đâu

- **Thẻ AI trên ribbon:** nút Hỏi AI, Viết lại.
- **Thanh bên AI** ở mép phải cửa sổ: các nút giống ribbon, kèm dòng cho biết đang dùng tài khoản AI nào.
- **Chuột phải** vào chữ (1xDoc) hoặc ô (1xSheet): Hỏi AI về tài liệu này…
- **Menu Tiếng Việt** trên thanh menu: mọi lệnh AI.

Chưa gắn tài khoản AI thì app hỏi bạn có muốn gắn ngay không, rồi mở [Tài khoản AI](/office/tai-khoan-ai).

## Hỏi AI {#hoi-ai}

1. **Chọn đoạn cần hỏi.** Không chọn thì app dùng cả tài liệu. Trong 1xSheet, app gửi vùng có dữ liệu của mọi trang tính.
2. **Bấm Hỏi AI và gõ câu hỏi.** Ví dụ: "Tóm tắt văn bản này trong 5 ý", "Cột nào có số liệu bất thường?".
3. **Đọc câu trả lời.** Cuối hộp trả lời ghi rõ tài khoản và mô hình đã dùng, phần nào đã gửi đi, bao nhiêu ký tự, có bị cắt bớt không.

Mỗi lần hỏi gửi tối đa khoảng 12.000 ký tự, cắt ở ranh giới đoạn. Tài liệu dài hơn thì chọn đúng phần cần hỏi.

## Viết lại {#viet-lai}

1. **Đặt con trỏ vào đoạn cần viết lại** hoặc chọn chữ trong đoạn đó. Viết lại làm việc trên cả đoạn chứa chỗ bạn chọn.
2. **Bấm Viết lại và ghi hướng muốn sửa.** Để trống thì AI viết rõ ràng hơn, giữ nguyên ý và thuật ngữ.
3. **Xem bản mới rồi quyết định.** Đồng ý thì đoạn được thay một lần; Cmd+Z một lần là hoàn tác.

Nếu bạn sửa đoạn đó trong lúc AI đang viết, app không áp dụng bản mới để khỏi đè lên chữ của bạn.

## Dữ liệu đi đâu {#rieng-tu}

Chữ được gửi thẳng từ máy bạn tới nhà cung cấp AI bạn đã chọn, bằng tài khoản của bạn. Khoá API nằm trong Keychain của macOS, không nằm trong tệp cấu hình. Chọn Ollama hoặc LM Studio thì không có gì rời khỏi máy. 1xAIoffice không bán gói AI: phí (nếu có) do nhà cung cấp tính trên tài khoản của bạn.

## Không làm gì {#gioi-han}

- Hỏi AI không sửa tài liệu. Muốn sửa thì dùng Viết lại.
- Viết lại chưa có trong 1xSheet và 1xSlide.
- Câu trả lời của AI có thể sai; đọc lại trước khi dùng cho văn bản chính thức.
