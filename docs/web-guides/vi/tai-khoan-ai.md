---
title: 1xAIoffice: gắn tài khoản AI, có hãng miễn phí
description: Gắn khoá API (Groq, Gemini, OpenRouter… có gói miễn phí), đăng nhập ChatGPT bằng gói đang trả, hoặc dùng AI chạy ngay trên máy. Khoá nằm trong Keychain.
headline: Gắn tài khoản AI cho 1xAIoffice
lead: Mở Tài khoản AI, chọn một hãng (hãng có gói miễn phí nằm đầu danh sách), dán khoá hoặc đăng nhập, chọn mô hình. Khoá được cất trong Keychain của macOS.
order: 3
---

1xAIoffice dùng tài khoản AI của chính bạn, không bán gói AI. Mở Tài khoản AI, chọn hãng (các hãng có gói miễn phí nằm đầu danh sách), dán khoá API hoặc đăng nhập, rồi chọn mô hình; khoá được cất trong Keychain của macOS.

## Chọn hãng

- **Có gói miễn phí, dùng khoá API:** Groq, Google Gemini, OpenRouter, Mistral, Cerebras, Hugging Face, NVIDIA, SambaNova, GitHub Models (khoá cần quyền `models:read`).
- **Trả theo mức dùng, khoá API:** OpenAI, Anthropic, DeepSeek, xAI, Together, Fireworks, Azure OpenAI.
- **Đăng nhập:** ChatGPT (dùng gói Plus/Pro bạn đang trả), Google Vertex, Azure (Entra ID), cổng AI nội bộ của cơ quan (SSO).
- **Chạy trên máy, không cần khoá:** Ollama, LM Studio, vLLM. Ollama và LM Studio không gửi gì ra mạng.

Mức miễn phí và giới hạn do từng hãng đặt và có thể đổi; xem trên trang của hãng. Dùng ChatGPT qua ứng dụng khác tính vào hạn mức của gói bạn đang trả.

## Các bước {#cac-buoc}

1. **Mở Tài khoản AI.** Trên thẻ AI, ở cuối thanh bên AI, hoặc menu Tiếng Việt ▸ Tài khoản AI.
2. **Chọn hãng.** Gõ số thứ tự hoặc tên hãng trong danh sách.
3. **Lấy khoá hoặc đăng nhập.** Với hãng dùng khoá, app hỏi có mở trang lấy khoá của hãng trong trình duyệt không; tạo khoá ở đó rồi dán vào ô nhập (chữ được che). Với hãng đăng nhập, trình duyệt mở trang đăng nhập; chọn Không thì app đưa mã để nhập trên thiết bị khác.
4. **Chọn mô hình.** App lấy danh sách mô hình từ hãng khi được, không thì bạn gõ tên.

Từ đây thanh bên AI ghi tài khoản và mô hình đang dùng.

## Khoá của bạn nằm đâu {#rieng-tu}

- Khoá API và mã đăng nhập nằm trong Keychain của macOS, mục tên `1xaioffice/<tên hãng>`.
- Tệp cấu hình trong hồ sơ app chỉ ghi tên mục Keychain, không bao giờ ghi khoá.
- Đăng nhập qua trình duyệt dùng PKCE, trang trả về là 127.0.0.1 trên chính máy bạn.

Muốn gỡ khoá: mở ứng dụng Keychain Access, tìm `1xaioffice` và xoá mục tương ứng.
