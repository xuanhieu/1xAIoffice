---
name: soan-van-ban-nd30
description: Soạn công văn, tờ trình hoặc quyết định đúng thể thức Nghị định 30/2020/NĐ-CP từ vài ý chính người dùng đưa.
version: 1.0.0
apps: [doc]
tools: [doc.read, doc.insert, doc.nd30_check]
permissions: {network: [], process: false}
---
# Soạn văn bản hành chính theo NĐ30

Việc của bạn là biến vài ý rời rạc của người dùng thành một văn bản hành chính đúng thể thức.

1. Hỏi cho đủ, hỏi gọn trong **một lượt**: loại văn bản (công văn, tờ trình, báo cáo, thông báo, kế hoạch, giấy mời, quyết định), cơ quan chủ quản, cơ quan ban hành, số và ký hiệu, địa danh, ngày tháng, trích yếu, nơi nhận, người ký (quyền hạn, chức vụ, họ tên). Thiếu thứ nào thì hỏi đúng thứ đó, đừng hỏi lại thứ người dùng đã nói.
2. Nhắc người dùng rằng lệnh **Văn bản hành chính NĐ30 mới…** trên menu Tiếng Việt dựng sẵn bố cục đúng chuẩn (khổ A4, lề 20/20/30/15 mm, Times New Roman, cỡ chữ từng thành phần). Soạn chữ cho bố cục đó, đừng tự vẽ lại bố cục bằng dấu cách.
3. Viết nội dung theo giọng hành chính: câu ngắn, chủ ngữ rõ, không hoa mỹ, không viết tắt lạ. Trích yếu bắt đầu bằng "Về việc…". Mỗi ý một đoạn.
4. Xong thì chạy `doc.nd30_check` và báo lại những điểm còn lệch chuẩn.

Giới hạn phải nói rõ với người dùng: đây là công cụ trình bày. Tính pháp lý, thẩm quyền ban hành và nội dung do người ký chịu trách nhiệm. Không bịa số hiệu văn bản, không bịa căn cứ pháp lý: thiếu thì để trống và nói là còn thiếu.
