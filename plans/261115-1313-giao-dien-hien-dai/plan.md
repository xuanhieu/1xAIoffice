# Giao diện hiện đại, chức năng lộ ra cho người dùng thấy (15/11/2026)

Yêu cầu của chủ dự án: icon và ribbon trông "cheap và old"; menu Công cụ AI (MCP), skill, mẫu NĐ30 không thấy ở
đâu (không có thẻ riêng, thanh bên, chuột phải); Start Center cần trực quan như WPS; mọi panel và icon hiện đại.
Đứng ở góc người dùng: họ phải tự thấy chức năng ở nơi họ quen tìm, không phải đọc hướng dẫn.

## Ranh giới
- WPS chỉ dùng để học bố cục và luồng thao tác (REA, ảnh chụp). KHÔNG chép icon, ảnh, chuỗi hay tệp giao diện của
  WPS vào sản phẩm: đó là tài sản bản quyền của Kingsoft.
- Icon: Fluent UI System Icons (MIT, Microsoft), bản 1.1.345 tại
  /Volumes/SSD1Tb-Black-APFS/Developer/fluentui-svg-icons-1.1.345. Nút lớn dùng biến thể `_color` (890 icon) để có
  điểm nhấn màu như WPS; nút nhỏ dùng `_regular` đơn sắc.

## Các phần, theo thứ tự giá trị cho người dùng
1. **Thẻ AI riêng trên ribbon** ngay sau Trang chủ, nút lớn có chữ: Hỏi AI, Viết lại, Chạy skill, Soạn văn bản
   NĐ30, Kiểm thể thức, Công cụ MCP, Cho trợ lý ngoài dùng, Tài khoản AI; nhóm Tiếng Việt. Writer, Calc, Impress.
2. **Menu chuột phải**: mục AI (hỏi về đoạn chọn, viết lại, chạy skill) và Kiểm thể thức NĐ30 ở đầu menu văn bản
   Writer; Hỏi AI, Đọc số/tiền, Bỏ dấu ở menu ô Calc.
3. **Icon cho lệnh của mình** ở mọi chỗ lệnh xuất hiện (ribbon, menu, chuột phải).
4. **Phủ icon Fluent** cho thanh bên, menu chuột phải, menu chính, để hết cảnh lẫn hai kiểu icon.
5. **Start Center kiểu mới**: cột trái (Văn bản, Bảng tính, Trình chiếu, Mẫu NĐ30, AI), nút Tạo mới nổi bật,
   danh sách gần đây, khung gợi ý bên phải (mẫu NĐ30, AI). Cần vá sfx2 (startcenter.ui, backingwindow.cxx).
6. **Thanh bên AI** (deck riêng ở cột phải): ô hỏi nhanh, nút skill, danh sách mẫu NĐ30.

Để sau, ghi rõ lý do: thanh công cụ nổi khi bôi đen chữ (WPS có, LibreOffice không có sẵn; cần sửa lõi sw).

## Tiêu chí xong
Mở app lần đầu, không đọc hướng dẫn: thấy thẻ AI, chuột phải thấy mục AI, Start Center có lối vào mẫu NĐ30 và AI;
không còn icon kiểu cũ trên ribbon, thanh bên và menu chuột phải của Writer/Calc. Kiểm bằng ảnh chụp app thật.
