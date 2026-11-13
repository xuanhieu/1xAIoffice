# 1xvn-tools: công cụ tiếng Việt

Extension đi kèm 1xVnOffice (MPL-2.0). Menu **Vietnamese / Tiếng Việt** và thanh lệnh trên thẻ **Extension / Tiện ích** của ribbon, trong Writer và Calc.

| Lệnh | Writer | Calc |
|---|---|---|
| Đọc số thành chữ | Thay số đang chọn ("1.250.000,5", "1,250,000.5", "3,5") bằng chữ | Ghi chữ vào ô bên phải mỗi ô số đang chọn, bỏ qua ô không trống |
| Đọc số tiền thành chữ | "Một triệu hai trăm năm mươi nghìn đồng" | Như trên |
| Chuyển mã TCVN3 sang Unicode | Không chọn gì: đổi các đoạn dùng phông `.Vn…` rồi đặt phông Times New Roman (phông `…H` là chữ hoa). Có vùng chọn: đổi vùng chọn | Đổi các ô chữ đang chọn |
| Chuẩn hóa Unicode tiếng Việt | NFC cho vùng chọn, hoặc cả tài liệu (giữ định dạng) | Các ô chữ đang chọn |
| Bỏ dấu tiếng Việt | Như trên | Như trên |

**Văn bản hành chính NĐ30 mới...** (menu Tiếng Việt): hộp thoại nhập loại văn bản (công văn, tờ trình, báo cáo, thông báo, kế hoạch, giấy mời, quyết định), cơ quan chủ quản, cơ quan ban hành, số, ký hiệu, địa danh, ngày, trích yếu, kính gửi, nội dung (mỗi dòng một đoạn), quyền hạn ký (TM., Q., KT., TL., TUQ.), chức vụ, họ tên, nơi nhận. Bấm OK khi thiếu hay sai thông tin thì hộp thoại báo lỗi, đưa con trỏ về đúng ô và vẫn giữ những gì đã gõ. Chữ trong văn bản được đặt ngôn ngữ tiếng Việt để kiểm chính tả đúng. Văn bản được dựng theo Phụ lục I NĐ30: khổ A4, lề 20/20/30/15 mm, Times New Roman, cỡ chữ từng thành phần, bảng tiêu đề 2 cột, đường kẻ dưới tiêu ngữ, tên cơ quan và trích yếu, nội dung canh đều lùi đầu dòng 1,27 cm, cách đoạn 6pt, số trang canh giữa lề trên và không hiện ở trang đầu, khối nơi nhận và chữ ký. Ngày nhỏ hơn 10 và tháng 1, 2 có số 0 phía trước ("ngày 05 tháng 01", "tháng 3"). Tài liệu Writer đang trống thì dựng vào đó, còn không thì mở cửa sổ mới. Mẫu: `docs/ui/nd30-to-trinh-sample-2026-11-13.png`. Quy định dùng: `data/nd30.json`, trích nguồn ở `docs/legal/sources/nd-30-2020-phu-luc-i-trich-2026-11-13.txt` (thư mục Office-VN). Đây là công cụ trình bày; tính pháp lý của văn bản do người ban hành chịu trách nhiệm.

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

Chưa làm (NĐ30): kiểm thể thức cho văn bản có sẵn, bố cục riêng của quyết định (căn cứ, điều khoản), nhớ thông tin cơ quan giữa các lần dùng, đường kẻ dài đúng từng dòng (hiện ước lượng theo bề rộng chữ). Chưa làm (khác): cảnh báo khi lưu `.xlsx` có ô dùng `DOCSO`/`DOCTIEN` (kèm lựa chọn đổi thành giá trị), chuyển mã VNI, icon riêng cho các nút.
