# SPDX-License-Identifier: MPL-2.0
"""Tập thay đổi do AI đề nghị, chưa áp vào tài liệu (thuần Python).

Theo ai-platform-design.md mục 5: công cụ ghi KHÔNG sửa tài liệu ngay. Chúng trả về một ChangeSet gắn vào các mốc;
người dùng xem trước rồi mới chọn áp dụng. Khi áp, lớp UNO bọc tất cả trong một bước hoàn tác, nên Ctrl+Z một lần
là trả lại như cũ.

Mốc ổn định: mỗi thay đổi nhớ chữ gốc của chỗ nó sẽ sửa. Nếu người dùng sửa chỗ đó trong lúc AI đang chạy, chữ gốc
không còn khớp, ChangeSet bị coi là **đã cũ** và không được áp.
"""
PREVIEW_CHARS = 600


class Change:
    """Một chỗ sửa: thay chữ ở mốc `anchor` từ `old` thành `new`."""

    def __init__(self, anchor, old, new):
        self.anchor, self.old, self.new = anchor, old, new

    @property
    def empty(self):
        return self.old.strip() == self.new.strip()

    def __repr__(self):
        return f"Change({self.anchor!r}, {self.old[:20]!r} -> {self.new[:20]!r})"

    def __eq__(self, other):
        return (self.anchor, self.old, self.new) == (other.anchor, other.old, other.new)


def build(items):
    """Dựng ChangeSet từ [(mốc, chữ cũ, chữ mới)], bỏ những chỗ không đổi gì."""
    changes = [Change(anchor, old, new) for anchor, old, new in items]
    return [change for change in changes if not change.empty]


def words(text):
    return len(text.split())


def summary(changes):
    """Một dòng tóm tắt cho người dùng."""
    if not changes:
        return "Không có gì để sửa."
    before = sum(words(change.old) for change in changes)
    after = sum(words(change.new) for change in changes)
    where = "1 chỗ" if len(changes) == 1 else f"{len(changes)} chỗ"
    return f"{where}: {before} từ → {after} từ."


def _shorten(text, limit):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def preview(changes, limit=PREVIEW_CHARS):
    """Bản xem trước dạng chữ: từng chỗ, chữ cũ rồi chữ mới."""
    if not changes:
        return summary(changes)
    blocks = []
    for index, change in enumerate(changes, 1):
        head = f"[{index}]" if len(changes) > 1 else ""
        blocks.append(f"{head}\nTrước:\n{_shorten(change.old, limit)}\n\nSau:\n{_shorten(change.new, limit)}".strip())
    return summary(changes) + "\n\n" + "\n\n———\n\n".join(blocks)


def stale(changes, current):
    """Mốc đã bị sửa từ lúc dựng ChangeSet. `current`: {mốc: chữ hiện tại}.

    So sánh sau khi gộp khoảng trắng, để khác biệt vô hại (xuống dòng, khoảng trắng thừa) không làm hỏng việc.
    """
    out = []
    for change in changes:
        now = current.get(change.anchor)
        if now is None or " ".join(now.split()) != " ".join(change.old.split()):
            out.append(change.anchor)
    return out
