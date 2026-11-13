# 1xvn-tools: công cụ tiếng Việt

Extension đi kèm 1xVnOffice (MPL-2.0). Menu **Vietnamese / Tiếng Việt** và thanh lệnh trên thẻ **Extension / Tiện ích** của ribbon, trong Writer và Calc.

| Lệnh | Writer | Calc |
|---|---|---|
| Đọc số thành chữ | Thay số đang chọn ("1.250.000,5", "1,250,000.5", "3,5") bằng chữ | Ghi chữ vào ô bên phải mỗi ô số đang chọn, bỏ qua ô không trống |
| Đọc số tiền thành chữ | "Một triệu hai trăm năm mươi nghìn đồng" | Như trên |
| Chuyển mã TCVN3 sang Unicode | Không chọn gì: đổi các đoạn dùng phông `.Vn…` rồi đặt phông Times New Roman (phông `…H` là chữ hoa). Có vùng chọn: đổi vùng chọn | Đổi các ô chữ đang chọn |
| Chuẩn hóa Unicode tiếng Việt | NFC cho vùng chọn, hoặc cả tài liệu (giữ định dạng) | Các ô chữ đang chọn |
| Bỏ dấu tiếng Việt | Như trên | Như trên |

Hàm bảng tính (nhóm **Text / Văn bản** trong Trình hướng dẫn hàm, có mô tả song ngữ):

| Hàm | Ví dụ | Kết quả |
|---|---|---|
| `DOCSO(Số; [Lẻ])` | `=DOCSO(21)`, `=DOCSO(105;"linh")`, `=DOCSO(3,25)` | Hai mươi mốt · Một trăm linh năm · Ba phẩy hai mươi lăm |
| `DOCTIEN(Số tiền; [Đơn vị])` | `=DOCTIEN(1250000)`, `=DOCTIEN(100;"USD")` | Một triệu hai trăm năm mươi nghìn đồng · Một trăm USD |

Số quá 18 chữ số phần nguyên, hay tham số "Lẻ" khác "lẻ"/"linh", cho lỗi trong ô thay vì chữ sai. Lưu ý: Microsoft Excel không có hai hàm này, file `.xlsx` mở trong Excel sẽ báo `#NAME?` ở các ô đó.

Mỗi lệnh là một bước hoàn tác. Chữ đã là Unicode không bao giờ được đem đi chuyển mã TCVN3 nếu người dùng không chọn, vì các chữ như "ã", "à" trùng vị trí byte với TCVN3.

- Logic: `pythonpath/vn1x/` (thuần Python), test: `tests/test_*.py` (`python3 -m unittest discover -s extensions/1xvn-tools/tests`).
- Lệnh UNO: `onex_tools.py` (ProtocolHandler `vnd.1x.tools:` và add-in `org.onexvn.tools.SheetFunctions`), menu: `Addons.xcu`, mô tả hàm: `CalcAddIns.xcu`.
- Kiểu UNO của hàm bảng tính: `idl/org/onexvn/tools/XVnSheetFunctions.idl`, biên dịch sẵn thành `types/onexvn-tools.rdb` bằng `tools/build_rdb.sh <instdir>` (cần SDK của bản build; CI không có nên file `.rdb` được commit).
- Bảng TCVN3: sinh bằng `tools/gen_tcvn3.py` từ bảng TCVN 5712:1993 của glibc (`data/sources/glibc-TCVN5712-1.charmap`, SHA-256 `e0249dfd…99a7`). Không dùng `iconv` của macOS vì bộ chuyển TCVN của nó trả byte NUL cho chữ ASCII.
- Kiểm trên app thật: `scripts/build-macos.sh tools` (`tests/runtime_check.py`).

Chưa làm: cảnh báo khi lưu `.xlsx` có ô dùng `DOCSO`/`DOCTIEN` (kèm lựa chọn đổi thành giá trị), chuyển mã VNI, icon riêng cho các nút.
