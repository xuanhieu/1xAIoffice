# SPDX-License-Identifier: MPL-2.0
"""Chọn phần tài liệu gửi cho mô hình AI (thuần Python, phần đọc tài liệu nằm ở lớp UNO).

Thứ tự ưu tiên theo ai-platform-design.md mục 4: vùng đang chọn → cả tài liệu, cắt bớt khi vượt ngân sách.
Cắt ở ranh giới đoạn để mô hình không nhận nửa câu, và luôn nói rõ cho người dùng biết đã gửi đi bao nhiêu.
"""
BUDGET_CHARS = 12000      # khoảng 3–4 nghìn token tiếng Việt, đủ cho một văn bản hành chính
SYSTEM = ("Bạn là trợ lý trong bộ văn phòng 1xVnOffice. Trả lời bằng tiếng Việt, ngắn gọn và chính xác. "
          "Chỉ dựa vào phần tài liệu được cung cấp; không bịa thêm. Nếu tài liệu không đủ dữ kiện để trả lời, "
          "hãy nói rõ là không đủ dữ kiện.")


def trim(text, budget=BUDGET_CHARS):
    """(chữ đã cắt, có cắt hay không). Cắt ở ranh giới đoạn gần nhất, không cắt giữa câu."""
    text = text.strip()
    if len(text) <= budget:
        return text, False
    cut = text[:budget]
    # keep: phần của dấu ngăn thuộc về câu đứng trước (dấu chấm giữ lại, dòng trống thì bỏ).
    for separator, keep in (("\n\n", 0), ("\n", 0), (". ", 1)):
        at = cut.rfind(separator)
        if at > budget // 2:
            return cut[:at + keep].rstrip(), True
    return cut.rstrip(), True


def build(question, selection="", document="", budget=BUDGET_CHARS):
    """Danh sách tin nhắn gửi mô hình, và phần mô tả cho người dùng biết đã gửi gì."""
    question = (question or "").strip()
    if not question:
        raise ValueError("chưa có câu hỏi")
    source = (selection or "").strip()
    scope = "vùng đang chọn"
    if not source:
        source, scope = (document or "").strip(), "cả tài liệu"
    if not source:
        raise ValueError("tài liệu trống, không có gì để hỏi")
    body, trimmed = trim(source, budget)
    note = f"{scope}, {len(body)} ký tự" + (" (đã cắt bớt cho vừa ngân sách)" if trimmed else "")
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Tài liệu ({scope}):\n\n{body}\n\n---\n\nCâu hỏi: {question}"},
    ]
    return messages, note
