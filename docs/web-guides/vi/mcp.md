---
title: 1xAIoffice và MCP: công cụ ngoài, trợ lý ngoài
description: Nối máy chủ MCP ngoài cho Hỏi AI dùng, hoặc cho Claude Desktop, Cursor đọc và sửa tài liệu 1xAIoffice. Công cụ nào, trợ lý nào cũng phải được bạn cho phép.
headline: Dùng MCP với 1xAIoffice
lead: MCP có hai chiều. Công cụ MCP cho Hỏi AI dùng thêm công cụ bên ngoài; Cho trợ lý ngoài để Claude Desktop hay Cursor làm việc với tài liệu đang mở. Chiều nào cũng hỏi bạn trước.
order: 4
---

MCP là chuẩn để trợ lý AI dùng công cụ. Trong 1xAIoffice có hai chiều: Công cụ MCP cho Hỏi AI gọi công cụ của máy chủ MCP bên ngoài; Cho trợ lý ngoài biến 1xAIoffice thành máy chủ MCP để Claude Desktop, Cursor đọc và sửa tài liệu đang mở. Cả hai đều tắt cho tới khi bạn cho phép.

## Nối máy chủ MCP bên ngoài {#cong-cu-ngoai}

1. **Bấm Công cụ MCP** trên thẻ AI. Chưa có cấu hình thì app chỉ đường dẫn tệp `mcp_servers.json` trong hồ sơ app kèm ví dụ.
2. **Khai máy chủ trong `mcp_servers.json`.** Cùng định dạng với `claude_desktop_config.json` (mục `mcpServers`, mỗi máy chủ có `command`/`args` hoặc `url`). Máy chủ cần mã truy cập cố định thì ghi `token_ref` là tên một mục trong Keychain, không ghi mã vào tệp.
3. **Mở lại Công cụ MCP** để xem các công cụ và trạng thái: đã cho phép, đã từ chối, sẽ hỏi khi dùng.
4. **Hỏi AI như thường.** Lần đầu AI muốn dùng một công cụ, app hỏi "Cho phép dùng công cụ này từ giờ?". Công cụ đổi mô tả hay tham số thì app hỏi lại.

Máy chủ cần đăng nhập thì trình duyệt mở ra, và chưa có gì được gửi đi cho tới khi bạn đồng ý ở đó. Chỉ Hỏi AI dùng công cụ MCP.

## Cho trợ lý ngoài dùng 1xAIoffice {#tro-ly-ngoai}

1. **Bấm Cho trợ lý ngoài** (menu Tiếng Việt ▸ Cho trợ lý AI dùng 1xAIoffice). Lần đầu app hỏi có bật không.
2. **Chép cấu hình app đưa ra** vào Claude Desktop, Cursor hoặc trợ lý khác hỗ trợ MCP, rồi khởi động lại trợ lý đó.
3. **Cho phép trợ lý.** Khi trợ lý xin kết nối, bấm lại Cho trợ lý ngoài: app hỏi "… xin được đọc và sửa tài liệu của bạn qua MCP. Cho phép từ giờ?". Cũng ở đây bạn xem danh sách đã cho phép và tắt máy chủ.

Trợ lý được phép thì có thể: xem tài liệu đang mở, đọc nội dung và dàn ý, đọc vùng ô trong 1xSheet, kiểm thể thức NĐ30, chuyển mã tiếng Việt, và chèn hay thay chữ. Mọi thay đổi đều hiện cho bạn xem và chờ bạn đồng ý.

## Không làm gì {#gioi-han}

- Máy chủ MCP của 1xAIoffice chạy qua stdio, không mở cổng mạng.
- [Skill có sẵn](/office/skill) không được chia sẻ ra ngoài; chỉ skill bạn tự thêm mới hiện cho trợ lý ngoài.
- Công cụ MCP chỉ liệt kê, không tự chạy công cụ nào.
