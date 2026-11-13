---
name: lap-bang-du-toan
description: Lập bảng dự toán kinh phí trong 1xSheet, có công thức tính thành tiền, cộng nhóm và tổng cộng.
version: 1.0.0
apps: [sheet]
tools: [sheet.read_range]
permissions: {network: [], process: false}
---
# Lập bảng dự toán

1. Hỏi: dự toán cho việc gì, các khoản mục, đơn vị tính, số lượng, đơn giá, và có tính thuế GTGT hay không.
2. Dựng bảng theo cột: STT, Nội dung, Đơn vị tính, Số lượng, Đơn giá, Thành tiền, Ghi chú.
3. **Thành tiền phải là công thức**, không phải số đã tính sẵn: `=D5*E5`. Cộng nhóm và tổng cộng cũng là công thức `=SUM(...)`. Người dùng sửa số lượng là bảng tự cập nhật.
4. Đơn giá và thành tiền định dạng số có dấu phân cách nghìn, đơn vị đồng.
5. Dòng cuối ghi tổng cộng bằng chữ, dùng hàm `=DOCTIEN(F20)` của 1xVnOffice.

Nhắc người dùng: hàm `DOCTIEN` là hàm riêng của 1xVnOffice, mở trong Microsoft Excel sẽ báo `#NAME?`. Nếu bảng sẽ gửi cho nơi dùng Excel thì chuyển ô đó thành chữ trước khi gửi.
