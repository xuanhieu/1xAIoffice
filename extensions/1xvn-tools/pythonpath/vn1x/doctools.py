# SPDX-License-Identifier: MPL-2.0
"""Bộ công cụ tài liệu dùng chung (thuần Python, không UNO).

Theo ai-platform-design.md mục 6: khung trợ lý trong app và MCP server (mục 8) mở ra đúng **một** bộ công cụ này,
để chỉ phải viết và kiểm một lần. Ở đây là phần không đụng tới tài liệu: tên công cụ, lược đồ tham số, nhãn
đọc/ghi theo chuẩn MCP, kiểm tham số, cắt kết quả quá dài và con trỏ trang tiếp.

Phần thật sự chạm vào tài liệu nằm ở lớp UNO (`backend` truyền vào `call`), nên bộ này kiểm được mà không cần mở
office. Hai nhãn theo chuẩn MCP:

* `readOnlyHint`  — công cụ không đổi gì trong tài liệu.
* `destructiveHint` — công cụ có thể làm mất nội dung đang có.

Công cụ ghi KHÔNG tự sửa tài liệu: lớp UNO đưa chúng qua xem trước và hoàn tác như mọi lệnh AI khác.
"""
MAX_RESULT_CHARS = 50000      # mục 6: kết quả đọc giới hạn 50.000 ký tự, kèm con trỏ trang tiếp
_STRING = {"type": "string"}


def _schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required)}


TOOLS = [
    {"name": "docs.list_open", "read_only": True, "destructive": False,
     "title": "Tài liệu đang mở",
     "description": "Liệt kê tài liệu đang mở trong 1xAIoffice: mã, tên, loại (văn bản, bảng tính, trình chiếu), "
                    "đã lưu hay chưa.",
     "schema": _schema({})},
    {"name": "doc.read", "read_only": True, "destructive": False,
     "title": "Đọc nội dung văn bản",
     "description": "Đọc nội dung một tài liệu văn bản dưới dạng Markdown. Dài quá thì trả về từng phần, "
                    "dùng tham số cursor để đọc tiếp.",
     "schema": _schema({"doc": _STRING, "cursor": {"type": "integer", "minimum": 0}}, ["doc"])},
    {"name": "doc.outline", "read_only": True, "destructive": False,
     "title": "Cây tiêu đề",
     "description": "Cây tiêu đề, bảng và ảnh của một tài liệu văn bản.",
     "schema": _schema({"doc": _STRING}, ["doc"])},
    {"name": "doc.insert", "read_only": False, "destructive": False,
     "title": "Chèn nội dung",
     "description": "Chèn văn bản vào tài liệu tại một mốc: đầu tài liệu, cuối tài liệu, hoặc sau một đoạn. "
                    "Người dùng xem trước và đồng ý thì mới được áp vào tài liệu.",
     "schema": _schema({"doc": _STRING, "text": _STRING,
                        "where": {"type": "string", "enum": ["start", "end", "after"]},
                        "anchor": {"type": "integer", "minimum": 0}}, ["doc", "text"])},
    {"name": "doc.replace", "read_only": False, "destructive": True,
     "title": "Thay nội dung một đoạn",
     "description": "Thay toàn bộ chữ của một đoạn bằng chữ mới. Người dùng xem trước và đồng ý thì mới được áp.",
     "schema": _schema({"doc": _STRING, "anchor": {"type": "integer", "minimum": 0}, "text": _STRING},
                       ["doc", "anchor", "text"])},
    {"name": "doc.nd30_check", "read_only": True, "destructive": False,
     "title": "Kiểm thể thức NĐ30",
     "description": "Kiểm thể thức văn bản hành chính theo Nghị định 30/2020/NĐ-CP: khổ giấy, lề, phông, cỡ chữ, "
                    "Quốc hiệu, Tiêu ngữ, mục Nơi nhận. Chỉ kiểm trình bày, không kết luận về giá trị pháp lý.",
     "schema": _schema({"doc": _STRING}, ["doc"])},
    {"name": "sheet.read_range", "read_only": True, "destructive": False,
     "title": "Đọc vùng bảng tính",
     "description": "Đọc giá trị và công thức của một vùng trong bảng tính, ví dụ 'Sheet1.A1:D20'.",
     "schema": _schema({"doc": _STRING, "range": _STRING}, ["doc", "range"])},
    {"name": "vn.convert_legacy", "read_only": False, "destructive": False,
     "title": "Chuyển mã chữ Việt cũ",
     "description": "Chuyển chữ TCVN3, VNI hoặc VIQR trong tài liệu sang Unicode. Người dùng xem trước rồi mới áp.",
     "schema": _schema({"doc": _STRING, "kind": {"type": "string", "enum": ["tcvn3", "vni", "viqr"]}},
                       ["doc", "kind"])},
    {"name": "vn.normalize", "read_only": False, "destructive": False,
     "title": "Chuẩn hoá chữ Việt",
     "description": "Chuẩn hoá Unicode NFC và khoảng trắng quanh dấu câu. Người dùng xem trước rồi mới áp.",
     "schema": _schema({"doc": _STRING}, ["doc"])},
]
BY_NAME = {tool["name"]: tool for tool in TOOLS}


def declarations():
    """Danh sách công cụ theo đúng hình dạng MCP tools/list."""
    return [{"name": tool["name"], "title": tool["title"], "description": tool["description"],
             "inputSchema": tool["schema"],
             "annotations": {"readOnlyHint": tool["read_only"], "destructiveHint": tool["destructive"]}}
            for tool in TOOLS]


class ToolError(ValueError):
    """Tham số sai, hoặc công cụ không có. Lỗi được trả về cho client, không làm chết máy chủ."""


def check(name, arguments):
    """Kiểm tên công cụ và tham số. Trả về tham số đã làm sạch, hoặc ném ToolError bằng tiếng Việt."""
    tool = BY_NAME.get(name)
    if tool is None:
        raise ToolError(f"không có công cụ tên {name!r}")
    arguments = dict(arguments or {})
    schema = tool["schema"]
    for field in schema["required"]:
        if field not in arguments or arguments[field] in (None, ""):
            raise ToolError(f"{name}: thiếu tham số bắt buộc {field!r}")
    out = {}
    for field, value in arguments.items():
        spec = schema["properties"].get(field)
        if spec is None:
            continue                     # tham số lạ thì bỏ, không làm hỏng lời gọi
        out[field] = _value(name, field, spec, value)
    return out


def _value(name, field, spec, value):
    kind = spec.get("type")
    if kind == "string":
        if not isinstance(value, str):
            raise ToolError(f"{name}: tham số {field!r} phải là chữ")
        if spec.get("enum") and value not in spec["enum"]:
            raise ToolError(f"{name}: {field!r} phải là một trong {', '.join(spec['enum'])}")
        return value
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ToolError(f"{name}: tham số {field!r} phải là số nguyên")
        if "minimum" in spec and value < spec["minimum"]:
            raise ToolError(f"{name}: {field!r} không được nhỏ hơn {spec['minimum']}")
        return value
    return value


def page(text, cursor=0, limit=MAX_RESULT_CHARS):
    """(phần chữ, con trỏ tiếp hoặc None). Cắt ở ranh giới dòng để không đứt giữa câu."""
    text = text or ""
    if cursor >= len(text):
        return "", None
    chunk = text[cursor:cursor + limit]
    if cursor + len(chunk) >= len(text):
        return chunk, None
    at = chunk.rfind("\n")
    if at > limit // 2:
        chunk = chunk[:at]
    return chunk, cursor + len(chunk)


def result(text, next_cursor=None, is_error=False):
    """Kết quả theo hình dạng MCP tools/call."""
    if next_cursor is not None:
        text = f"{text}\n\n…(còn nữa, gọi lại với cursor={next_cursor})"
    out = {"content": [{"type": "text", "text": text}]}
    if is_error:
        out["isError"] = True
    return out


def call(backend, name, arguments):
    """Chạy một công cụ qua `backend` (lớp UNO, hoặc đồ giả khi kiểm thử). Luôn trả về kết quả MCP, không ném."""
    try:
        arguments = check(name, arguments)
        handler = getattr(backend, name.replace(".", "_"), None)
        if handler is None:
            raise ToolError(f"công cụ {name!r} chưa dùng được trong phiên này")
        text = handler(**arguments)
    except ToolError as exc:
        return result(str(exc), is_error=True)
    except Exception as exc:              # noqa: BLE001 - lỗi của lớp UNO không được làm chết máy chủ
        return result(f"{name} lỗi: {exc}", is_error=True)
    if isinstance(text, tuple):           # (chữ, con trỏ tiếp)
        return result(text[0], text[1])
    return result(text if isinstance(text, str) else str(text))
