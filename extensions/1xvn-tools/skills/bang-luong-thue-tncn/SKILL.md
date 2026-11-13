---
name: bang-luong-thue-tncn
description: Lập bảng lương trong 1xSheet có công thức bảo hiểm bắt buộc và thuế thu nhập cá nhân lũy tiến.
version: 1.0.0
apps: [sheet]
tools: [sheet.read_range]
permissions: {network: [], process: false}
---
# Bảng lương có thuế TNCN

1. Hỏi trước, đừng đoán: mức lương đóng bảo hiểm, số người phụ thuộc của từng người, mức giảm trừ gia cảnh đang áp dụng, tỷ lệ bảo hiểm bắt buộc, và kỳ lương.
2. Cột tối thiểu: Họ tên, Lương, Phụ cấp, Tổng thu nhập, Bảo hiểm, Giảm trừ bản thân, Giảm trừ người phụ thuộc, Thu nhập tính thuế, Thuế TNCN, Thực lĩnh.
3. Mọi ô tính đều là **công thức**. Thuế lũy tiến từng phần viết bằng một công thức bậc thang, có chú thích từng bậc ở cột Ghi chú, để người làm kế toán kiểm lại được.
4. Dùng `=SAPTEN(...)` để sắp danh sách theo tên đúng thứ tự tiếng Việt, và `=XUNGHO(...)` khi cần in phiếu lương.

**Luôn nói rõ:** mức giảm trừ gia cảnh, tỷ lệ bảo hiểm và biểu thuế thay đổi theo văn bản của cơ quan thuế. Lấy số người dùng đưa, không lấy số bạn nhớ. Bảng này là công cụ tính, không thay cho kiểm tra của kế toán.
