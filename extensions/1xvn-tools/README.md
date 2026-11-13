# 1xvn-tools: công cụ tiếng Việt

Extension đi kèm 1xVnOffice (MPL-2.0). Menu **Vietnamese / Tiếng Việt** và thanh lệnh trên thẻ **Extension / Tiện ích** của ribbon, trong Writer và Calc.

| Lệnh | Writer | Calc |
|---|---|---|
| Đọc số thành chữ | Thay số đang chọn ("1.250.000,5", "1,250,000.5", "3,5") bằng chữ | Ghi chữ vào ô bên phải mỗi ô số đang chọn, bỏ qua ô không trống |
| Đọc số tiền thành chữ | "Một triệu hai trăm năm mươi nghìn đồng" | Như trên |
| Chuyển mã TCVN3 sang Unicode | Không chọn gì: đổi các đoạn dùng phông `.Vn…` rồi đặt phông Times New Roman (phông `…H` là chữ hoa). Có vùng chọn: đổi vùng chọn | Đổi các ô chữ đang chọn |
| Chuẩn hóa Unicode tiếng Việt | NFC cho vùng chọn, hoặc cả tài liệu (giữ định dạng) | Các ô chữ đang chọn |
| Bỏ dấu tiếng Việt | Như trên | Như trên |

Mỗi lệnh là một bước hoàn tác. Chữ đã là Unicode không bao giờ được đem đi chuyển mã TCVN3 nếu người dùng không chọn, vì các chữ như "ã", "à" trùng vị trí byte với TCVN3.

- Logic: `pythonpath/vn1x/` (thuần Python), test: `tests/test_*.py` (`python3 -m unittest discover -s extensions/1xvn-tools/tests`).
- Lệnh UNO: `onex_tools.py` (ProtocolHandler `vnd.1x.tools:`), menu: `Addons.xcu`.
- Bảng TCVN3: sinh bằng `tools/gen_tcvn3.py` từ bảng TCVN 5712:1993 của glibc (`data/sources/glibc-TCVN5712-1.charmap`, SHA-256 `e0249dfd…99a7`). Không dùng `iconv` của macOS vì bộ chuyển TCVN của nó trả byte NUL cho chữ ASCII.
- Kiểm trên app thật: `scripts/build-macos.sh tools` (`tests/runtime_check.py`).

Chưa làm: hàm bảng tính `DOCSO`/`DOCTIEN` (cần thư viện kiểu UNO), chuyển mã VNI, icon riêng cho các nút.
