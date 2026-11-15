# SPDX-License-Identifier: MPL-2.0
"""Quyền cho từng công cụ MCP (thuần Python).

Theo ai-platform-design.md mục 7: mỗi công cụ của máy chủ MCP hiện rõ tên, mô tả và quyền; lần đầu dùng phải hỏi;
người dùng chọn "luôn cho phép" cho từng công cụ. Ở đây giữ nguyên tắc **chưa cho phép thì không chạy**.

Quyền lưu trong `mcp_tools.json` ở hồ sơ người dùng, khoá là "<máy chủ>/<công cụ>":

    {"tools": {"giay-to/tra_cuu_van_ban": "allow", "giay-to/xoa_file": "deny"}}

Mô tả công cụ do máy chủ MCP tự khai nên có thể đổi sau lưng người dùng (một cách tấn công đã biết). Vì vậy quyền
được gắn kèm dấu vân tay của mô tả: mô tả đổi thì quyền cũ không còn giá trị và phải hỏi lại.
"""
import hashlib
import json
from pathlib import Path

FILENAME = "mcp_tools.json"
ALLOW, DENY, ASK = "allow", "deny", "ask"


def key(server_id, tool_name):
    return f"{server_id}/{tool_name}"


def fingerprint(tool):
    """Dấu vân tay của mô tả và lược đồ tham số, để biết máy chủ có đổi công cụ sau lưng không."""
    payload = json.dumps({"description": tool.get("description", ""), "schema": tool.get("schema", {})},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load(path):
    file = Path(path)
    if not file.is_file():
        return {"tools": {}}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except ValueError:
        return {"tools": {}}        # tệp hỏng thì coi như chưa cho phép gì, phía an toàn
    tools = data.get("tools")
    return {"tools": tools if isinstance(tools, dict) else {}}


def save(path, store):
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def decide(store, server_id, tool):
    """ALLOW / DENY / ASK cho một công cụ. Chưa có mục nào thì ASK; mô tả đã đổi cũng thành ASK."""
    entry = (store.get("tools") or {}).get(key(server_id, tool["name"]))
    if entry is None:
        return ASK
    if isinstance(entry, str):
        return entry if entry in (ALLOW, DENY) else ASK
    if entry.get("state") not in (ALLOW, DENY):
        return ASK
    if entry.get("fingerprint") and entry["fingerprint"] != fingerprint(tool):
        return ASK                  # máy chủ đã đổi mô tả hoặc tham số: phải hỏi lại
    return entry["state"]


def remember(store, server_id, tool, state):
    """Ghi nhớ lựa chọn của người dùng cho một công cụ."""
    if state not in (ALLOW, DENY):
        raise ValueError(f"trạng thái không hợp lệ: {state!r}")
    out = {"tools": dict(store.get("tools") or {})}
    out["tools"][key(server_id, tool["name"])] = {"state": state, "fingerprint": fingerprint(tool),
                                                  "description": tool.get("description", "")[:200]}
    return out


def allowed_tools(store, server_id, tools):
    """Chỉ những công cụ đã được cho phép, dùng để báo cho mô hình biết nó có gì trong tay."""
    return [tool for tool in tools if decide(store, server_id, tool) == ALLOW]


def describe(server_id, tool):
    """Dòng mô tả hiện cho người dùng khi hỏi quyền."""
    schema = tool.get("schema") or {}
    fields = ", ".join((schema.get("properties") or {}).keys()) or "không có tham số"
    return (f"Máy chủ “{server_id}” muốn dùng công cụ “{tool['name']}”.\n\n"
            f"Máy chủ mô tả: {tool.get('description') or '(không có mô tả)'}\n"
            f"Tham số: {fields}\n\n"
            "Mô tả này do máy chủ tự khai, không phải do 1xAIoffice kiểm chứng. "
            "Chỉ cho phép những máy chủ bạn tin cậy.")
