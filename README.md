# 1xAIoffice

Bộ văn phòng trọn gói, miễn phí và riêng tư của người Việt: 1xDoc, 1xSheet, 1xSlide trong một ứng dụng.

Sản phẩm của [xuanhieu.org](https://xuanhieu.org) và [1xag.com](https://1xag.com). Trạng thái: **đang phát triển, chưa phát hành bản cài**.

## Giới thiệu 1xAIoffice

Bộ văn phòng trọn gói, miễn phí và riêng tư của người Việt: 1xDoc, 1xSheet, 1xSlide trong một ứng dụng.

**Ai làm ra.** xuanhieu.org là nơi tác giả làm việc về tìm kiếm, nội dung và phần mềm. 1xag.com là hệ sản phẩm 1X, nhà của 1xAIoffice.

**Sứ mệnh.** Mang đến cho mọi người Việt, từ cơ quan nhà nước, doanh nghiệp đến cá nhân, một bộ văn phòng hiện đại, miễn phí, tôn trọng quyền riêng tư và hiểu tiếng Việt.

**Tầm nhìn.** Một bộ văn phòng người Việt tin dùng mỗi ngày: mở được các tệp nhận về, soạn đúng thể thức văn bản hành chính Việt Nam, và để mỗi người gắn trợ lý AI của riêng mình.

**Đã dùng được hôm nay**

- Một ứng dụng cho văn bản, bảng tính và trình chiếu, mặc định lưu .docx, .xlsx, .pptx.
- Giao diện tiếng Việt đầy đủ, đổi từ tiếng Anh trong Tuỳ chọn.
- Trình soạn văn bản hành chính theo Nghị định 30/2020/NĐ-CP (khổ giấy, lề, phông chữ, khối chữ ký).
- Công cụ tiếng Việt: chuyển mã TCVN3 sang Unicode, chuẩn hoá Unicode, bỏ dấu, đọc số và đọc tiền thành chữ (DOCSO, DOCTIEN trong 1xSheet).
- Không quảng cáo, không nhắc nâng cấp, không theo dõi; macro bị chặn trừ khi bạn tin cậy.

**Đang làm tiếp**

- Đo độ tương thích với Microsoft Office trên bộ tài liệu thật của Việt Nam.
- Ký số bằng USB Token.
- Nền tảng AI mở: khoá API riêng, máy chủ MCP, plugin và skill của bạn.
- Triển khai hàng loạt cho tổ chức.

**Điểm khác biệt**

- Miễn phí trước: không thu phí, không quảng cáo, không nhắc nâng cấp trong ứng dụng.
- Làm cho công việc của người Việt: văn bản hành chính và công cụ tiếng Việt có sẵn, không phải tiện ích cài thêm.
- Riêng tư mặc định: không gửi gì ra ngoài trừ khi bạn bật.
- Mở: mã nguồn công khai theo giấy phép MPL-2.0.

**Ủng hộ tác giả**

1xAIoffice miễn phí và không quảng cáo. Nếu phần mềm giúp ích cho bạn, mời Xuân Hiếu ly cafe: quét mã VietQR bằng ứng dụng ngân hàng bất kỳ, hoặc chuyển khoản, từ 50.000đ.

<img src="branding/out/vietqr.svg" alt="VietQR" width="180">

**MB Bank** · `9112233449` · PHAM XUAN HIEU  
50.000đ · 100.000đ · 200.000đ · 500.000đ · [Trang ủng hộ](https://1xag.com/?donate)

---

## About 1xAIoffice

The free, private, all-in-one office suite for Vietnam: 1xDoc, 1xSheet and 1xSlide in one app.

**Who makes it.** xuanhieu.org is the home of the author's work on search, content and software. 1xag.com is the 1X product family that 1xAIoffice belongs to.

**Mission.** Give everyone in Vietnam, from government agencies and businesses to individuals, a modern office suite that is free, respects privacy and understands Vietnamese.

**Vision.** An office suite people in Vietnam trust every day: it opens the files they receive, writes Vietnamese administrative documents correctly, and lets each person plug in their own AI assistant.

**What works today**

- One app for documents, spreadsheets and presentations, saved as .docx, .xlsx and .pptx by default.
- Full Vietnamese interface, switchable from English in Options.
- Administrative document composer following Decree 30/2020/ND-CP (layout, margins, fonts, signature block).
- Vietnamese tools: TCVN3 to Unicode, Unicode normalization, remove diacritics, number and amount in words (DOCSO, DOCTIEN in 1xSheet).
- No ads, no upgrade prompts and no tracking; macros are blocked unless you trust them.

**On the roadmap**

- Measured compatibility with Microsoft Office on a collection of real Vietnamese documents.
- Digital signatures with USB tokens.
- An open AI platform: your own API keys, MCP servers, plugins and skills.
- Managed deployment for organizations.

**Why it is different**

- Free first: no payment, no ads and no upgrade prompts inside the app.
- Made for Vietnamese work: administrative documents and text tools are built in, not add-ons.
- Private by default: nothing is sent anywhere unless you turn it on.
- Open: the code is public under the MPL-2.0 license.

**Support the author**

1xAIoffice is free and has no ads. If it helps you, you can buy Xuân Hiếu a coffee: scan the VietQR code with any Vietnamese banking app, or transfer, from 50,000 VND.

<img src="branding/out/vietqr.svg" alt="VietQR" width="180">

**MB Bank** · `9112233449` · PHAM XUAN HIEU  
50.000đ · 100.000đ · 200.000đ · 500.000đ · [Donation page](https://1xag.com/en/?donate)

---

## Cấu trúc repo

| Thư mục | Nội dung |
|---|---|
| `branding/` | Nhận diện: màu, logo, nội dung giới thiệu (nguồn của hướng dẫn trong app) |
| `config/` | Cấu hình mặc định, theme, địa chỉ web |
| `build-config/` | Tuỳ chọn build cho từng nền tảng, mỗi dòng có lý do |
| `patches/` | Bản vá nguồn (càng ít càng tốt), theo thứ tự trong `series` |
| `l10n/` | Bản dịch tiếng Việt |
| `scripts/` | Tải nguồn, build, sinh logo và hướng dẫn, kiểm tra repo |
| `extensions/` | Công cụ tiếng Việt (`1xvn-tools`) |
| `docs/` | Hướng dẫn build và tài liệu kỹ thuật |

Build trên macOS: [docs/BUILD.md](docs/BUILD.md).

## Giấy phép

Mã trong repo theo MPL-2.0 (`LICENSE`). Phần mềm và phông chữ bên thứ ba, cùng giấy phép của chúng, xem `NOTICE.md` và mục License trong ứng dụng.
