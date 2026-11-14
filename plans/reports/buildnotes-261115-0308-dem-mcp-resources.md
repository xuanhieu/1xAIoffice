# Sổ ghi đêm 15/11/2026 — chạy không người canh

Việc tự nhận: lấp những phần còn thiếu so với bản thiết kế `ai-platform-design.md` mà làm được mà không cần
khoá thật, không cần mạng, và không chạm vào nhóm việc phải xin phép.

## Default đã chọn

| # | Việc | Default | Lý do | Sửa ở đâu |
|---|---|---|---|---|
| 1 | Ai được đọc nội dung resource | Trợ lý **chưa ghép đôi vẫn xem được danh sách** tài liệu, nhưng **không đọc được nội dung** | Giống hệt luật đang áp cho `tools/call`. Danh sách chỉ là tên tài liệu; nội dung mới là thứ nhạy cảm, và đọc trộm cũng tệ như sửa trộm | `mcpserver/server.py`, `require_pairing` |
| 2 | Ai được đọc thân skill qua prompt | Cũng phải ghép đôi | Thân skill là cách làm việc đã đóng gói của cơ quan, không phải thứ ai hỏi cũng đưa | cùng tệp, `get_prompt` |
| 3 | Tài liệu văn bản ra Markdown đến đâu | **Chỉ đổi tiêu đề thành `#`**, không đoán in đậm, danh sách hay bảng | Đoán sai thì trợ lý đọc ra một tài liệu không giống bản người dùng đang nhìn — nguy hiểm hơn là Markdown nghèo nàn | `vn1x/mcpresources.py`, `to_markdown` |
| 4 | Bảng tính thành resource thế nào | **Mỗi trang tính một resource**, không gộp cả sổ | Gộp thì mất ranh giới giữa các trang, trợ lý đọc nhầm số của trang khác | `mcpresources.descriptors` |
| 5 | CSV của trang tính | Đúng RFC 4180 (bọc nháy kép khi có phẩy, nháy, xuống dòng) | Địa chỉ kiểu "Hà Nội, Việt Nam" rất thường gặp; không bọc là lệch cột | `mcpresources.to_csv` |
| 6 | Tên trang tính có dấu gạch chéo | Giữ nguyên, phần sau `1x://sheet/<id>/` lấy trọn | "Quý 1/2026" là cách đặt tên phổ biến ở Việt Nam | `mcpresources.parse` |

| 7 | Khoảng cách giữa các đoạn | Chỉ bắt lỗi khi **nhỏ hơn** 6pt, không có mức tối đa | Phụ lục I mục 6đ chỉ nói "tối thiểu là 6pt". Bắt cả mức trên là báo oan văn bản đúng, mà báo oan còn tệ hơn bỏ sót | `nd30_check._check_spacing` |
| 8 | Giãn dòng đặt kiểu khác | Bỏ qua, không báo lỗi | Tài liệu đặt khoảng cách dòng cố định theo mm thì không quy ra "dòng đơn / 1,5 lines" được nếu không biết cỡ chữ và phông; im lặng còn hơn báo bừa | cùng chỗ |

## Lỗi có sẵn đã sửa trong đêm

- **Bộ kiểm NĐ30 thiếu hai quy định của Phụ lục I**: giãn dòng (dòng đơn đến 1,5 lines) và khoảng cách giữa các
  đoạn (tối thiểu 6pt). Nay có `body_line_spacing` và `body_space_after`; `nd30_check_writer.describe` đọc thêm
  `ParaLineSpacing` và `ParaBottomMargin`.
- **Số trong lời nhắn hiện sai**: `_mm` gọi `.rstrip("0")` lên cả số nguyên, nên lề 20 mm hiện thành "2 mm" và
  khổ A4 rộng 210 mm hiện thành "21 mm". Người dùng đọc lời nhắn đó sẽ không hiểu gì. Đã sửa và có test riêng
  cho từng con số tròn.

| 9 | Dung sai khi đo lề và khổ giấy | **0,05 mm** | Writer giữ số đo bằng twip nên 15 mm đọc ra có thể là 14,99 mm. Không chừa dung sai thì bộ kiểm báo sai cả văn bản do chính app dựng. 0,05 mm rộng hơn sai số quy đổi (~0,018 mm) nhưng hẹp hơn nhiều so với bước 5 mm giữa các mốc của Nghị định | `nd30_check.ROUNDING_MM` |

## Lỗi có sẵn đã sửa trong đêm (tiếp)

- **Bộ kiểm báo sai chính văn bản app dựng ra.** Thêm bước kiểm "văn bản app dựng ra tự vượt qua bộ kiểm thể
  thức" thì nó đỏ ngay ở `margin_right_mm`: bộ dựng đặt lề phải đúng 15 mm, Writer lưu bằng twip và trả về
  14,99 mm, bộ kiểm so cứng nên kết luận sai. Người dùng đặt lề đúng 15 mm trong Writer cũng dính y hệt.
  Đây là phép thử đáng giá nhất đêm nay: hai nửa (bộ dựng và bộ kiểm) viết độc lập nhau, nên bất đồng giữa
  chúng là có thật một bên sai.

## Việc đang chờ chủ dự án

Không có việc nào trong đêm chạm tới nhóm phải xin phép (gửi tin, đăng công khai, chi tiền, xoá vĩnh viễn, nhập
khoá, đổi cấu hình bảo mật). Những việc vẫn treo từ trước:

- Chưa gọi thử nhà cung cấp AI thật nào, nên tiêu chí nghiệm thu M5 vẫn chưa chạy được.
- Luồng OAuth mới chỉ đứng trước máy chủ giả; cần một `client_id` thật.
- Kho 2.159 biểu mẫu Coachio: chưa đụng vì phải rõ chuyện bản quyền trước.
- Báo cáo branding/salekit của ChatGPT chưa có trong kho nên chưa đọc được.
