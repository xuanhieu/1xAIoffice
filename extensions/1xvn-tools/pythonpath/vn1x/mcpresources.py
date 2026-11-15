# SPDX-License-Identifier: MPL-2.0
"""Tài liệu đang mở của 1xAIoffice nhìn dưới dạng MCP resource, thuần Python (có test riêng, không cần UNO).

Theo bản thiết kế mục 8: mỗi tài liệu văn bản là `1x://doc/<id>` ở dạng Markdown, mỗi trang tính là
`1x://sheet/<id>/<tên trang>` ở dạng CSV.

Vì sao có resource khi đã có công cụ `doc.read`: trợ lý gắn resource vào ngữ cảnh một lần rồi đọc lại nhiều lượt
mà không tốn thêm lời gọi công cụ, và người dùng thấy rõ tài liệu nào đang được đưa cho trợ lý.
"""
import csv
import io

SCHEME = "1x://"
MARKDOWN = "text/markdown"
CSV_TYPE = "text/csv"
HEADING_PREFIX = ("Heading", "Tiêu đề")
MAX_HEADING_LEVEL = 6


class ResourceError(ValueError):
    """Địa chỉ resource sai, hoặc không có tài liệu đó."""


def doc_uri(doc_id):
    return f"{SCHEME}doc/{doc_id}"


def sheet_uri(doc_id, sheet):
    return f"{SCHEME}sheet/{doc_id}/{sheet}"


def parse(uri):
    """(loại, mã tài liệu, tên trang tính) từ một địa chỉ `1x://`. Trang tính là None với tài liệu văn bản."""
    if not isinstance(uri, str) or not uri.startswith(SCHEME):
        raise ResourceError(f"địa chỉ phải bắt đầu bằng {SCHEME!r}: {uri!r}")
    parts = uri[len(SCHEME):].split("/")
    if parts[0] == "doc" and len(parts) == 2 and parts[1]:
        return "doc", parts[1], None
    if parts[0] == "sheet" and len(parts) >= 3 and parts[1]:
        sheet = "/".join(parts[2:])          # tên trang tính có thể chứa dấu gạch chéo
        if sheet:
            return "sheet", parts[1], sheet
    raise ResourceError(f"địa chỉ không đúng dạng 1x://doc/<id> hoặc 1x://sheet/<id>/<trang>: {uri!r}")


def descriptors(documents):
    """Danh sách resource để trả cho resources/list.

    `documents`: [{"id": "doc1", "title": "...", "kind": "doc"|"sheet", "sheets": ["Sheet1", ...]}]
    Bảng tính không tự nó là một resource: mỗi TRANG TÍNH là một resource, vì gộp cả sổ vào một CSV thì mất ranh
    giới giữa các trang.
    """
    out = []
    for document in documents or []:
        doc_id = document.get("id") or ""
        title = document.get("title") or doc_id
        if not doc_id:
            continue
        if document.get("kind") == "sheet":
            for sheet in document.get("sheets") or []:
                out.append({"uri": sheet_uri(doc_id, sheet), "name": f"{title} — {sheet}",
                            "mimeType": CSV_TYPE,
                            "description": f"Trang tính {sheet!r} của bảng tính đang mở trong 1xAIoffice."})
        else:
            out.append({"uri": doc_uri(doc_id), "name": title, "mimeType": MARKDOWN,
                        "description": "Tài liệu văn bản đang mở trong 1xAIoffice."})
    return out


def heading_level(style):
    """Mức tiêu đề của một kiểu đoạn, 0 nghĩa là đoạn thường."""
    name = (style or "").strip()
    for prefix in HEADING_PREFIX:
        if name.startswith(prefix):
            tail = name[len(prefix):].strip()
            if tail.isdigit() and 1 <= int(tail) <= MAX_HEADING_LEVEL:
                return int(tail)
            if not tail:
                return 1
    return 0


def to_markdown(paragraphs):
    """Markdown từ [(kiểu đoạn, chữ)].

    Chỉ đổi tiêu đề thành `#`; mọi thứ khác giữ nguyên chữ. Cố ý KHÔNG đoán in đậm, danh sách hay bảng: đoán sai
    thì trợ lý đọc ra một tài liệu không giống bản người dùng đang nhìn, mà đó mới là thứ nguy hiểm.
    """
    lines = []
    for style, text in paragraphs or []:
        body = (text or "").strip()
        level = heading_level(style)
        if not body:
            continue
        lines.append("#" * level + " " + body if level else body)
    return "\n\n".join(lines)


def to_csv(rows):
    """CSV đúng chuẩn RFC 4180 từ các hàng ô đã đọc; ô có dấu phẩy, nháy kép hay xuống dòng đều được bọc đúng."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    for row in rows or []:
        writer.writerow(["" if cell is None else str(cell) for cell in row])
    return buffer.getvalue().rstrip("\n")


def contents(uri, text):
    """Khối contents của resources/read."""
    kind, _, _ = parse(uri)
    return [{"uri": uri, "mimeType": CSV_TYPE if kind == "sheet" else MARKDOWN, "text": text}]
