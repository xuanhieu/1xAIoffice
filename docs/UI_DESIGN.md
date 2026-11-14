# Giao diện 1xVnOffice

Chủ dự án chốt ngày 13/11/2026: **không dùng giao diện upstream**. Bố cục và cách làm việc theo kiểu WPS Office, chất lượng hướng tới Microsoft Office 2026.

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

Giới hạn thật: VCL (bộ giao diện của upstream) không có hiệu ứng trong mờ và chuyển động như Office. Bản 1.0 nhắm tới bố cục, icon, khoảng cách và phông chữ ngang Office; không hứa giống từng điểm ảnh.

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
| 8 | Ô "Tìm lệnh" (Alt+Q) có tìm không dấu | Dùng tính năng tìm lệnh có sẵn của upstream, thêm chuẩn hoá tiếng Việt | 3 |
| 9 | Thanh truy cập nhanh trên thanh tiêu đề (Lưu, Hoàn tác, Làm lại) | Cấu hình notebookbar | 2 |
| 10 | Khung trợ lý AI bên phải | Giai đoạn 8 (`ai-platform-design.md`) | 8 |

## Nhận diện và theme "Sơn mài" (13/11/2026)

Chủ dự án không muốn theme mặc định của upstream. Hướng đã làm:

- **Brief:** nền than chì ánh xanh (`#17181C`–`#24252B`), một màu nhấn cobalt `#4C7DFF`, vàng chỉ dùng trong logo. Lấy cảm hứng từ sơn mài Việt (nền sẫm, vàng), để có bản sắc riêng, khác cả xám trắng của upstream lẫn đỏ của WPS.
- **Một nguồn token:** `branding/tokens.json`. `scripts/brand/make-brand.py` sinh ra mọi thứ từ đó:
  - logo "1x" (khối squircle, nét x màu vàng), wordmark Noto Sans (OFL) đã đổi thành đường nét;
  - logo sáng và tối cho About và Start Center, nền About, splash hai cỡ, icon app `main.icns`;
  - icon theme `images_1x.zip`;
  - lớp cấu hình `config/1x-theme.xcd`.
- **Theme:** dùng cơ chế ColorScheme của upstream 26.8 (`LibreOfficeTheme=1`, scheme `1xVnOffice`). Plugin macOS có áp các màu này. Không vá mã lõi. Người dùng vẫn đổi về Automatic/Light/Dark được trong Options.
- **Icon theme "1x":** chỉ chứa icon đã thay, ở dạng SVG nên sắc nét trên Retina. Icon nào chưa có thì upstream tự lấy từ `colibre_dark`. Vì vậy có thể thay dần sang bộ Fluent (mục 6) mà không phải làm hết một lần.
- **Start Center:**
  - Bản vá `0001-startcenter-1x-labels.patch` đổi tên ứng dụng thành 1xDoc/1xSheet/1xSlide.
  - Bản dịch tiếng Việt cho Start Center nằm ở `l10n/vi/sfx2/messages.po`. `l10n-merge.py` khớp theo msgctxt khi chữ gốc tiếng Anh do chính 1x đổi.
  - Nút quyên góp cho TDF đã tắt (`ShowDonation=false`).
- **Còn thiếu so với trang chủ kiểu WPS:** ô tìm tài liệu ở đầu trang, thẻ tài liệu (mục 4), khung đề xuất bên phải, danh sách gần đây dạng bảng (tên, nơi lưu, ngày sửa). Các phần này cần viết lại `BackingWindow` (sfx2, C++) hoặc làm trang chủ riêng. Đây là việc kế tiếp của mục 5.

## Logo "tất cả trong một" và bộ nhận diện riêng (13/11/2026)

- **Logo:** số 1 ở giữa, vòng quỹ đạo nghiêng quanh nó, ba vệ tinh là ba ứng dụng: 1xDoc (xanh dương, trang chữ), 1xSheet (xanh lá, bảng), 1xSlide (cam, màn chiếu). Nửa trước của vòng đi qua phía trước số 1. Sinh bằng `scripts/brand/make-brand.py` từ `branding/tokens.json`; chữ "1x" vàng trong wordmark.
- **Gỡ thương hiệu cũ khỏi những gì người dùng nhìn thấy:**
  - Hộp About: `patches/source/0002-about-1x.patch` đổi mô tả, dòng bản quyền, dòng nhà phát hành và bỏ liên kết build id về kho upstream; bản dịch ở `l10n/vi/cui`.
  - Địa chỉ web của Trợ giúp, About, Start Center và Extension Manager: `config/1x-identity.xcd` (chỉ dùng gốc `1xag.com`, `xuanhieu.org` và kho GitHub công khai, không dựa vào trang con chưa có).
  - README, NOTICE, hướng dẫn trong app và tài liệu kỹ thuật không nhắc tên cũ; thư mục `upstream/` và `patches/source/` đổi tên theo.
- **Nội dung giới thiệu** (chủ sở hữu, sứ mệnh, tầm nhìn, điểm khác biệt) nằm ở `branding/about.json`, một nguồn cho README và hướng dẫn trong app. Phần "đã dùng được" chỉ liệt kê thứ chạy thật; thứ chưa xong nằm ở "đang làm tiếp".
- **Phần phải giữ theo giấy phép:** hộp License của ứng dụng (thông báo MPL-2.0 và giấy phép bên thứ ba), tệp `LICENSE`, `NOTICE`, `CREDITS` trong thư mục tài nguyên của bộ cài, và tiêu đề bản quyền trong từng file nguồn. Đây là điều kiện của giấy phép, không phải thương hiệu, nên không gỡ.
- **Còn sót, không nhìn thấy trong giao diện:** tên khoá cấu hình `LibreOfficeTheme`, mã định danh gói macOS `org.libreoffice.script`, tên tarball và địa chỉ tải trong `upstream/source-lock.json`. Đổi mã định danh gói cần build lại cả bộ cài.

## Mã VietQR trong hướng dẫn (13/11/2026)

Mục "Ủng hộ tác giả" trong hướng dẫn 1xDoc có mã VietQR nằm sẵn trong tệp, không cần mạng và không gửi số tài khoản ra dịch vụ ngoài khi build.

- `scripts/brand/vietqr.py` dựng chuỗi theo chuẩn EMVCo của NAPAS (CRC-16/CCITT-FALSE); `scripts/brand/qr.py` vẽ mã QR thuần Python (chế độ byte, phiên bản 1–10, mức L/M).
- Mã sinh ra là **mã tĩnh**, không ghi sẵn số tiền, để người ủng hộ tự chọn mức; các mức gợi ý vẫn in bằng chữ bên cạnh.
- **Ba lớp kiểm**, vì một mã QR sai sẽ đưa tiền đi đâu không biết:
  1. `scripts/tests/test_qr.py` (chạy cả trên CI): chuỗi dựng ra phải trùng từng ký tự với một mã VietQR thật của chủ tài khoản, kể cả CRC; bit thông tin định dạng và phiên bản phải khớp bảng trong tiêu chuẩn.
  2. `scripts/check-vietqr.sh` (macOS): vẽ ảnh rồi giải mã lại bằng CoreImage và so với chuỗi gốc.
  3. Trước khi phát hành: lấy ảnh ra khỏi chính tệp .docx và .pdf đã sinh rồi giải mã (đã làm ngày 13/11/2026, cả hai ngôn ngữ đều đúng).
- Bộ vẽ đã được quét đủ 20 tổ hợp phiên bản 1–10 × mức L/M ở sức chứa tối đa, giải mã lại đúng hết. Chuỗi dài hơn sức chứa phiên bản 10 thì báo lỗi thay vì vẽ sai.
- Bài học: phần dư BCH của thông tin định dạng và phiên bản phải tính từ **dữ liệu gốc**, không phải dữ liệu đã dịch trái. Sai chỗ này thì mã vẫn ra hình đúng kiểu nhưng máy quét không đọc được.

## Ribbon gọn kiểu WPS / Office (13/11/2026)

- **Icon Fluent:** `branding/fluent-map.json` ánh xạ 232 lệnh ribbon sang Fluent UI System Icons (MIT). `make-brand.py --fluent <icons>` sinh đủ ba cỡ (`cmd/sc_`, `cmd/lc_`, `cmd/32/`) vào `images_1x.zip`, nét màu `#E3E5EB` hợp nền than chì. Lệnh chưa có trong bảng dùng icon `colibre_dark`; muốn thêm lệnh thì chỉ cần sửa file JSON.
- **Bố cục:** bước build `ribbon` (`scripts/ui/ribbon.py`) ghi lại `notebookbar.ui` đã cài của Writer, Calc, Impress và Draw từ bản gốc, chạy lại không cộng dồn và không cần build lại lõi.
  - Ẩn tên nhóm (239 nhãn).
  - Cut, Copy, Clear chỉ hiện icon.
  - Nút lớn giữ nguyên như bản gốc; chỉ hạ những nút đã nhìn tận mắt thấy gây hại (`DEMOTE_LARGE`).
  - Vạch ngăn nhóm, thêm 14/11/2026 (xem mục dưới).

## Nhịp nhóm trên ribbon, đo từ WPS (14/11/2026)

Gỡ tên nhóm xong mà không thay bằng gì thì cả dải chỉ còn một hàng icon, không phân biệt được nhóm nào với nhóm
nào. WPS cũng không ghi tên nhóm, nhưng nó giữ **vạch ngăn và nhịp khoảng cách**. Số đo lấy từ chính bộ cài WPS
Office trên máy (`Resources/office6/skins/2018white_dark/*.kuip`, là XML token thường):

| Thứ | WPS (nền tối) | 1xVnOffice làm theo |
|---|---|---|
| Thang khoảng cách | 0 / 4 / 8 / 12 / 16 / 20 / 24 / 32 | `GROUP_GAP = 6` mỗi bên vạch → 12px giữa hai nhóm |
| Vạch ngăn | trắng 10% (`#FFFFFF1A`); loại đậm hơn là 20% | theo màu đường kẻ của theme |
| Kiểu vạch | gradient, mờ hẳn ở 20% trên và 20% dưới nên không cắt ngang cả dải | `SEPARATOR_INSET = 6`: vạch ngắn hơn chiều cao nhóm (VCL không vẽ được gradient) |
| Bo góc | 4 và 6 | theme đang dùng |
| Nền | `#2D2D2D` (dải lệnh), `#1E1E1E` (vùng sâu), `#323233` (nổi) | đối chiếu với `config/1x-theme.xcd` |

Chỉ lấy **số đo và cách làm**, không chép tài nguyên của WPS vào kho.

**Ba bẫy đã gặp, đều chỉ lộ ra khi mở app thật, không bài kiểm nào bắt được:**

1. Nhóm của bản gốc mang `packing/position` 0,1,2… Vạch ngăn mới không có `position` thì VCL coi như 0 và dồn
   hết chúng về mép trái thành ba bốn vạch dính nhau. Phải đánh số lại cả hộp (`_renumber`).
2. Nhóm rỗng hoặc đang ẩn mà vẫn kèm vạch ngăn thì ribbon đầy vạch thừa, nên `_has_content` bỏ qua chúng.
3. **Cụm lệnh tiếng Việt bị vẽ ngoài cùng bên trái** dù đã khai ở cuối thẻ Home. Nguyên nhân nằm trong
   `vcl/source/window/builder.cxx`: dựng xong một hộp, VCL sắp lại toàn bộ con theo `m_nPosition`
   (`sortIntoBestTabTraversalOrder`), mà con nào không có `position` thì mặc định là **-1**. Các cụm lệnh của
   extension do `NotebookBarAddonsMerger::MergeNotebookBarAddons` dựng thẳng bằng C++, không đi qua packing của
   tệp `.ui`, nên luôn mang -1 — tức luôn đứng trước mọi nhóm đánh số 0,1,2…
   Cách chữa: `_renumber` đánh số **âm** (-n-1 … -2) cho những gì mình điều khiển được, thế là -1 của extension
   thành lớn nhất và cụm lệnh tiếng Việt về đúng cuối dải. Không vá lõi, chỉ dùng đúng cơ chế sẵn có.

**Nút lớn tên dài là thủ phạm của mảng trống giữa ribbon.** `.uno:ToggleMergeCells` ("Merge and Center Cells")
là nút lớn chữ-dưới-icon của bản gốc; tên dài kéo cả cột rộng ra, và khi lệnh bị vô hiệu (chọn một ô) nó trông
như một dòng chữ xám lơ lửng. Hạ xuống chỉ-icon là hết. Không hạ hàng loạt: ribbon của mình vốn đã ít chữ hơn
WPS, mỗi nút lớn bị hạ là mất thêm một cái nhãn.

**Vì sao chưa gắn chữ cho nhiều lệnh như WPS:** WPS ghi chữ cạnh gần như mọi lệnh trên Home (Wrap Text, Merge,
Rows and Columns, Sheets, Fill, AutoSum, Sort, Filter, Find, Freeze Panes). Bên LibreOffice phần lớn cụm trên
Home là **một toolbox chứa nhiều lệnh** (ví dụ `bxHomeCharFormat` gồm B, I, U, S), nên bật chữ sẽ gắn chữ cho
từng nút một chứ không gắn cho cả cụm. Muốn giống WPS phải tách cụm ra, là việc khác và lớn hơn.
- **Còn khác WPS:**
  - Thẻ đang chọn vẫn vẽ dạng viên thuốc, vì plugin macOS (Aqua) tự vẽ cả vùng thẻ.
  - Chưa có thẻ tài liệu trên thanh tiêu đề.
  - Impress còn hàng công cụ vẽ và thanh Properties.
  - Thẻ "Extension" vẫn hiện.
  - Chưa có nút NĐ30 và công cụ tiếng Việt ngay trên thẻ Home.
  - Dải thẻ (File | Home | Insert…) có vạch ngăn giữa các thẻ, WPS thì không có. **Nguyên nhân** (đã tra,
    14/11/2026): `vcl/osx/salnativewidgets.cxx` vẽ mỗi `ControlType::TabItem` bằng một **NSSegmentedControl**
    ba ô của macOS, và chính NSSegmentedControl vẽ vạch ngăn giữa các ô. Vạch đó không nằm trong tệp `.ui`
    nên `ribbon.py` không với tới được.
    Ba cách chữa, đều đắt hơn hẳn những việc đã làm: (a) `EnableNativeWidget(false)` trên thẻ ribbon — **không
    dùng được**, vì nó lan xuống mọi con nên cả dải lệnh mất kiểu vẽ gốc của hệ điều hành; (b) báo
    `ControlType::TabItem` là không hỗ trợ trong plugin macOS — ảnh hưởng mọi hộp thoại có thẻ trong cả bộ;
    (c) vá `vcl/source/control/tabctrl.cxx` thêm một cờ chỉ tắt vẽ-gốc cho thẻ của notebookbar, rồi dựng lại
    lõi. Chỉ (c) là đúng phạm vi, nhưng cần vá lõi và build lại.
  - Còn trống khoảng một phần ba bề ngang bên phải dải lệnh.

## Bộ hướng dẫn nhanh đi kèm (13/11/2026)

- `scripts/guides/make-guides.py` dùng chính 1xVnOffice sinh ra 1xDoc (.docx, kèm .pdf), 1xSheet (.xlsx) và 1xSlide (.pptx), mỗi file có bản tiếng Anh và tiếng Việt. Nội dung do 1x tự viết, ảnh là ảnh chụp 1xVnOffice. Bước build `guides` cài chúng vào `App/Contents/Resources/guides/<lang>/`, kèm ảnh xem trước trang đầu.
- Hướng dẫn 1xSheet là bảng chạy được: đổi số lượng thì thành tiền, số tiền bằng chữ (DOCTIEN) và biểu đồ tự cập nhật. Bảng có sẵn lọc, cố định dòng tiêu đề và định dạng có điều kiện.
- Lần chạy đầu, job `GuideSeeder` (sự kiện `onFirstRunInitialization`) đưa ba hướng dẫn vào mục Gần đây theo ngôn ngữ giao diện, rồi nạp lại Start Center. Job chỉ chạy khi mục Gần đây còn trống.
- Bài học: upstream headless trên macOS bị abort trong `AquaSalMenu::setMainMenu` khi mở một tài liệu ẩn (`Hidden=True`) hoặc một cửa sổ tài liệu thứ hai. Vì vậy mỗi tệp được sinh trong một phiên soffice riêng, với tài liệu hiển thị.

## Số đo gốc (13/11/2026)

`scripts/ui-coverage.py` so ribbon với bảng đối chiếu `docs/ui/writer-command-map.csv` (86 lệnh chính của Word: Trang đầu, Chèn, Thiết kế, Bố cục, Tham chiếu, Thư, Xem lại, Xem).

| Ribbon | Đúng thẻ | Sai thẻ | Thiếu | Chi tiết |
|---|---|---|---|---|
| upstream 26.8 Writer, `notebookbar.ui` gốc | 70/86 (81%) | 15 | 1 | `docs/ui/baseline-writer-upstream-26.8.md` |
| Mục tiêu 1xDoc 1.0 | 86/86 (100%) | 0 | 0 | CI chạy script với `--min 1.0` khi ribbon của 1x nằm trong repo |

Những lệnh lệch chính: đầu trang, chân trang, số trang, ngày giờ, chú thích, dòng chữ ký đang ở thẻ khác thay vì "Chèn"; hình mờ ở "Bố cục" thay vì "Thiết kế" (upstream không có thẻ Thiết kế); trộn thư ở "Công cụ" thay vì "Thư"; "Sắp xếp" không có trên ribbon.

### Bản build đầu tiên (13/11/2026)

- Ribbon dạng thẻ đã là mặc định trong cả bốn ứng dụng nhờ `config/1x-defaults.xcd`. Ảnh: `docs/ui/writer-ribbon-baseline-2026-11-13.png` (so với giao diện cổ điển trước đó: `docs/ui/writer-classic-upstream-2026-11-13.png`).
- **Bản dịch tiếng Việt của upstream 26.8 mới đạt 62% giao diện** (20.444/32.460 chuỗi; Writer `sw` 38%, `svx` 50%, `sfx2` 54%, `vcl` 55%, `cui` 85%). Hậu quả: ribbon lẫn Anh–Việt ("Home", "Insert", "Cut" chưa dịch; "Dán", "Tiêu đề 1" đã dịch).
- Đã sửa (13/11/2026): tên sản phẩm, hộp chào mừng, hộp About và các địa chỉ web đều là của 1xVnOffice (xem mục Nhận diện và Bộ nhận diện riêng).

### Bản dịch tiếng Việt của 1x (việc mới, giai đoạn 2)

1. Lớp dịch riêng `l10n/vi/` (các file `.po` bổ sung) được trộn vào `translations/source/vi` trước khi build. Script kiểm: không chuỗi nào của các module giao diện chính bị thiếu.
2. Bảng thuật ngữ theo cách gọi quen thuộc của Word, Excel, PowerPoint tiếng Việt (Trang đầu, Chèn, Bố cục, Tham chiếu, Xem lại…); đặt dấu thanh theo một quy ước thống nhất (cần chủ dự án chốt: "hóa" hay "hoá"); phím tắt không trùng trong cùng hộp thoại.
3. Dịch khoảng 12.000 chuỗi còn thiếu bằng AI theo bảng thuật ngữ, người duyệt lại phần hiện trên ribbon và hộp thoại phổ biến trước.
4. Gửi bản dịch về Weblate của upstream để giảm phần phải tự giữ.
5. Mục tiêu bản 1.0: 100% chuỗi của `sfx2 sw sc sd svx cui vcl framework` có tiếng Việt.

Tiến độ:

| Ngày | Phạm vi | Số chuỗi | Ghi chú |
|---|---|---|---|
| 13/11/2026 | Toàn bộ Writer (`sw/messages.po`): 3.214 chuỗi còn thiếu, dịch song song bằng 11 subagent theo bảng thuật ngữ, qua bước kiểm biến và phím tắt; `sw` đạt 5.353/5.353 (100%) | 3.214 | Ảnh `docs/ui/writer-vi-full-2026-11-13.png`. Mặc định giao diện là tiếng Anh (chủ dự án chốt 13/11/2026), tiếng Việt chọn trong Tùy chọn |
| 13/11/2026 | Ribbon Writer (`notebookbar.ui`) và nhãn của 415 lệnh trên ribbon đó | 97 + 353 | Nhiều bản dịch nháp cũ sai nghĩa ("Reject All" → "Chọn tất cả", "Orientation" → "Trình chiếu", "Next" → "Văn bản"); đã dịch lại theo `l10n/vi/glossary.csv` |

Kết quả trên bản build release (ảnh `docs/ui/writer-1xvnoffice-vi-2026-11-13.png`): toàn bộ thẻ, nhóm và nút của ribbon Writer đã tiếng Việt; tên sản phẩm 1xVnOffice; không còn hộp chào mừng, mẹo hằng ngày hay thanh mời quyên góp khi mở app.

Còn tiếng Anh, làm ở lượt sau: tên kiểu đoạn ("Default Paragraph Style", "Body Text", "Block Quotation"), thanh trạng thái ("0 words, 0 characters", "Default Page Style", "Insert"). Ngôn ngữ tài liệu mặc định vẫn là "Anh (Mỹ)", cần đổi sang tiếng Việt để kiểm tra chính tả đúng.

Bài học: kiểm tra `msgfmt` là chưa đủ. Bộ đọc của upstream (`cfgex`) bỏ qua không báo lỗi khi chuỗi nhiều dòng bị ghi gộp một dòng, nên bước `defaults` giờ đọc thẳng nhãn lệnh tiếng Việt từ ứng dụng đang chạy.

Cách làm: `scripts/l10n-merge.py` trộn `l10n/vi/**.po` vào cây dịch trước khi build (bước `l10n` của `build-macos.sh`); bộ đọc/ghi PO tự viết (`scripts/po.py`) giữ nguyên dòng gốc, ghi lại file không đổi giống hệt từng byte.

## Thứ tự làm

1. Đo trước: chụp ribbon Tabbed hiện có của upstream 26.8 sau khi build xong, lập `command-map.csv` cho Writer.
2. Viết lại `notebookbar.ui` của Writer theo bảng đối chiếu, rồi tới Calc và Impress.
3. Sinh bộ icon Fluent cho các lệnh có mặt trên ribbon (khoảng 400 icon), sau đó mới tới phần còn lại.
4. Backstage "Tệp" và trang chủ.
5. Thẻ tài liệu.

## Không làm

- Không chép bố cục pixel, ảnh, icon của WPS hay Microsoft.
- Không giữ menu cổ điển làm mặc định. Người dùng vẫn chuyển được trong Xem ▸ Giao diện người dùng.

## Cắt (Cmd+X) giữ ô tới khi dán (14/11/2026)

Bản gốc LibreOffice Calc **xoá ô ngay** khi bấm Cut. Excel, WPS và Google Sheets đều giữ nguyên nội dung, vẽ
viền đứt quanh vùng nguồn, và chỉ chuyển khi người dùng dán; bấm Esc là bỏ. Khác nhau ở đây là **ngữ nghĩa**,
không phải hiệu ứng: người quen ba phần mềm kia mà cắt xong đổi ý sẽ tưởng vừa mất dữ liệu.

Bản vá `patches/source/0003-calc-cut-keeps-cells-until-paste.patch`:

| Chỗ | Làm gì |
|---|---|
| `ScModule` | Giữ vùng đang chờ cắt: `SetPendingCut`, `ClearPendingCut` |
| `ScViewFunc::CutToClip` | Chép vào clipboard rồi **ghi nhớ** vùng nguồn thay vì xoá |
| `ScViewFunc::PasteFromClip` | Xoá vùng nguồn ngay sau khi mở nhóm hoàn tác, nên Ctrl+Z một lần trả lại cả hai đầu |
| `SID_CANCEL` (cellsh3) | Esc bỏ vùng đang chờ, dữ liệu giữ nguyên |
| `ScGridWindow` (gridwin4) | Vẽ viền đứt màu xanh thương hiệu quanh vùng đang chờ |

Calc vốn đã có `ScClipParam::mbCutMode` để chỉnh tham chiếu công thức khi dán dữ liệu cắt, nên phần khó nhất
đã có sẵn; việc của bản vá chỉ là **dời thời điểm xoá**.

**Hai chỗ cố ý giữ cách cũ:** vùng chọn nhiều mảnh (`IsMultiMarked`) vẫn xoá ngay, vì gộp nhiều mảnh vào một
bước hoàn tác cần thêm việc; và vùng nguồn **chồng lên** vùng đích thì không xoá, vì phần chồng nhau vừa bị
ghi đè, xoá tiếp là mất dữ liệu thật.

**Chưa có:** viền chạy (marching ants). Viền hiện đứng yên. Muốn chạy phải thêm một bộ đếm giờ vẽ lại viền
theo nhịp, làm sau.

Kiểm: `scripts/build-macos.sh tools`, phần `cut` — bảy bước gồm cắt, dán, Ctrl+Z một lần, và Esc rồi dán.
