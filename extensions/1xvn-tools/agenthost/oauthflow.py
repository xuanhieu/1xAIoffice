# SPDX-License-Identifier: MPL-2.0
"""Phần OAuth có chạm mạng và kho bí mật. Chỉ Agent Host nạp tệp này.

Logic thuần (PKCE, hình dạng yêu cầu, hạn thẻ) nằm ở vn1x/oauth.py và có test riêng; ở đây chỉ còn việc gọi
mạng, mở trình duyệt, và đọc/ghi Keychain.

Thẻ đi vào Keychain qua ĐẦU VÀO CHUẨN của lệnh `security`, không qua tham số dòng lệnh, nên giá trị thẻ không
hiện ra trong danh sách tiến trình và không nằm trên đĩa dưới dạng chữ thường.
"""
import base64
import binascii
import json
import os
import secrets
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pythonpath"))
from vn1x import mcphttp, oauth  # noqa: E402

USER_AGENT = mcphttp.USER_AGENT

LOGIN_TIMEOUT = 300          # người dùng có 5 phút để đăng nhập xong trong trình duyệt
DEVICE_POLL_TIMEOUT = 300
HTTP_TIMEOUT = 30

DONE_PAGE = """<!doctype html><html lang="vi"><meta charset="utf-8">
<title>1xVnOffice</title>
<body style="font-family:-apple-system,system-ui,sans-serif;text-align:center;padding:4rem">
<h1>{title}</h1><p>{body}</p></body></html>"""


class FlowError(RuntimeError):
    """Đăng nhập hỏng. Lời nhắn đã viết sẵn bằng tiếng Việt cho người dùng."""


# ---------------------------------------------------------------- kho bí mật

def keychain_write(ref, value, label="1xVnOffice"):
    """Ghi một bí mật vào Keychain, KHÔNG qua tham số dòng lệnh và KHÔNG bị cắt ở 128 ký tự.

    Hai cái bẫy đã gặp thật:
      * `security add-generic-password -w` không tham số thì hỏi giá trị trên bàn phím, và chỗ nhập đó chỉ giữ
        **128 ký tự**. Gói thẻ OAuth hay khoá API dài hơn thế bị cắt cụt mà không báo gì — lưu xong tưởng xong,
        lúc dùng mới thấy hỏng.
      * Đưa giá trị vào `-w <giá trị>` thì nó hiện trong danh sách tiến trình của máy.
    `security -i` đọc LỆNH từ đầu vào chuẩn, nên giá trị đi qua stdin mà vẫn không vướng giới hạn 128.
    """
    command = f'add-generic-password -U -a 1xvnoffice -s {_quote(ref)} -D {_quote(label)} -w {_quote(value)}\n'
    try:
        done = subprocess.run(["security", "-i"], input=command, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def _quote(value):
    """Bọc một giá trị cho bộ đọc lệnh của `security`."""
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _keychain_read(ref):
    try:
        done = subprocess.run(["security", "find-generic-password", "-w", "-s", ref],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def read_bundle(ref):
    """Gói thẻ đã cất, hoặc {} khi chưa có. Không bao giờ in giá trị ra."""
    if not ref:
        return {}
    override = os.environ.get("ONEX_OAUTH_STORE_FOR_TEST")
    if override:
        try:
            with open(override, encoding="utf-8") as handle:
                return json.loads(handle.read() or "{}").get(ref, {})
        except (OSError, ValueError):
            return {}
    raw = _keychain_read(ref)
    if not raw:
        return {}
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, binascii.Error):
        pass
    try:                                    # mục cũ lưu thẳng JSON, vẫn đọc được
        return json.loads(raw)
    except ValueError:
        return {}


def write_bundle(ref, bundle):
    """Cất gói thẻ vào kho bí mật của hệ điều hành."""
    if not ref:
        raise FlowError("chưa đặt tên mục trong kho bí mật cho tài khoản này")
    payload = base64.b64encode(json.dumps(bundle, ensure_ascii=False).encode("utf-8")).decode("ascii")
    override = os.environ.get("ONEX_OAUTH_STORE_FOR_TEST")
    if override:
        try:
            with open(override, encoding="utf-8") as handle:
                store = json.loads(handle.read() or "{}")
        except (OSError, ValueError):
            store = {}
        store[ref] = bundle
        with open(override, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(store, ensure_ascii=False))
        return
    if not keychain_write(ref, payload, "1xVnOffice OAuth"):
        raise FlowError("không ghi được thẻ vào kho bí mật của hệ điều hành")


def forget(ref):
    """Xoá thẻ của một tài khoản khỏi kho bí mật."""
    if os.environ.get("ONEX_OAUTH_STORE_FOR_TEST"):
        write_bundle(ref, {})
        return
    subprocess.run(["security", "delete-generic-password", "-s", ref], capture_output=True, timeout=10)


# ---------------------------------------------------------------- gọi mạng

def post_form(url, headers, body, timeout=HTTP_TIMEOUT):
    """(mã HTTP, dữ liệu JSON hoặc chữ thô) cho một yêu cầu dạng form."""
    request = urllib.request.Request(url, data=body.encode("utf-8"),
                                     headers=dict(headers, **{"User-Agent": USER_AGENT}), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            return response.status, _json_or_text(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, _json_or_text(exc.read())
    except urllib.error.URLError as exc:
        raise FlowError(f"không kết nối được tới máy chủ đăng nhập: {exc.reason}") from None


def _json_or_text(raw):
    text = raw.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except ValueError:
        return text


def with_client_secret(config):
    """Cấu hình kèm client secret đọc từ kho bí mật, nếu nhà cung cấp đòi.

    Google cấp client secret cho cả ứng dụng Desktop và đòi nó ở bước đổi thẻ, dù luồng đã có PKCE. Secret đó
    nằm trong Keychain như mọi bí mật khác, không nằm trong providers.json.
    """
    ref = (config or {}).get("client_secret_ref")
    if not ref:
        return config
    value = read_secret(ref)
    if not value:
        raise FlowError(f"chưa lưu client secret của ứng dụng OAuth ({ref}); mở AI ▸ Tài khoản AI để nhập lại")
    return dict(config, client_secret=value)


def read_secret(ref):
    """Một bí mật thường (không phải gói thẻ) trong kho bí mật của hệ điều hành."""
    if not ref:
        return ""
    override = os.environ.get("ONEX_SECRET_STORE_FOR_TEST")
    if override:
        try:
            with open(override, encoding="utf-8") as handle:
                return json.loads(handle.read() or "{}").get(ref, "")
        except (OSError, ValueError):
            return ""
    return _keychain_read(ref)


def _exchange(config, url, headers, body):
    status, data = post_form(url, headers, body)
    if status >= 400 or not isinstance(data, dict):
        detail = data.get("error_description") or data.get("error") if isinstance(data, dict) else str(data)[:200]
        raise FlowError(f"máy chủ đăng nhập từ chối ({status}): {detail}")
    return oauth.bundle(data)


# ---------------------------------------------------------------- luồng mở trình duyệt

class _Callback(BaseHTTPRequestHandler):
    def do_GET(self):                                     # noqa: N802 - tên do thư viện chuẩn quy định
        self.server.callback_url = f"http://127.0.0.1:{self.server.server_port}{self.path}"
        ok = "error=" not in self.path
        page = DONE_PAGE.format(
            title="Đã đăng nhập xong" if ok else "Đăng nhập không thành công",
            body="Bạn quay lại 1xVnOffice được rồi; đóng tab này đi." if ok
                 else "Quay lại 1xVnOffice và thử lại.")
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):                         # im lặng: không ghi đường dẫn (có mã uỷ quyền) ra nhật ký
        return


def fetch_json(url, timeout=HTTP_TIMEOUT):
    """Đọc một tệp JSON công khai (bản mô tả uỷ quyền). None nếu không có."""
    try:
        request = urllib.request.Request(url, method="GET",
                                         headers={"Accept": "application/json", "User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as reply:
            return json.loads(reply.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, ValueError, OSError):
        return None


def discover_mcp_oauth(url, challenge=None, app_name="1xVnOffice"):
    """Tự tìm cách đăng nhập của một máy chủ MCP ở xa, theo chuẩn uỷ quyền của MCP.

    Đi đúng ba bước: lời thách thức 401 → bản mô tả tài nguyên (RFC 9728) → bản mô tả máy chủ uỷ quyền. Không
    bước nào bắt người dùng khai tay địa chỉ hay client_id.
    """
    from vn1x import mcphttp
    resource = None
    for candidate in mcphttp.metadata_urls(url, challenge):
        resource = fetch_json(candidate)
        if resource:
            break
    if not resource:
        raise FlowError(f"máy chủ MCP {url} đòi đăng nhập nhưng không chỉ ra cách đăng nhập")
    server = None
    for candidate in mcphttp.authorization_server_urls(resource):
        server = fetch_json(candidate)
        if server:
            break
    if not server:
        raise FlowError("không đọc được bản mô tả của máy chủ uỷ quyền")
    return mcphttp.oauth_config(url, resource, server, app_name)


def register_client(config, redirect_uri):
    """Tự đăng ký ứng dụng (RFC 7591) và trả về client_id. Ứng dụng trên máy là client công khai, không secret."""
    from vn1x import mcphttp
    url = config.get("registration_url")
    if not url:
        raise FlowError("máy chủ không cho tự đăng ký ứng dụng; cần quản trị viên cấp client_id")
    body = json.dumps(mcphttp.registration_body(config.get("app_name") or "1xVnOffice", redirect_uri,
                                                config.get("scopes")), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "Accept": "application/json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT,
                                    context=ssl.create_default_context()) as reply:
            data = json.loads(reply.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        raise FlowError(f"đăng ký ứng dụng bị từ chối ({exc.code}): "
                        f"{exc.read().decode('utf-8', 'replace')[:200]}") from None
    except (urllib.error.URLError, ValueError) as exc:
        raise FlowError(f"không đăng ký được ứng dụng: {exc}") from None
    client_id = (data or {}).get("client_id")
    if not client_id:
        raise FlowError("máy chủ đăng ký không trả về client_id")
    return client_id


def mcp_secret_ref(url):
    """Tên mục trong kho bí mật cho thẻ của một máy chủ MCP; mỗi máy chủ một mục."""
    host = url.split("://", 1)[-1].split("/", 1)[0]
    return f"1xvnoffice/mcp/{host}"


def host_id():
    """Mã định danh ổn định của MÁY này, để nhà cung cấp nhận ra cùng một máy ở các lần đăng nhập sau.

    Không phải bí mật và không nói gì về người dùng: chỉ là một chuỗi ngẫu nhiên sinh một lần rồi giữ lại.
    """
    path = Path(os.environ.get("ONEX_HOST_ID_PATH")
                or Path.home() / ".config" / "1xvnoffice" / "host-id")
    try:
        existing = path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    except OSError:
        pass
    fresh = secrets.token_hex(16)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(fresh + "\n", encoding="utf-8")
    except OSError:
        pass
    return fresh


def login_browser(config, ref, timeout=LOGIN_TIMEOUT, register=None):
    """Đăng nhập bằng mã uỷ quyền + PKCE. Trả về (mô tả đã che của gói thẻ, client_id được cấp hoặc "").

    `register` (nếu có) được gọi với redirect_uri ĐÃ BIẾT CỔNG và trả về client_id. Phải đăng ký sau khi mở
    cổng chứ không trước: máy chủ so redirect_uri từng ký tự, nên đăng ký "http://127.0.0.1/callback" rồi đăng
    nhập bằng "http://127.0.0.1:54321/callback" là bị từ chối.
    """
    verifier, challenge = oauth.pkce_pair()
    state = oauth.state_token()
    server = HTTPServer(("127.0.0.1", 0), _Callback)
    server.callback_url = None
    server.timeout = 1
    redirect_uri = f"http://127.0.0.1:{server.server_port}{config.get('redirect_path') or '/callback'}"
    if register is not None:
        try:
            config = dict(config, client_id=register(redirect_uri))
        except Exception:
            server.server_close()
            raise
    extra = dict(config.get("extra_auth_params") or {})
    if config.get("dynamic_client") and config.get("client_id") == oauth.DYNAMIC_CLIENT:
        extra.update(oauth.registration_params(host_id(), config.get("app_name") or "1xVnOffice"))
    if config.get("resource"):
        extra["resource"] = config["resource"]
    config = dict(config, extra_auth_params=extra)
    url = oauth.authorize_url(config, redirect_uri, challenge, state)
    thread = threading.Thread(target=_serve_until, args=(server, timeout), daemon=True)
    thread.start()
    if not webbrowser.open(url):
        server.server_close()
        raise FlowError("không mở được trình duyệt; hãy dùng cách đăng nhập bằng mã thiết bị")
    thread.join(timeout + 2)
    callback = server.callback_url
    server.server_close()
    if not callback:
        raise FlowError(f"chờ quá {timeout} giây mà chưa thấy đăng nhập xong")
    code = oauth.parse_redirect(callback, state)
    issued = oauth.issued_client_id(callback)
    if issued:
        config = dict(config, client_id=issued)      # lần đăng ký đầu: dùng ngay client_id vừa được cấp
    elif config.get("client_id") == oauth.DYNAMIC_CLIENT:
        raise FlowError("đăng ký chưa xong: nhà cung cấp không cấp client_id nào trong lần gọi về")
    config = with_client_secret(config)
    tokens = _exchange(config, *oauth.token_request(config, code, verifier, redirect_uri))
    write_bundle(ref, tokens)
    return oauth.redacted(tokens), issued


def _serve_until(server, timeout):
    stop = time.monotonic() + timeout
    while server.callback_url is None and time.monotonic() < stop:
        server.handle_request()


# ---------------------------------------------------------------- luồng mã thiết bị

def device_start(config):
    """Xin mã thiết bị. Trả về {user_code, verification_url, device_code, interval} để app hiện cho người dùng."""
    status, data = post_form(*oauth.device_start_request(config))
    if status >= 400 or not isinstance(data, dict) or not data.get("device_code"):
        detail = data.get("error_description") or data.get("error") if isinstance(data, dict) else str(data)[:200]
        raise FlowError(f"không xin được mã thiết bị ({status}): {detail}")
    return {"device_code": data["device_code"], "user_code": data.get("user_code", ""),
            "verification_url": data.get("verification_uri_complete") or data.get("verification_uri")
            or data.get("verification_url", ""),
            "interval": int(data.get("interval") or 5),
            "expires_in": int(data.get("expires_in") or DEVICE_POLL_TIMEOUT)}


def device_poll(config, ref, device_code, interval=5, timeout=DEVICE_POLL_TIMEOUT):
    """Hỏi lại cho tới khi người dùng đồng ý. Trả về mô tả đã che của gói thẻ."""
    config = with_client_secret(config)
    url, headers, body = oauth.device_poll_request(config, device_code)
    stop = time.monotonic() + timeout
    wait = max(int(interval), 1)
    while time.monotonic() < stop:
        status, data = post_form(url, headers, body)
        error = data.get("error") if isinstance(data, dict) else None
        if status < 400 and isinstance(data, dict) and data.get("access_token"):
            tokens = oauth.bundle(data)
            write_bundle(ref, tokens)
            return oauth.redacted(tokens)
        if error == "authorization_pending":
            time.sleep(wait)
            continue
        if error == "slow_down":
            wait += 5
            time.sleep(wait)
            continue
        detail = (data.get("error_description") or error) if isinstance(data, dict) else str(data)[:200]
        raise FlowError(f"đăng nhập không thành công: {detail}")
    raise FlowError(f"chờ quá {timeout} giây mà chưa thấy đồng ý trên trình duyệt")


# ---------------------------------------------------------------- dùng thẻ

def access_token(provider):
    """Thẻ truy cập còn hạn cho một nhà cung cấp OAuth, tự gia hạn khi sắp hết.

    Ném FlowError kèm lời nhắn tiếng Việt khi chưa đăng nhập hoặc không gia hạn được.
    """
    config = provider.get("oauth") or {}
    ref = provider.get("secret_ref") or ""
    stored = read_bundle(ref)
    if not stored.get("access_token"):
        raise FlowError(f"chưa đăng nhập tài khoản {provider.get('id', '?')!r}; "
                        "mở AI ▸ Tài khoản AI để đăng nhập")
    if not oauth.needs_refresh(stored):
        return stored["access_token"]
    if not stored.get("refresh_token"):
        raise FlowError(f"thẻ của {provider.get('id', '?')!r} đã hết hạn và không tự gia hạn được; "
                        "hãy đăng nhập lại")
    config = with_client_secret(config)
    fresh = _exchange(config, *oauth.refresh_request(config, stored["refresh_token"]))
    merged = oauth.merge(stored, fresh)
    write_bundle(ref, merged)
    return merged["access_token"]
