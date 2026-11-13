# Giao diện 1xVnOffice

Chủ dự án chốt ngày 13/11/2026: **không dùng giao diện LibreOffice**. Bố cục và cách làm việc theo kiểu WPS Office, chất lượng hướng tới Microsoft Office 2026.

## Giới hạn pháp lý

- Bố cục ribbon, thứ tự thẻ, tên lệnh thông dụng và phím tắt là quy ước chung mà Microsoft, WPS, ONLYOFFICE đều dùng. 1xVnOffice theo các quy ước này.
- **Không chép** icon, hình vẽ, logo, màu thương hiệu, tên sản phẩm hay ảnh chụp của WPS (Kingsoft) và Microsoft. Đó là tài sản có bản quyền và nhãn hiệu.
- **Bộ icon:** dùng Fluent UI System Icons của Microsoft (giấy phép MIT, `github.com/microsoft/fluentui-system-icons`). Nhờ vậy giao diện có nét hiện đại giống Office 2026 mà vẫn hợp pháp. Icon riêng của 1x (NĐ30, chuyển mã, AI) vẽ cùng phong cách.

## Mục tiêu đo được

"Hoàn hảo như Microsoft Office 2026" được quy thành các tiêu chí kiểm được:

| Tiêu chí | Mục tiêu bản 1.0 | Cách đo |
|---|---|---|
| Vị trí lệnh | 200 lệnh dùng nhiều nhất của Word, Excel, PowerPoint nằm cùng thẻ và cùng nhóm như Office | Bảng đối chiếu trong `docs/ui/command-map.csv`; test đọc file `.ui` và so |
| Phím tắt | Toàn bộ phím tắt phổ biến của Office chạy giống hệt | Test tự động gửi phím rồi kiểm lệnh được gọi |
| Số lần bấm | Các tác vụ phổ biến không cần nhiều bước hơn Office (ví dụ chèn bảng, đổi lề, trộn ô, thêm slide) | Kịch bản thao tác, đếm số bước |
| Hình ảnh | Ảnh chụp từng thẻ ribbon, sáng và tối, 1x và 2x, được người duyệt chấp nhận | Bộ ảnh chụp tự động, so với ảnh đã duyệt |
| Tốc độ | Đổi thẻ ribbon dưới 50 ms, mở thẻ tài liệu mới dưới 300 ms | Đo bằng bộ đo hiệu năng |

Giới hạn thật: VCL (bộ giao diện của LibreOffice) không có hiệu ứng trong mờ và chuyển động như Office. Bản 1.0 nhắm tới bố cục, icon, khoảng cách và phông chữ ngang Office; không hứa giống từng điểm ảnh.

## Các phần cần làm

| # | Phần | Cách làm | Giai đoạn |
|---|---|---|---|
| 1 | Ribbon mặc định cho cả bốn ứng dụng | Lớp cấu hình `config/1x-defaults.xcd` (đã có) | 2, xong |
| 2 | Thẻ và nhóm theo Office: Trang đầu, Chèn, Thiết kế, Bố cục, Tham chiếu, Thư, Xem lại, Xem, Trợ giúp (Writer); tương tự cho Sheet và Slide | Viết lại `notebookbar.ui` của từng module, đưa vào `patches/` hoặc ghi đè qua lớp UI | 2 |
| 3 | Thẻ "Tệp" mở màn hình backstage (Mới, Mở, Lưu, In, Xuất, Thông tin) thay menu | Bản vá sfx2 | 2 |
| 4 | Thẻ tài liệu trong một cửa sổ, nút "+" mở tài liệu mới (đặc trưng của WPS) | Bản vá framework/vcl; mỗi tài liệu vẫn là một frame, gom vào một cửa sổ chứa | 2–3 |
| 5 | Trang chủ thống nhất: tài liệu gần đây, mẫu NĐ30, nút tạo 1xDoc/1xSheet/1xSlide | Thay Start Center | 2 |
| 6 | Bộ icon "1x Fluent" từ Fluent UI System Icons, bản sáng và tối | Sinh `images_1x.zip` bằng script, ánh xạ tên lệnh UNO sang icon Fluent | 2 |
| 7 | Màu nhấn theo ứng dụng: 1xDoc xanh dương, 1xSheet xanh lá, 1xSlide cam | Lớp cấu hình giao diện | 2 |
| 8 | Ô "Tìm lệnh" (Alt+Q) có tìm không dấu | Dùng tính năng tìm lệnh có sẵn của LibreOffice, thêm chuẩn hoá tiếng Việt | 3 |
| 9 | Thanh truy cập nhanh trên thanh tiêu đề (Lưu, Hoàn tác, Làm lại) | Cấu hình notebookbar | 2 |
| 10 | Khung trợ lý AI bên phải | Giai đoạn 8 (`ai-platform-design.md`) | 8 |

## Số đo gốc (13/11/2026)

`scripts/ui-coverage.py` so ribbon với bảng đối chiếu `docs/ui/writer-command-map.csv` (86 lệnh chính của Word: Trang đầu, Chèn, Thiết kế, Bố cục, Tham chiếu, Thư, Xem lại, Xem).

| Ribbon | Đúng thẻ | Sai thẻ | Thiếu | Chi tiết |
|---|---|---|---|---|
| LibreOffice 26.8 Writer, `notebookbar.ui` gốc | 70/86 (81%) | 15 | 1 | `docs/ui/baseline-writer-libreoffice-26.8.md` |
| Mục tiêu 1xDoc 1.0 | 86/86 (100%) | 0 | 0 | CI chạy script với `--min 1.0` khi ribbon của 1x nằm trong repo |

Những lệnh lệch chính: đầu trang, chân trang, số trang, ngày giờ, chú thích, dòng chữ ký đang ở thẻ khác thay vì "Chèn"; hình mờ ở "Bố cục" thay vì "Thiết kế" (LibreOffice không có thẻ Thiết kế); trộn thư ở "Công cụ" thay vì "Thư"; "Sắp xếp" không có trên ribbon.

### Bản build đầu tiên (13/11/2026)

- Ribbon dạng thẻ đã là mặc định trong cả bốn ứng dụng nhờ `config/1x-defaults.xcd`. Ảnh: `docs/ui/writer-ribbon-baseline-2026-11-13.png` (so với giao diện cổ điển trước đó: `docs/ui/writer-classic-libreoffice-2026-11-13.png`).
- **Bản dịch tiếng Việt của LibreOffice 26.8 mới đạt 62% giao diện** (20.444/32.460 chuỗi; Writer `sw` 38%, `svx` 50%, `sfx2` 54%, `vcl` 55%, `cui` 85%). Hậu quả: ribbon lẫn Anh–Việt ("Home", "Insert", "Cut" chưa dịch; "Dán", "Tiêu đề 1" đã dịch).
- Tên sản phẩm vẫn là "LibreOfficeDev", hộp chào mừng của LibreOffice vẫn hiện. Cả hai sửa ở phần thương hiệu (giai đoạn 2).

### Bản dịch tiếng Việt của 1x (việc mới, giai đoạn 2)

1. Lớp dịch riêng `l10n/vi/` (các file `.po` bổ sung) được trộn vào `translations/source/vi` trước khi build. Script kiểm: không chuỗi nào của các module giao diện chính bị thiếu.
2. Bảng thuật ngữ theo cách gọi quen thuộc của Word, Excel, PowerPoint tiếng Việt (Trang đầu, Chèn, Bố cục, Tham chiếu, Xem lại…); đặt dấu thanh theo một quy ước thống nhất (cần chủ dự án chốt: "hóa" hay "hoá"); phím tắt không trùng trong cùng hộp thoại.
3. Dịch khoảng 12.000 chuỗi còn thiếu bằng AI theo bảng thuật ngữ, người duyệt lại phần hiện trên ribbon và hộp thoại phổ biến trước.
4. Gửi bản dịch về Weblate của LibreOffice để giảm phần phải tự giữ.
5. Mục tiêu bản 1.0: 100% chuỗi của `sfx2 sw sc sd svx cui vcl framework` có tiếng Việt.

Tiến độ:

| Ngày | Phạm vi | Số chuỗi | Ghi chú |
|---|---|---|---|
| 13/11/2026 | Toàn bộ Writer (`sw/messages.po`): 3.214 chuỗi còn thiếu, dịch song song bằng 11 subagent theo bảng thuật ngữ, qua bước kiểm biến và phím tắt; `sw` đạt 5.353/5.353 (100%) | 3.214 | Ảnh `docs/ui/writer-vi-full-2026-11-13.png`. Mặc định giao diện là tiếng Anh (chủ dự án chốt 13/11/2026), tiếng Việt chọn trong Tùy chọn |
| 13/11/2026 | Ribbon Writer (`notebookbar.ui`) và nhãn của 415 lệnh trên ribbon đó | 97 + 353 | Nhiều bản dịch nháp cũ sai nghĩa ("Reject All" → "Chọn tất cả", "Orientation" → "Trình chiếu", "Next" → "Văn bản"); đã dịch lại theo `l10n/vi/glossary.csv` |

Kết quả trên bản build release (ảnh `docs/ui/writer-1xvnoffice-vi-2026-11-13.png`): toàn bộ thẻ, nhóm và nút của ribbon Writer đã tiếng Việt; tên sản phẩm 1xVnOffice; không còn hộp chào mừng, mẹo hằng ngày hay thanh mời quyên góp khi mở app.

Còn tiếng Anh, làm ở lượt sau: tên kiểu đoạn ("Default Paragraph Style", "Body Text", "Block Quotation"), thanh trạng thái ("0 words, 0 characters", "Default Page Style", "Insert"). Ngôn ngữ tài liệu mặc định vẫn là "Anh (Mỹ)", cần đổi sang tiếng Việt để kiểm tra chính tả đúng.

Bài học: kiểm tra `msgfmt` là chưa đủ. Bộ đọc của LibreOffice (`cfgex`) bỏ qua không báo lỗi khi chuỗi nhiều dòng bị ghi gộp một dòng, nên bước `defaults` giờ đọc thẳng nhãn lệnh tiếng Việt từ ứng dụng đang chạy.

Cách làm: `scripts/l10n-merge.py` trộn `l10n/vi/**.po` vào cây dịch trước khi build (bước `l10n` của `build-macos.sh`); bộ đọc/ghi PO tự viết (`scripts/po.py`) giữ nguyên dòng gốc, ghi lại file không đổi giống hệt từng byte.

## Thứ tự làm

1. Đo trước: chụp ribbon Tabbed hiện có của LibreOffice 26.8 sau khi build xong, lập `command-map.csv` cho Writer.
2. Viết lại `notebookbar.ui` của Writer theo bảng đối chiếu, rồi tới Calc và Impress.
3. Sinh bộ icon Fluent cho các lệnh có mặt trên ribbon (khoảng 400 icon), sau đó mới tới phần còn lại.
4. Backstage "Tệp" và trang chủ.
5. Thẻ tài liệu.

## Không làm

- Không chép bố cục pixel, ảnh, icon của WPS hay Microsoft.
- Không giữ menu cổ điển làm mặc định. Người dùng vẫn chuyển được trong Xem ▸ Giao diện người dùng.
