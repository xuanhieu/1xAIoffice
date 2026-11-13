---
name: tom-tat-van-ban-phap-luat
description: Tóm tắt một văn bản pháp luật hoặc văn bản hành chính dài, nêu rõ ai phải làm gì, từ bao giờ.
version: 1.0.0
apps: [doc]
tools: [doc.read, doc.outline]
permissions: {network: [], process: false}
---
# Tóm tắt văn bản pháp luật

Người đọc cần biết văn bản này **bắt họ làm gì**, chứ không cần một bản rút gọn đều đều.

1. Đọc cả văn bản (`doc.read`, đọc tiếp bằng cursor nếu dài).
2. Trả lời theo thứ tự: văn bản gì, của ai, hiệu lực từ bao giờ; ai chịu tác động; những nghĩa vụ mới hoặc thay đổi so với trước; mốc thời gian phải làm; chế tài nếu có.
3. Mỗi ý kèm điều khoản dẫn nguồn trong chính văn bản (Điều, Khoản, Điểm). Không có điều khoản tương ứng thì nói là văn bản không nêu.
4. Cuối cùng, liệt kê những chỗ văn bản nói không rõ hoặc có thể hiểu hai cách.

Không suy diễn ngoài văn bản. Không trả lời thay cho luật sư: nếu người dùng hỏi "tôi có bị phạt không", hãy nêu điều khoản liên quan và nói rõ đây không phải tư vấn pháp lý.
