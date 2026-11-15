# SPDX-License-Identifier: MPL-2.0
"""Logic OAuth 2.0 cho 1xAIoffice, thuần Python (có test riêng, không cần mạng và không cần UNO).

Hai luồng được hỗ trợ, cả hai đều KHÔNG cần client secret:

* **Mã uỷ quyền + PKCE** (RFC 7636): mặc định. Mở trình duyệt của người dùng, nhận mã trả về ở một cổng
  loopback 127.0.0.1 dựng tạm, rồi đổi mã lấy thẻ. Dùng khi máy có trình duyệt.
* **Mã thiết bị** (RFC 8628): dự phòng cho máy không mở được trình duyệt, hoặc khi người dùng muốn đăng nhập
  trên điện thoại. Người dùng mở một đường dẫn và gõ mã ngắn.

Tệp này chỉ dựng *hình dạng* yêu cầu và tính hạn thẻ. Việc gọi mạng và cất thẻ nằm trong Agent Host
(`agenthost/oauthflow.py`), vì chỉ tiến trình đó mới được ra mạng và đọc kho bí mật của hệ điều hành.

Thẻ (access token, refresh token) KHÔNG bao giờ được ghi vào providers.json hay nhật ký: chúng nằm trong
Keychain, và các hàm ở đây không in giá trị thẻ ra bất cứ đâu.
"""
import base64
import hashlib
import os
import secrets
import time
from urllib.parse import urlencode, urlparse, parse_qs

REFRESH_MARGIN_SECONDS = 120     # xin thẻ mới sớm 2 phút, để không hết hạn giữa chừng một câu hỏi dài
DEFAULT_EXPIRES_IN = 3600


class OAuthError(ValueError):
    """Luồng OAuth hỏng hoặc cấu hình thiếu."""


def _required(config, *fields):
    for field in fields:
        if not (config or {}).get(field):
            raise OAuthError(f"cấu hình OAuth thiếu {field!r}")


def pkce_pair():
    """(code_verifier, code_challenge) theo phương pháp S256."""
    verifier = base64.urlsafe_b64encode(os.urandom(64)).decode("ascii").rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return verifier, base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def state_token():
    """Chuỗi ngẫu nhiên chống ghép yêu cầu lạ (CSRF) trong lần trả về."""
    return secrets.token_urlsafe(24)


def authorize_url(config, redirect_uri, challenge, state):
    """Đường dẫn để mở trong trình duyệt của người dùng."""
    _required(config, "authorize_url", "client_id")
    params = {
        "response_type": "code",
        "client_id": config["client_id"],
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    scopes = config.get("scopes") or []
    if scopes:
        params["scope"] = " ".join(scopes)
    params.update(config.get("extra_auth_params") or {})
    joiner = "&" if "?" in config["authorize_url"] else "?"
    return config["authorize_url"] + joiner + urlencode(params)


def parse_redirect(url, expected_state):
    """Mã uỷ quyền trong đường dẫn trình duyệt gọi về. Ném OAuthError khi bị từ chối hoặc state lệch."""
    query = parse_qs(urlparse(url).query)
    got = (query.get("state") or [""])[0]
    if got != expected_state:
        raise OAuthError("lần trả về không khớp yêu cầu đã gửi (state lệch); đã bỏ qua")
    if query.get("error"):
        detail = (query.get("error_description") or query.get("error"))[0]
        raise OAuthError(f"nhà cung cấp từ chối đăng nhập: {detail}")
    code = (query.get("code") or [""])[0]
    if not code:
        raise OAuthError("lần trả về không có mã uỷ quyền")
    return code


DYNAMIC_CLIENT = "dynamic_agent_client"


def issued_client_id(url):
    """client_id mà máy chủ cấp cho lần đăng ký đầu, đọc từ địa chỉ gọi về. Rỗng nghĩa là lần này không cấp.

    Luồng "dùng gói ChatGPT" của OpenAI cho ứng dụng mã nguồn mở tự đăng ký: lần đầu gửi
    client_id=dynamic_agent_client, và chính lần gọi về mang theo client_id thật để lưu lại dùng về sau.
    """
    got = (parse_qs(urlparse(url).query).get("client_id") or [""])[0]
    return "" if got == DYNAMIC_CLIENT else got


def registration_params(host_id, app_name):
    """Tham số thêm cho lần đăng ký đầu: máy nào, và ứng dụng tên gì hiện trên màn hình cho phép."""
    return {"ext_agent_host_id": host_id, "agent_name_hint": app_name}


def token_request(config, code, verifier, redirect_uri):
    """(url, headers, thân yêu cầu dạng form) để đổi mã lấy thẻ."""
    _required(config, "token_url", "client_id")
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": config["client_id"], "code_verifier": verifier}
    if config.get("resource"):
        form["resource"] = config["resource"]
    return _form_request(config, form)


def refresh_request(config, refresh_token):
    """(url, headers, thân yêu cầu) để xin thẻ truy cập mới bằng refresh token."""
    _required(config, "token_url", "client_id")
    if not refresh_token:
        raise OAuthError("không có refresh token; cần đăng nhập lại")
    form = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": config["client_id"]}
    if config.get("resource"):
        form["resource"] = config["resource"]
    return _form_request(config, form)        # cố ý KHÔNG gửi scope: gửi lại là thu hẹp quyền đã được cấp


def device_start_request(config):
    """(url, headers, thân yêu cầu) để xin mã thiết bị."""
    _required(config, "device_url", "client_id")
    form = {"client_id": config["client_id"]}
    scopes = config.get("scopes") or []
    if scopes:
        form["scope"] = " ".join(scopes)
    return config["device_url"], _form_headers(), urlencode(form)


def device_poll_request(config, device_code):
    """(url, headers, thân yêu cầu) để hỏi xem người dùng đã đồng ý chưa."""
    _required(config, "token_url", "client_id")
    if not device_code:
        raise OAuthError("thiếu mã thiết bị")
    return _form_request(config, {"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                                  "device_code": device_code, "client_id": config["client_id"]})


def _form_request(config, form):
    if config.get("client_secret"):
        form["client_secret"] = config["client_secret"]
    return config["token_url"], _form_headers(), urlencode(form)


def _form_headers():
    return {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}


def bundle(response, now=None):
    """Gói thẻ để cất vào kho bí mật. Chỉ giữ đúng những trường cần, không giữ cả câu trả lời của máy chủ."""
    if not isinstance(response, dict) or not response.get("access_token"):
        detail = (response or {}).get("error_description") or (response or {}).get("error") or "thiếu access_token"
        raise OAuthError(f"máy chủ không cấp thẻ: {detail}")
    now = time.time() if now is None else now
    try:
        lifetime = int(response.get("expires_in") or DEFAULT_EXPIRES_IN)
    except (TypeError, ValueError):
        lifetime = DEFAULT_EXPIRES_IN
    out = {"access_token": response["access_token"], "token_type": response.get("token_type") or "Bearer",
           "expires_at": now + lifetime}
    for field in ("refresh_token", "scope", "id_token"):
        if response.get(field):
            out[field] = response[field]
    return out


def merge(old, new):
    """Gói thẻ mới, giữ lại refresh token cũ khi lần làm mới không trả về cái mới (Google hay làm vậy)."""
    out = dict(new)
    if not out.get("refresh_token") and (old or {}).get("refresh_token"):
        out["refresh_token"] = old["refresh_token"]
    return out


def needs_refresh(stored, now=None, margin=REFRESH_MARGIN_SECONDS):
    """Thẻ sắp hết hạn chưa? Không có thẻ cũng tính là cần."""
    if not stored or not stored.get("access_token"):
        return True
    expires_at = stored.get("expires_at")
    if not expires_at:
        return False
    return (time.time() if now is None else now) >= float(expires_at) - margin


def header(stored):
    """Dòng Authorization. Ném OAuthError khi chưa đăng nhập."""
    if not stored or not stored.get("access_token"):
        raise OAuthError("chưa đăng nhập tài khoản này")
    return f"{stored.get('token_type') or 'Bearer'} {stored['access_token']}"


def redacted(stored):
    """Mô tả gói thẻ để hiện cho người dùng và ghi nhật ký. KHÔNG chứa giá trị thẻ."""
    if not stored:
        return "chưa đăng nhập"
    left = int(float(stored.get("expires_at") or 0) - time.time())
    when = f"còn {max(left, 0) // 60} phút" if stored.get("expires_at") else "không rõ hạn"
    renew = "có thể tự gia hạn" if stored.get("refresh_token") else "hết hạn thì phải đăng nhập lại"
    return f"đã đăng nhập, thẻ {when}, {renew}"
