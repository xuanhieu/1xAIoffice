# Báo cáo sáng 15/11/2026

## Kết quả

Đêm làm năm commit, đã đẩy lên `main`. Lấp xong hai phần còn thiếu của mốc M4 theo bản thiết kế, và **tìm ra
ba lỗi có sẵn** trong phần NĐ30 — trong đó một lỗi khiến bộ kiểm báo sai chính văn bản do app dựng ra.

| Commit | Việc |
|---|---|
| `f87bac6` | Tài liệu đang mở thành MCP resource, skill thành MCP prompt |
| `71baecb` | Kiểm thêm giãn dòng và khoảng cách đoạn; sửa số hiện sai trong lời nhắn |
| `ae51d27` | Bộ kiểm không còn báo sai văn bản do chính app dựng ra |
| `9f492c9` | Kiểm nhất quán cỡ chữ, và test riêng cho từng skill |
| `9f2a4e1` | Tài liệu cho phần resource và prompt |

Số đo cuối đêm: **416 test logic** (đầu đêm 363), độ phủ logic tiếng Việt **97,4%**, **128 bước kiểm trên app
thật** (đầu đêm 119), smoke test đạt, `check-repo.py` đạt, bước `defaults` đạt.

## Ba lỗi có sẵn đã sửa

**1. Bộ kiểm báo sai chính văn bản app dựng ra.** Em thêm một phép thử: văn bản do bộ dựng tạo phải vượt qua bộ
kiểm thể thức của chính app. Nó đỏ ngay lần chạy đầu ở `margin_right_mm`. Nguyên nhân: Writer giữ lề bằng twip,
nên lề đặt đúng 15 mm đọc ra là 14,99 mm, mà bộ kiểm so cứng. Người dùng tự đặt lề 15 mm trong Writer cũng
dính y hệt — tức bộ kiểm đang báo oan những văn bản đúng. Đã chừa dung sai 0,05 mm cho số đo milimét.

Đây là phép thử đáng giá nhất đêm nay, vì hai nửa (bộ dựng và bộ kiểm) viết độc lập nhau, nên bất đồng giữa
chúng là bằng chứng có thật một bên sai.

**2. Bộ kiểm thiếu hai quy định của Phụ lục I mục 6đ:** giãn dòng (tối thiểu dòng đơn, tối đa 1,5 lines) và
khoảng cách giữa các đoạn (tối thiểu 6pt). Nay có đủ.

**3. Số trong lời nhắn hiện sai.** Hàm `_mm` gọi `.rstrip("0")` lên cả số nguyên, nên lề 20 mm hiện thành
"2 mm" và khổ A4 rộng 210 mm hiện thành "21 mm". Người dùng đọc lời nhắn đó sẽ không hiểu gì.

## Việc mới

**MCP resource và prompt** (bản thiết kế mục 8, trước nay còn thiếu). Tài liệu văn bản thành `1x://doc/<mã>`
dạng Markdown, mỗi trang tính thành `1x://sheet/<mã>/<trang>` dạng CSV, và mỗi skill đã cài thành một prompt
dùng được thẳng trong Claude Desktop. Quyền giữ đúng một luật: chưa ghép đôi thì xem được danh sách nhưng
không đọc được nội dung.

## Default đã chọn

Chín mục, ghi đầy đủ kèm lý do và chỗ sửa trong `plans/reports/buildnotes-261115-0308-dem-mcp-resources.md`.
Bốn mục đáng để ý nhất:

- **Chưa ghép đôi vẫn xem được danh sách tài liệu, nhưng không đọc được nội dung** — cùng luật đang áp cho
  `tools/call`, vì đọc trộm cũng tệ như sửa trộm.
- **Markdown chỉ đổi tiêu đề**, không đoán in đậm hay bảng — đoán sai nguy hiểm hơn Markdown nghèo nàn.
- **Khoảng cách đoạn chỉ bắt lỗi khi nhỏ hơn 6pt**, không có mức tối đa, vì Nghị định chỉ đặt mức tối thiểu.
  Báo oan một văn bản đúng còn tệ hơn bỏ sót.
- **Dung sai 0,05 mm** khi đo lề và khổ giấy: rộng hơn sai số quy đổi twip (~0,018 mm), hẹp hơn nhiều so với
  bước 5 mm giữa các mốc của Nghị định.

## Việc đang chờ anh quyết

Không việc nào trong đêm chạm tới nhóm phải xin phép. Những việc vẫn treo:

1. **Chưa gọi thử nhà cung cấp AI thật nào.** Tiêu chí nghiệm thu M5 vẫn chưa chạy được. Cần anh gắn khoá thật
   hoặc chạy Ollama.
2. **Luồng OAuth mới chỉ đứng trước máy chủ giả**; cần một `client_id` thật của Google hoặc Entra ID.
3. **Kho 2.159 biểu mẫu Coachio**: chưa đụng, vì phải rõ chuyện bản quyền trước khi đóng gói vào sản phẩm.
4. **Báo cáo branding/salekit của ChatGPT** chưa có trong kho nên em chưa đọc được dòng nào.

## Câu hỏi còn mở

- Bước dọn CSV (giãn cột, tô đậm, ghim tiêu đề) vẫn chỉ kiểm được bằng mắt, vì soffice headless trên macOS
  không mở nổi tài liệu thứ hai trong một phiên. Có đáng dựng một phiên riêng chỉ cho bước này không?
- Vạch ngăn giữa các thẻ ribbon do `NSSegmentedControl` của macOS vẽ; muốn bỏ phải vá lõi và dựng lại. Có làm
  không, hay chấp nhận?
