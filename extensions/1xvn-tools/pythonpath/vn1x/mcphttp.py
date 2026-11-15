# SPDX-License-Identifier: MPL-2.0
"""Logic để nối tới máy chủ MCP qua HTTP, thuần Python (có test riêng, không cần mạng và không cần UNO).

Máy chủ MCP ở xa thường đòi đăng nhập. Chuẩn uỷ quyền của MCP đi theo ba bước, và cả ba đều đọc được từ chính
máy chủ, không phải khai tay:

  1. Gọi thử, bị trả 401 kèm header `WWW-Authenticate` chỉ tới bản mô tả tài nguyên (RFC 9728).
  2. Bản mô tả đó cho biết máy chủ uỷ quyền nào đứng sau; hỏi tiếp bản mô tả của máy chủ uỷ quyền.
  3. Bản mô tả ấy cho đường đăng nhập, đường cấp thẻ, và thường cả đường tự đăng ký ứng dụng (RFC 7591) — nhờ
     vậy người dùng không phải tự đi xin client_id.

Tệp này chỉ dựng *hình dạng* yêu cầu và đọc câu trả lời. Việc gọi mạng nằm trong Agent Host.
"""
import json

JSON_RPC = "2.0"
PROTOCOL_VERSION = "2025-06-18"
ACCEPT = "application/json, text/event-stream"
# Tên ứng dụng gửi kèm mọi lời gọi ra ngoài. Nhiều máy chủ (Cloudflare chẳng hạn) trả 403 cho
# User-Agent mặc định của urllib. Chỉ tên sản phẩm và phiên bản, KHÔNG kèm gì về người dùng.
USER_AGENT = "1xVnOffice/0.1"


class HttpMcpError(RuntimeError):
    """Máy chủ MCP ở xa trả lời sai, hoặc chưa đăng nhập."""


def parse_challenge(header):
    """{resource_metadata, scope} từ header WWW-Authenticate. Thiếu thì trả về rỗng, không ném lỗi.

    Dạng gặp thật: Bearer resource_metadata="https://.../.well-known/oauth-protected-resource/mcp", scope="mcp:tools"
    """
    out = {}
    for part in (header or "").split(","):
        name, _, value = part.strip().partition("=")
        name = name.strip().removeprefix("Bearer").strip()
        value = value.strip().strip('"')
        if name and value:
            out[name] = value
    return out


def metadata_urls(resource_url, challenge=None):
    """Những địa chỉ cần hỏi để biết đăng nhập ở đâu, theo thứ tự nên thử.

    Ưu tiên địa chỉ máy chủ tự chỉ ra trong header; nếu không có thì dựng theo quy ước của RFC 9728, đặt
    `.well-known` TRƯỚC đường dẫn chứ không nối vào sau — `https://máy/mcp` ra
    `https://máy/.well-known/oauth-protected-resource/mcp`.
    """
    named = (challenge or {}).get("resource_metadata")
    if named:
        return [named]
    scheme, _, rest = resource_url.partition("://")
    host, _, path = rest.partition("/")
    path = f"/{path}".rstrip("/")
    return [f"{scheme}://{host}/.well-known/oauth-protected-resource{path}",
            f"{scheme}://{host}/.well-known/oauth-protected-resource"]


def authorization_server_urls(metadata):
    """Địa chỉ bản mô tả của máy chủ uỷ quyền, dựng từ bản mô tả tài nguyên."""
    servers = (metadata or {}).get("authorization_servers") or []
    out = []
    for base in servers:
        base = base.rstrip("/")
        out.append(f"{base}/.well-known/oauth-authorization-server")
        out.append(f"{base}/.well-known/openid-configuration")
    return out


def oauth_config(resource_url, resource_metadata, server_metadata, app_name="1xVnOffice"):
    """Cấu hình OAuth cho vn1x.oauth, dựng từ hai bản mô tả vừa đọc được."""
    for field in ("authorization_endpoint", "token_endpoint"):
        if not (server_metadata or {}).get(field):
            raise HttpMcpError(f"máy chủ uỷ quyền không khai {field}")
    scopes = (resource_metadata or {}).get("scopes_supported") or \
             (server_metadata or {}).get("scopes_supported") or []
    config = {"authorize_url": server_metadata["authorization_endpoint"],
              "token_url": server_metadata["token_endpoint"],
              "scopes": list(scopes),
              "resource": (resource_metadata or {}).get("resource") or resource_url,
              "redirect_path": "/callback",
              "app_name": app_name}
    if server_metadata.get("registration_endpoint"):
        config["registration_url"] = server_metadata["registration_endpoint"]
    return config


def registration_body(app_name, redirect_uri, scopes):
    """Thân yêu cầu tự đăng ký ứng dụng (RFC 7591). Ứng dụng chạy trên máy nên là client công khai, không secret."""
    return {"client_name": app_name, "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"], "token_endpoint_auth_method": "none",
            "scope": " ".join(scopes or [])}


def request_body(method, params=None, request_id=1):
    return {"jsonrpc": JSON_RPC, "id": request_id, "method": method, "params": params or {}}


def notification_body(method, params=None):
    """Thông báo thì KHÔNG có id: gửi kèm id là máy chủ phải trả lời, và nó sẽ chờ một câu trả lời không tới."""
    return {"jsonrpc": JSON_RPC, "method": method, "params": params or {}}


def parse_reply(content_type, raw):
    """Kết quả JSON-RPC từ câu trả lời, dù máy chủ trả một khối JSON hay một chuỗi sự kiện.

    Chuẩn "Streamable HTTP" cho phép cả hai, nên client phải đọc được cả hai.
    """
    if "text/event-stream" in (content_type or ""):
        for line in (raw or "").splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                message = json.loads(payload)
            except ValueError:
                continue
            if isinstance(message, dict) and ("result" in message or "error" in message):
                return message
        raise HttpMcpError("máy chủ gửi chuỗi sự kiện nhưng không có kết quả nào trong đó")
    try:
        message = json.loads(raw or "")
    except ValueError:
        raise HttpMcpError(f"máy chủ trả về thứ không phải JSON: {(raw or '')[:120]}") from None
    if not isinstance(message, dict):
        raise HttpMcpError("máy chủ trả về JSON không đúng hình dạng JSON-RPC")
    return message


def result_or_raise(message):
    """Phần result, hoặc ném lỗi mang đúng lời máy chủ nói."""
    if "error" in message:
        error = message["error"] or {}
        raise HttpMcpError(error.get("message") or f"máy chủ báo lỗi {error.get('code')}")
    if "result" not in message:
        raise HttpMcpError("câu trả lời không có result")
    return message["result"]
