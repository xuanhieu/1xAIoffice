# SPDX-License-Identifier: MPL-2.0
"""Skill: gói hướng dẫn sẵn cho trợ lý AI (thuần Python, không UNO).

Theo ai-platform-design.md mục 9. Một skill là một thư mục có `SKILL.md`, đầu tệp là khối front matter:

    ---
    name: soan-cong-van-nd30
    description: Soạn công văn hành chính đúng thể thức NĐ30 từ vài ý chính người dùng đưa.
    version: 1.0.0
    apps: [doc]
    tools: [doc.insert, doc.nd30_check]
    permissions: {network: [], process: false}
    ---
    # Soạn công văn NĐ30
    …

Định dạng giống Agent Skills của Anthropic, thêm ba trường riêng `apps`, `tools`, `permissions`, nên skill viết
cho Claude chạy được ở đây với rất ít sửa đổi.

**Nạp từng phần** (mục 9.2): mô hình chỉ thấy `name` và `description` của mọi skill đã cài; thân `SKILL.md` chỉ
được nạp khi người dùng chọn skill đó, và `references/` chỉ nạp khi thân skill xin.

**Chưa chạy `scripts/`.** Front matter khai được quyền `process`, nhưng ở mốc này 1xVnOffice không chạy script
của skill: một skill tải về từ mạng mà chạy được lệnh thì mất an toàn, và việc duyệt kho skill chưa có.
"""
import os
import re
from pathlib import Path

APPS = ("doc", "sheet", "slide")
MAX_BODY_CHARS = 20000
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


class SkillError(ValueError):
    """Skill hỏng: thiếu trường bắt buộc, tên sai, hoặc xin thứ không được phép."""


def _scalar(raw):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [part.strip().strip("'\"") for part in raw[1:-1].split(",") if part.strip()]
    if raw.startswith("{") and raw.endswith("}"):
        out = {}
        for part in _split_top(raw[1:-1]):
            key, _, value = part.partition(":")
            if key.strip():
                out[key.strip()] = _scalar(value)
        return out
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    return raw.strip("'\"")


def _split_top(text):
    """Tách theo dấu phẩy ở mức ngoài cùng, không cắt bên trong [] hay {}."""
    parts, depth, current = [], 0, ""
    for char in text:
        if char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current)
    return parts


def parse(text):
    """(front matter dạng dict, thân). Ném SkillError nếu SKILL.md không hợp lệ."""
    if not text.startswith("---"):
        raise SkillError("SKILL.md phải mở đầu bằng khối front matter “---”")
    end = text.find("\n---", 3)
    if end < 0:
        raise SkillError("front matter chưa đóng bằng “---”")
    head, body = text[3:end], text[end + 4:]
    meta = {}
    for line in head.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise SkillError(f"dòng front matter không hiểu được: {line!r}")
        meta[key.strip()] = _scalar(value)
    return meta, body.strip()


def validate(meta, folder_name=""):
    """Kiểm front matter, trả về bản đã làm sạch. Mặc định an toàn: không mạng, không chạy script."""
    name = meta.get("name") or ""
    if not _NAME.match(name):
        raise SkillError(f"tên skill không hợp lệ: {name!r} (chỉ chữ thường, số và dấu gạch ngang)")
    if folder_name and folder_name != name:
        raise SkillError(f"tên trong SKILL.md ({name!r}) khác tên thư mục ({folder_name!r})")
    description = (meta.get("description") or "").strip()
    if not description:
        raise SkillError(f"skill {name!r} thiếu mô tả")
    apps = meta.get("apps") or list(APPS)
    if isinstance(apps, str):
        apps = [apps]
    unknown = [app for app in apps if app not in APPS]
    if unknown:
        raise SkillError(f"skill {name!r} khai app lạ: {', '.join(unknown)}")
    tools = meta.get("tools") or []
    if isinstance(tools, str):
        tools = [tools]
    permissions = meta.get("permissions") or {}
    network = permissions.get("network") or []
    if isinstance(network, str):
        network = [network]
    return {"name": name, "description": description, "version": str(meta.get("version") or "0.0.0"),
            "apps": apps, "tools": tools,
            "permissions": {"network": network, "process": bool(permissions.get("process"))}}


def load(folder):
    """Đọc một thư mục skill. Trả về dict đã kiểm, có thêm `path`; thân KHÔNG nạp ở đây."""
    path = Path(folder)
    file = path / "SKILL.md"
    if not file.is_file():
        raise SkillError(f"{path.name}: không có SKILL.md")
    meta, _ = parse(file.read_text(encoding="utf-8"))
    out = validate(meta, path.name)
    out["path"] = str(path)
    return out


def discover(*folders):
    """Mọi skill cài được trong các thư mục đã cho. Skill hỏng bị bỏ qua, kèm lý do, chứ không làm chết lệnh.

    Trả về (danh sách skill, danh sách lỗi dạng chữ). Skill trùng tên thì thư mục ĐỨNG SAU thắng, nên skill
    của người dùng đè được skill đi kèm.
    """
    found, problems = {}, []
    for folder in folders:
        base = Path(folder)
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            try:
                skill = load(child)
            except (SkillError, OSError, UnicodeDecodeError) as exc:
                problems.append(f"{child.name}: {exc}")
                continue
            found[skill["name"]] = skill
    return [found[name] for name in sorted(found)], problems


def summaries(skills, app=None):
    """Phần duy nhất mô hình được thấy từ đầu: tên và mô tả, lọc theo app đang dùng."""
    return [{"name": s["name"], "description": s["description"]}
            for s in skills if app is None or app in s["apps"]]


def body(skill):
    """Thân SKILL.md, chỉ nạp khi skill được chọn. Cắt bớt nếu quá dài."""
    text = (Path(skill["path"]) / "SKILL.md").read_text(encoding="utf-8")
    _, content = parse(text)
    if len(content) > MAX_BODY_CHARS:
        return content[:MAX_BODY_CHARS] + "\n…(phần còn lại của skill đã bị cắt)"
    return content


def reference(skill, relative):
    """Một tệp trong thư mục skill, nạp khi thân skill xin.

    Chặn đường dẫn trỏ ra ngoài thư mục skill ("../../etc/passwd"): skill có thể tải về từ mạng.
    """
    base = Path(skill["path"]).resolve()
    target = (base / relative).resolve()
    if not str(target).startswith(str(base) + os.sep):
        raise SkillError(f"skill {skill['name']!r} xin tệp ngoài thư mục của nó: {relative!r}")
    if not target.is_file():
        raise SkillError(f"skill {skill['name']!r} không có tệp {relative!r}")
    return target.read_text(encoding="utf-8")


def allowed_tools(skill, available):
    """Công cụ skill được dùng: phần giao của `tools` trong front matter và những công cụ đang có.

    Skill không khai `tools` thì không được dùng công cụ nào — khai rõ mới được, không ngầm hiểu.
    """
    wanted = set(skill.get("tools") or [])
    return [tool for tool in available if (tool.get("name") if isinstance(tool, dict) else tool) in wanted]


def prompt(skill, question=""):
    """Tin nhắn hệ thống cho một lượt chạy skill: thân skill là HƯỚNG DẪN, câu hỏi người dùng là việc cần làm."""
    lines = [f"Bạn đang chạy skill “{skill['name']}” của 1xVnOffice.", "", body(skill)]
    if skill["permissions"]["network"]:
        lines += ["", "Skill này khai cần mạng tới: " + ", ".join(skill["permissions"]["network"])]
    if question.strip():
        lines += ["", "Việc người dùng cần: " + question.strip()]
    return "\n".join(lines)
