# Build 1xVnOffice trên macOS

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
scripts/build-macos.sh preflight extract patch configure
```

```bash
scripts/build-macos.sh build config sign smoke defaults
```

- `fetch-source.sh` tải bốn tarball (khoảng 625 MB), kiểm kích thước, SHA-256 trong `upstream/libreoffice-lock.json` và chữ ký OpenPGP của LibreOffice Build Team (kiểm bằng `sqv`, khoá lưu ở `upstream/libreoffice-signing-key.asc`). Sai một trong ba là dừng.
- `build` lần đầu mất vài giờ; ccache nằm ở `$ONEX_WORK/ccache` (tối đa 20 GB) nên các lần sau nhanh hơn nhiều.
- `sign` ký ad-hoc (`codesign -s -`), đủ để chạy trên Apple Silicon. Developer ID và notarization làm khi có doanh thu.
- `smoke` chuyển một file chữ tiếng Việt sang PDF ở chế độ không giao diện để xác nhận bản build chạy được.
- `defaults` mở một profile mới ở chế độ không giao diện và kiểm 10 giá trị mặc định của `config/1x-defaults.xcd` (ribbon, tiếng Việt, định dạng lưu, bảo mật macro).

Log nằm ở `$ONEX_WORK/logs/`.

## Đổi phiên bản LibreOffice

1. Lấy tên tarball, SHA-256 (trang `.mirrorlist` trên download.documentfoundation.org) và commit (`git ls-remote --tags https://git.libreoffice.org/core 'refs/tags/libreoffice-<phiên bản>*'`).
2. Sửa `upstream/libreoffice-lock.json`.
3. Chạy `python3 scripts/check-repo.py`, rồi build lại.
