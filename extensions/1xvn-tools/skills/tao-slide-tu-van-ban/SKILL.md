---
name: tao-slide-tu-van-ban
description: Chuyển một văn bản dài thành dàn ý trình chiếu, mỗi trang một ý, có ghi chú cho người trình bày.
version: 1.0.0
apps: [doc, slide]
tools: [doc.read, doc.outline]
permissions: {network: [], process: false}
---
# Tạo slide từ văn bản

1. Đọc văn bản và lấy cây tiêu đề (`doc.outline`) làm khung.
2. Mỗi trang chiếu một ý. Tiêu đề trang là một câu khẳng định, không phải một danh từ cụt ("Ngân sách tăng 12%", không phải "Ngân sách").
3. Tối đa 5 gạch đầu dòng mỗi trang, mỗi dòng tối đa khoảng 12 từ. Số liệu để nguyên, đừng làm tròn khác bản gốc.
4. Với mỗi trang, viết thêm phần **ghi chú cho người trình bày**: câu nói dẫn dắt và chỗ cần nhấn.
5. Trang đầu: tên bài, người trình bày, ngày. Trang cuối: điều cần người nghe quyết hoặc làm.

Không bịa ví dụ, không thêm số liệu không có trong văn bản gốc.
