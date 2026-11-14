# Báo cáo sáng 14/11/2026 — nền tảng AI của 1xVnOffice

## Kết quả

Xong cả ba mốc còn lại của giai đoạn 8, đã đẩy lên `main`:

| Mốc | Việc | Commit |
|---|---|---|
| M3 | MCP client qua stdio, quyền theo từng công cụ | `9ec820f` |
| M4 | 1xVnOffice làm máy chủ MCP, trợ lý ngoài đọc và sửa được tài liệu | `864899f` |
| M5 | Skill: định dạng, nạp từng phần, 8 skill đi kèm | `9147b8d` |

Số đo: **253 test logic** (trước đêm nay là 171), độ phủ logic tiếng Việt **97,9%** (ngưỡng 90%), và **94 bước kiểm chạy trên app thật** (trước đêm nay là 67). Tất cả đều đạt.

Ba việc người dùng thấy được:

1. **Mô hình dùng được công cụ ngoài.** Khai máy chủ MCP trong `mcp_servers.json` (chép thẳng từ Claude Desktop được). Lần đầu một công cụ được dùng, 1xVnOffice hiện tên, mô tả, tham số rồi hỏi. Máy chủ đổi mô tả sau lưng thì quyền cũ hết giá trị, phải hỏi lại.
2. **Trợ lý ngoài điều khiển được 1xVnOffice.** Claude Desktop hay Cursor đọc tài liệu đang mở, kiểm thể thức NĐ30, sửa một đoạn. Máy chủ tắt sẵn; trợ lý phải được duyệt; mỗi lần sửa đều hỏi; Ctrl+Z một lần trả lại như cũ.
3. **Tám skill đi kèm**: soạn văn bản NĐ30, tóm tắt văn bản pháp luật, viết lại trang trọng/dễ hiểu, dịch Việt–Anh, lập bảng dự toán, bảng lương thuế TNCN, tạo slide từ văn bản, kiểm chính tả tiếng Việt.

Một lỗi đáng nhớ: vòng gọi công cụ đạt hết test trong tiến trình nhưng **chết trên app thật**, vì app chạy Agent Host bằng `python -I` và cờ đó bỏ thư mục script khỏi `sys.path`. Đã sửa, và đã thêm một test chạy host.py đúng cách app gọi.

## Default đã tự chọn (và chỗ sửa nếu anh muốn khác)

Đủ 17 mục trong `plans/reports/buildnotes-261114-0051-ai-platform-mcp.md`. Những mục đáng anh xem lại nhất:

| Việc | Default | Sửa ở đâu |
|---|---|---|
| Thư viện MCP | Tự viết client JSON-RPC bằng thư viện chuẩn, không vendor SDK `mcp` | `agenthost/mcpclient.py` |
| Kiểu kết nối | Chỉ stdio, không mở cổng mạng nào | `mcpclient.py`, `mcpserver/server.py` |
| Máy chủ MCP của 1xVnOffice | **Tắt sẵn**, bật bằng một lệnh trên menu | `mcp_server.json` trong hồ sơ người dùng |
| Số bước gọi công cụ | 8 bước, 120 giây (bản thiết kế nói 12 bước, 5 phút) | `agenthost/host.py` |
| Kích thước kết quả MCP | Cắt ở 20.000 ký tự | `mcpclient.py` |
| `scripts/` của skill | **Chưa chạy** | `pythonpath/vn1x/skills.py` |
| Lệnh chạy skill | Chỉ đọc, không tự sửa tài liệu | `onex_tools.py`, `cmd_AiSkill` |
| Bộ công cụ mở cho trợ lý ngoài | 9 công cụ, chưa có xuất PDF và ký số | `pythonpath/vn1x/doctools.py` |

## Đang chờ anh quyết

1. **Chưa gọi thử nhà cung cấp AI thật nào.** Toàn bộ kiểm thử dùng máy chủ giả trên `127.0.0.1`. Cần anh gắn khoá thật (hoặc chạy Ollama cục bộ) mới biết chắc hình dạng yêu cầu và trả lời khớp thực tế, và mới chạy được tiêu chí nghiệm thu của M5 ("`/cong-van` tạo công văn đạt kiểm thể thức").
2. **Có vendor thư viện ngoài không** (`mcp`, `httpx`, `keyring`, `jsonschema`). Phải tải gói về kho nên em không tự làm.
3. **Có mở bản MCP qua HTTP không** (127.0.0.1 + token, và OAuth cho máy chủ từ xa). Đây là nửa còn lại của tiêu chí M3 và M4.
4. **Hai công cụ còn thiếu đụng tới việc không quay lại được**: `file.export_pdf` (ghi file ra ngoài) và `sign.request` (ký số). Em dừng ở đây chờ anh.
5. **Mẫu văn bản Đảng** (Hướng dẫn 05-HD/VPTW) vẫn chờ một nguồn tin cậy, và **lần chạy nghiệm thu 50 văn bản thật** vẫn chờ tài liệu của anh — hai việc này treo từ giai đoạn 3.

## Còn thiếu so với bản thiết kế

- MCP server: resources (`1x://doc/<id>`), prompts (mở skill thành MCP prompt), bản HTTP.
- Skill: gọi bằng `/` trong khung trợ lý và ô lệnh Alt+Q — chưa có vì chưa có khung trợ lý dạng sidebar.
- Giai đoạn 4 trở đi chưa bắt đầu: bản Windows/Linux, ký số, đo tương thích Microsoft Office, cập nhật an toàn, triển khai cho cơ quan.
