# Bài hướng dẫn cho 1xag.com/office

Nguồn của các bài mà nút "Hướng dẫn ↗" trong hộp thoại 1xAIoffice mở ra (`guide_url` trong
`extensions/1xai-tools/onex_tools.py`): `https://1xag.com/office/<bài>` và bản tiếng Anh `https://1xag.com/office/en/<bài>`.

- `vi/<bài>.md`, `en/<bài>.md`: cùng tên tệp, front matter đúng định dạng bài hướng dẫn 1xPass của repo `1x-hub`
  (`title` ≤ 60 ký tự, `description` ≤ 155, `headline`, `lead`, `order`). Link trong bài trỏ `/office/<bài>` hoặc
  `/office/en/<bài>`.
- Tên bài là giá trị trong `GUIDE_TOPICS`. Test `extensions/1xai-tools/tests/test_guide_links.py` báo lỗi khi một chủ đề
  thiếu bài ở một ngôn ngữ, hai thư mục lệch nhau hoặc front matter vượt giới hạn.

## Đưa lên 1xag.com

Hub chỉ sinh trang `/<tag>/<bài>` cho sản phẩm có trong sổ 1xPass (`license-server/src/products/<tag>.ts`).
1xAIoffice chưa có tag vì gói và giá chưa chốt. Khi chốt:

1. Chạy skill `/1xpass` để đăng ký tag `office` (hoặc thêm `/office` vào `HUB_PATH` nếu chỉ cần trang).
2. Chép `vi/*.md` vào `1x-hub/src/content/vi/pass/office/` và `en/*.md` vào `1x-hub/src/content/en/pass/office/`.
3. Thêm từng bài vào `pages.json › guides.<lang>.items` và chạy ba bước kiểm tra trong `1x-hub/CONTENT.md`.

Chỉ viết điều mã nguồn làm được; sửa tính năng thì sửa bài cùng lúc.
