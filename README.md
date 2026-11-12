# 1xVnOffice

Bộ văn phòng tiếng Việt cho Windows, macOS và Linux: **1xDoc** (văn bản), **1xSheet** (bảng tính), **1xSlide** (trình chiếu). Dựa trên LibreOffice. Miễn phí, không quảng cáo, không theo dõi, cho người dùng tự gắn mô hình AI, MCP, plugin và skill.

Trạng thái: **đang dựng dây chuyền build (giai đoạn 1)**. Chưa có bản cài.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| `upstream/libreoffice-lock.json` | Phiên bản LibreOffice được khoá: tarball, SHA-256, kích thước, khoá ký OpenPGP, commit |
| `build-config/` | Tuỳ chọn `configure` cho từng nền tảng, mỗi dòng có lý do |
| `patches/libreoffice/` | Bản vá lõi (càng ít càng tốt), theo thứ tự trong `series` |
| `scripts/` | Tải nguồn, build, kiểm tra repo |
| `extensions/` | Extension tiếng Việt và nền tảng AI (giai đoạn 3 và 8) |
| `docs/` | Hướng dẫn build và tài liệu kỹ thuật |

## Build trên macOS

Xem [docs/BUILD.md](docs/BUILD.md).

## Giấy phép

Mã trong repo: MPL-2.0 (`LICENSE`). Ghi công LibreOffice: `NOTICE.md`.
