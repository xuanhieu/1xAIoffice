---
title: 1xAIoffice: chạy skill AI cho việc văn phòng
description: Skill là bộ hướng dẫn làm sẵn cho AI: soạn văn bản NĐ30, tóm tắt văn bản pháp luật, lập bảng lương. Cách chạy skill có sẵn và tự thêm skill của bạn.
headline: Chạy skill AI trong 1xAIoffice
lead: Skill là cách làm đã soạn sẵn cho một loại việc. Bấm Chạy skill, chọn skill, gõ việc cần làm; AI làm theo đúng cách đó trên tài liệu của bạn.
order: 2
---

Skill là bộ hướng dẫn soạn sẵn cho một loại việc, ví dụ soạn văn bản theo NĐ30 hay lập bảng lương. Bấm Chạy skill, chọn skill hợp với việc, gõ yêu cầu; AI đọc tài liệu đang mở và trả lời theo đúng cách skill đã đặt ra.

## Skill có sẵn

| Skill | Dùng trong |
|---|---|
| soan-van-ban-nd30: soạn văn bản hành chính theo NĐ30 | 1xDoc |
| viet-lai-trang-trong: viết lại giọng trang trọng | 1xDoc |
| kiem-chinh-ta-tieng-viet: soát chính tả tiếng Việt | 1xDoc |
| tom-tat-van-ban-phap-luat: tóm tắt văn bản pháp luật | 1xDoc |
| dich-viet-anh-hanh-chinh: dịch văn bản hành chính Việt–Anh | 1xDoc |
| tao-slide-tu-van-ban: dàn ý slide từ văn bản | 1xDoc, 1xSlide |
| bang-luong-thue-tncn: bảng lương và thuế TNCN | 1xSheet |
| lap-bang-du-toan: lập bảng dự toán | 1xSheet |

Danh sách hiện ra khi bấm Chạy skill chỉ gồm skill hợp với app đang mở.

## Các bước {#cac-buoc}

1. **Bấm Chạy skill** trên thẻ AI, ở thanh bên AI hoặc khi chuột phải.
2. **Gõ tên skill** trong danh sách hiện ra.
3. **Gõ việc cần làm.** Hộp nhập ghi mô tả của skill để bạn biết nó làm được gì.
4. **Đọc kết quả.** Cuối câu trả lời ghi tên và phiên bản skill đã dùng.

Skill chỉ đọc tài liệu, không tự sửa. Muốn đưa kết quả vào văn bản thì chép vào, hoặc dùng [Viết lại](/office/ai).

## Thêm skill của bạn {#skill-rieng}

Mỗi skill là một thư mục có tệp `SKILL.md` (phần đầu ghi `name`, `description`, `apps`: doc, sheet, slide), theo định dạng Agent Skills. Đặt thư mục đó vào:

`~/.config/1xaioffice/skills/`

Lần sau bấm Chạy skill, skill mới hiện trong danh sách. Thư mục này nằm ngoài hồ sơ app nên không mất khi đặt lại 1xAIoffice. Skill của bạn cũng được chia sẻ cho trợ lý AI bên ngoài khi bạn bật [máy chủ MCP](/office/mcp).

## Không làm gì {#gioi-han}

- Skill không chạy script hay chương trình kèm theo; chỉ phần hướng dẫn được đưa cho AI.
- Skill có sẵn của 1xAIoffice không được chia sẻ ra ngoài qua MCP.
- Skill cần một [tài khoản AI](/office/tai-khoan-ai) đã gắn.
