# Build 1xAIoffice trên macOS

## Yêu cầu

- macOS trên Apple Silicon, Xcode (đã cài ở `/Volumes/SSD1Tb-Black-APFS/Developer/Xcode.app`).
- Ổ ngoài có ít nhất 80 GiB trống. Mặc định mọi thứ lớn nằm ở `/Volumes/SSD1Tb-Black-APFS/Developer/1xvnoffice-work`; đổi bằng biến `ONEX_WORK`.
- Công cụ build nằm trong một Homebrew riêng trên SSD (`$ONEX_BREW`, mặc định `/Volumes/SSD1Tb-Black-APFS/Developer/homebrew-1x`), không cài gì vào `/opt/homebrew` hay ổ trong. Lần đầu chạy (10–20 phút):

```bash
scripts/bootstrap-tools.sh
```

Configure và make chạy với PATH sạch: thư mục hệ thống cộng `$ONEX_WORK/toolbin` (liên kết tới đúng các công cụ cần dùng). `pkg-config` được trỏ tới một thư mục tìm kiếm rỗng để thư viện của Homebrew không lẫn vào bản build.

## Các bước

```bash
scripts/fetch-source.sh --dry-run
```

```bash
scripts/fetch-source.sh
```

```bash
scripts/build-macos.sh preflight extract patch l10n configure
```

```bash
scripts/build-macos.sh build config extensions sign smoke defaults tools
```

- `fetch-source.sh` tải bốn tarball (khoảng 625 MB), kiểm kích thước, SHA-256 trong `upstream/source-lock.json` và chữ ký OpenPGP của upstream Build Team (kiểm bằng `sqv`, khoá lưu ở `upstream/source-signing-key.asc`). Sai một trong ba là dừng.
- `build` lần đầu mất vài giờ; ccache nằm ở `$ONEX_WORK/ccache` (tối đa 20 GB) nên các lần sau nhanh hơn nhiều.
- `sign` ký ad-hoc (`codesign -s -`), đủ để chạy trên Apple Silicon. Developer ID và notarization làm khi có doanh thu.
- `smoke` chuyển một file chữ tiếng Việt sang PDF ở chế độ không giao diện để xác nhận bản build chạy được.
- `extensions` đóng gói `extensions/*` thành `.oxt` (`scripts/build-extensions.py`) và cài vào app dạng extension đi kèm.
- `tools` gọi các lệnh tiếng Việt trên tài liệu Writer và Calc thật, mỗi loại trong một phiên soffice riêng (trên macOS, upstream 26.8 chạy headless bị dừng khi tạo tài liệu Calc sau tài liệu Writer).
- `l10n` trộn lớp dịch `l10n/vi/` vào bản dịch upstream và xoá file `.mo` của các module bị đổi (gbuild không tự biên dịch lại khi `.po` đổi).
- `defaults` mở một profile mới ở chế độ không giao diện, kiểm 15 giá trị mặc định của `config/1x-defaults.xcd` và đọc nhãn tiếng Việt của lệnh Cắt từ ứng dụng đang chạy.

Log nằm ở `$ONEX_WORK/logs/`.

## Đổi phiên bản upstream

1. Lấy tên tarball, SHA-256 (trang `.mirrorlist` trên download.documentfoundation.org) và commit (`git ls-remote --tags https://git.libreoffice.org/core 'refs/tags/libreoffice-<phiên bản>*'`).
2. Sửa `upstream/source-lock.json`.
3. Chạy `python3 scripts/check-repo.py`, rồi build lại.

## Trước khi push: chạy đúng các bước của CI tại máy

`scripts/ci-local.sh` đọc các bước `run:` trong `.github/workflows/quality.yml` và chạy y nguyên (khoảng 40 giây), nên
máy và CI không thể lệch nhau. Hook `.githooks/pre-push` gọi nó trước mỗi lần push và chặn push nếu có bước hỏng.
Một lần cho mỗi bản clone: `git config core.hooksPath .githooks` và `brew install shellcheck`.

Lý do (15/11/2026): CI hỏng năm lần push liền vì shellcheck báo SC2043 mà máy làm việc không có shellcheck.
