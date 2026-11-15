#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""1x Agent Host: tiến trình riêng đứng giữa 1xVnOffice và các mô hình AI.

Vì sao tách tiến trình (theo ai-platform-design.md mục 2): lỗi hay treo ở phần AI không làm sập tài liệu đang mở,
mọi kết nối mạng đi qua một chỗ nên ghi nhật ký và áp chính sách được, và thư viện ngoài không lẫn vào Python của
LibreOffice. Chạy với cờ -I nên không nạp thư viện lạ trong thư mục làm việc.

Giao tiếp: đọc MỘT yêu cầu JSON ở stdin, ghi MỘT trả lời JSON ở stdout, rồi thoát.

  vào : {"action":"ask","provider":{...},"model":"...","messages":[...],"max_tokens":1000,"timeout":60,
         "tools":[{"name":"...","description":"...","schema":{...},"server":{...}}]}
  ra  : {"ok":true,"text":"...","usage":{"input":12,"output":34},"steps":[{"tool":"...","server":"..."}]}
        {"ok":false,"code":"auth","error":"Khoá API bị từ chối..."}

Công cụ trong "tools" đã được người dùng cho phép ở lớp trên; host không tự hỏi quyền và không bao giờ chạy công cụ
nằm ngoài danh sách đó. Kết quả công cụ được đưa lại cho mô hình như DỮ LIỆU, không phải lệnh.

Khoá API KHÔNG bao giờ đi qua yêu cầu: host tự đọc từ kho bí mật của hệ điều hành theo `secret_ref`.
Chỉ dùng thư viện chuẩn của Python.
"""
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

RETRY_CODES = (429, 500, 502, 503, 504)
OPENAI_WIRE = ("openai", "ollama", "azure")
MAX_TOOL_STEPS = 8          # bản thiết kế nói 12; hạ xuống cho bản đầu để vòng lặp hỏng không chạy lâu
TOOL_LOOP_SECONDS = 120
MAX_RETRIES = 2
DEFAULT_TIMEOUT = 60

ERRORS = {
    "auth": "Khoá API bị từ chối. Kiểm tra lại khoá trong Tuỳ chọn ▸ AI, hoặc khoá đã hết hạn.",
    "quota": "Nhà cung cấp báo vượt hạn mức hoặc gọi quá nhanh. Thử lại sau ít phút.",
    "timeout": "Quá giờ chờ trả lời. Mạng chậm, hoặc mô hình đang bận.",
    "network": "Không kết nối được tới nhà cung cấp. Kiểm tra mạng, hoặc máy chủ nội bộ chưa chạy.",
    "secret": "Không lấy được khoá API từ kho bí mật của hệ điều hành ({ref}).",
    "config": "Cấu hình nhà cung cấp chưa đúng: {detail}",
    "server": "Nhà cung cấp trả lỗi {status}: {detail}",
    "answer": "Không đọc được câu trả lời của nhà cung cấp.",
    "plan_limit": "Gói ChatGPT của bạn đã hết lượt dùng cho ứng dụng này. Chờ sang kỳ sau, hoặc gắn thêm một "
                  "nhà cung cấp khác trong AI ▸ Tài khoản AI.",
    "stream": "Nhà cung cấp trả lời dở chừng rồi dừng ({detail}).",
    "login": "{detail}",
    "action": "Việc không hỗ trợ: {action!r}.",
    "tool_unknown": "Mô hình đòi dùng công cụ {name!r} chưa được cho phép, nên đã bị từ chối.",
    "tool_failed": "Công cụ {name!r} lỗi: {detail}",
    "tool_steps": "Mô hình gọi công cụ quá {steps} lượt mà chưa xong; đã dừng.",
    "tool_time": "Vòng gọi công cụ quá {seconds} giây; đã dừng.",
}


def fail(code, **kwargs):
    return {"ok": False, "code": code, "error": ERRORS[code].format(**kwargs)}


def read_secret(ref):
    """Khoá API lấy từ Keychain (macOS). `ref` là tên mục, ví dụ "1xvnoffice/anthropic"."""
    if not ref:
        return ""
    if os.environ.get("ONEX_AI_SECRET_FOR_TEST") is not None:
        return os.environ["ONEX_AI_SECRET_FOR_TEST"]      # chỉ dùng khi chạy kiểm tự động
    try:
        out = subprocess.run(["security", "find-generic-password", "-w", "-s", ref],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def _auth_headers(kind, mode, secret):
    """Header xác thực. Thẻ OAuth luôn là Bearer; khoá API thì mỗi hãng một kiểu."""
    if not secret or mode == "none":
        return {}
    if mode == "oauth":
        return {"Authorization": f"Bearer {secret}"}
    if kind == "anthropic":
        return {"x-api-key": secret}
    if kind == "gemini":
        return {"x-goog-api-key": secret}
    if kind == "azure":
        return {"api-key": secret}
    return {"Authorization": f"Bearer {secret}"}


def credential(provider):
    """(cách xác thực, giá trị) cho một nhà cung cấp. Ném ValueError kèm lời nhắn tiếng Việt khi chưa sẵn sàng.

    Khoá API và thẻ OAuth chỉ tồn tại trong tiến trình này; không ghi ra đâu cả.
    """
    mode = provider.get("auth") or ("oauth" if provider.get("oauth") else
                                    ("key" if provider.get("secret_ref") else "none"))
    if mode == "none":
        return "none", ""
    if mode == "oauth":
        import oauthflow
        try:
            return "oauth", oauthflow.access_token(provider)
        except oauthflow.FlowError as exc:
            raise ValueError(str(exc)) from None
    secret = read_secret(provider.get("secret_ref"))
    if not secret:
        raise KeyError(provider.get("secret_ref") or "")
    return "key", secret


def tool_declarations(kind, tools):
    """Khai báo công cụ theo đúng hình dạng của từng nhà cung cấp."""
    if not tools:
        return None
    if kind in OPENAI_WIRE:
        return [{"type": "function",
                 "function": {"name": t["name"], "description": t.get("description", ""),
                              "parameters": t.get("schema") or {"type": "object", "properties": {}}}}
                for t in tools]
    if kind == "anthropic":
        return [{"name": t["name"], "description": t.get("description", ""),
                 "input_schema": t.get("schema") or {"type": "object", "properties": {}}} for t in tools]
    if kind == "gemini":
        return [{"function_declarations": [{"name": t["name"], "description": t.get("description", ""),
                                            "parameters": t.get("schema") or {"type": "object", "properties": {}}}
                                           for t in tools]}]
    return None


def parse_tool_calls(kind, data):
    """[{id, name, arguments}] mô hình muốn gọi, rỗng nếu không gọi gì."""
    out = []
    try:
        if kind in OPENAI_WIRE:
            for call in (data["choices"][0]["message"].get("tool_calls") or []):
                function = call.get("function") or {}
                arguments = function.get("arguments") or "{}"
                out.append({"id": call.get("id", function.get("name", "")), "name": function.get("name", ""),
                            "arguments": json.loads(arguments) if isinstance(arguments, str) else arguments})
        elif kind == "anthropic":
            for block in data.get("content", []):
                if block.get("type") == "tool_use":
                    out.append({"id": block.get("id", ""), "name": block.get("name", ""),
                                "arguments": block.get("input") or {}})
        elif kind == "gemini":
            for part in data["candidates"][0]["content"]["parts"]:
                call = part.get("functionCall")
                if call:
                    out.append({"id": call.get("name", ""), "name": call.get("name", ""),
                                "arguments": call.get("args") or {}})
    except (KeyError, IndexError, TypeError, ValueError):
        return []
    return [call for call in out if call["name"]]


def build_request(provider, model, messages, max_tokens, secret, tools=None, mode="key"):
    """(url, headers, body) cho từng loại nhà cung cấp. Lỗi cấu hình thì ném ValueError.

    `mode` là cách xác thực: "key" (khoá API, mỗi hãng một kiểu header), "oauth" (thẻ truy cập, luôn là
    Authorization: Bearer), hoặc "none" (máy chủ cục bộ).
    """
    kind = provider.get("type", "")
    base = (provider.get("base_url") or "").rstrip("/")
    system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
    chat = [m for m in messages if m.get("role") != "system"]
    if kind == "responses":
        # Luồng "dùng gói ChatGPT" của OpenAI: Responses API, và tài liệu bắt buộc store=false, stream=true.
        base = base or "https://api.openai.com/v1"
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        headers.update(_auth_headers(kind, mode, secret))
        chat_input = [{"role": m["role"], "content": m["content"]} for m in chat]
        body = {"model": model, "input": chat_input, "max_output_tokens": max_tokens,
                "store": False, "stream": True}
        if system:
            body["instructions"] = system
        return f"{base}/responses", headers, body
    if kind == "azure":
        if not base:
            raise ValueError("Azure OpenAI cần base_url của tài nguyên")
        headers = {"Content-Type": "application/json"}
        headers.update(_auth_headers(kind, mode, secret))
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False}
        declared = tool_declarations(kind, tools)
        if declared:
            body["tools"] = declared
        version = provider.get("api_version") or "2024-10-21"
        return f"{base}/deployments/{model}/chat/completions?api-version={version}", headers, body
    if kind in OPENAI_WIRE:
        base = base or ("http://127.0.0.1:11434/v1" if kind == "ollama" else "https://api.openai.com/v1")
        headers = {"Content-Type": "application/json"}
        headers.update(_auth_headers(kind, mode, secret))
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False}
        declared = tool_declarations(kind, tools)
        if declared:
            body["tools"] = declared
        return f"{base}/chat/completions", headers, body
    if kind == "anthropic":
        base = base or "https://api.anthropic.com/v1"
        headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        headers.update(_auth_headers(kind, mode, secret))
        body = {"model": model, "messages": chat, "max_tokens": max_tokens}
        if system:
            body["system"] = system
        declared = tool_declarations(kind, tools)
        if declared:
            body["tools"] = declared
        return f"{base}/messages", headers, body
    if kind == "gemini":
        base = base or "https://generativelanguage.googleapis.com/v1beta"
        headers = {"Content-Type": "application/json"}
        headers.update(_auth_headers(kind, mode, secret))
        body = {"contents": [{"role": "user" if m["role"] == "user" else "model",
                              "parts": [{"text": m["content"]}]} for m in chat],
                "generationConfig": {"maxOutputTokens": max_tokens}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        declared = tool_declarations(kind, tools)
        if declared:
            body["tools"] = declared
        path = (provider.get("model_path") or "models").strip("/")
        return f"{base}/{path}/{model}:generateContent", headers, body
    raise ValueError(f"loại nhà cung cấp không hỗ trợ: {kind!r}")


def parse_answer(kind, data):
    """(chữ trả lời, số token). Trả về (None, _) khi không đọc được."""
    try:
        if kind in OPENAI_WIRE:
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            return text, {"input": usage.get("prompt_tokens", 0), "output": usage.get("completion_tokens", 0)}
        if kind == "anthropic":
            text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
            usage = data.get("usage") or {}
            return (text or None), {"input": usage.get("input_tokens", 0), "output": usage.get("output_tokens", 0)}
        if kind == "gemini":
            parts = data["candidates"][0]["content"]["parts"]
            usage = data.get("usageMetadata") or {}
            return ("".join(p.get("text", "") for p in parts) or None,
                    {"input": usage.get("promptTokenCount", 0), "output": usage.get("candidatesTokenCount", 0)})
    except (KeyError, IndexError, TypeError):
        return None, {}
    return None, {}


def post(url, headers, body, timeout):
    """(mã HTTP, dữ liệu đã giải mã JSON hoặc chữ thô). Ném urllib.error.URLError khi không nối được."""
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, raw


def parse_responses_stream(raw):
    """(chữ, token, lỗi) từ chuỗi sự kiện của Responses API.

    Theo tài liệu: chữ tới dần qua `response.output_text.delta`, và CHỈ được coi là xong khi thấy
    `response.completed`. Hết luồng mà chưa thấy sự kiện đó thì phải coi là hỏng, không được dùng phần đã nhận.
    Hết lượt của gói thì tới `response.failed` kèm mã `subscription_sharing_usage_limit_exceeded`.
    """
    text, usage, done, failure = [], {}, False, None
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            event = json.loads(payload)
        except ValueError:
            continue
        kind = event.get("type", "")
        if kind == "response.output_text.delta":
            text.append(event.get("delta") or "")
        elif kind == "response.completed":
            done = True
            spent = (event.get("response") or {}).get("usage") or {}
            usage = {"input": spent.get("input_tokens", 0), "output": spent.get("output_tokens", 0)}
        elif kind in ("response.failed", "response.incomplete", "error"):
            detail = (event.get("response") or event).get("error") or {}
            failure = detail.get("code") or detail.get("message") or kind
    if failure:
        return None, usage, failure
    if not done:
        return None, usage, "luồng dừng giữa chừng"
    return "".join(text), usage, None


def get_stream(url, headers, body, timeout):
    """(mã HTTP, toàn văn chuỗi sự kiện). Đọc hết rồi mới dựng câu trả lời: ở đây không cần hiện dần."""
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def tool_result_message(kind, call, text):
    """Đưa kết quả công cụ lại cho mô hình, đúng hình dạng từng nhà cung cấp. Kết quả luôn là dữ liệu."""
    if kind in OPENAI_WIRE:
        return {"role": "tool", "tool_call_id": call["id"], "content": text}
    if kind == "anthropic":
        return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call["id"], "content": text}]}
    if kind == "gemini":
        return {"role": "user", "content": f"Kết quả công cụ {call['name']}:\n{text}"}
    return {"role": "user", "content": text}


def assistant_turn_message(kind, data, calls):
    """Lượt của mô hình (gồm lời gọi công cụ) để ghi vào lịch sử trước khi trả kết quả."""
    if kind in OPENAI_WIRE:
        return data["choices"][0]["message"]
    if kind == "anthropic":
        return {"role": "assistant", "content": data.get("content", [])}
    return {"role": "assistant", "content": "".join(
        part.get("text", "") for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))
        or f"(gọi công cụ {', '.join(c['name'] for c in calls)})"}


def run_tool(tools, call):
    """Chạy một công cụ MCP đã được cho phép. Trả về (chữ kết quả, lỗi hoặc None)."""
    import mcpclient                       # cùng thư mục với host.py; xem _add_own_dir ở cuối tệp
    wanted = next((t for t in tools if t.get("name") == call["name"]), None)
    if wanted is None:
        return None, ERRORS["tool_unknown"].format(name=call["name"])
    server = wanted.get("server") or {}
    try:
        with mcpclient.StdioServer(server.get("command", ""), server.get("args") or [],
                                   env=server.get("env") or {}, cwd=server.get("cwd"),
                                   timeout=server.get("timeout", mcpclient.DEFAULT_TIMEOUT)) as mcp:
            text, _ = mcp.call_tool(call["name"], call.get("arguments") or {})
        return text, None
    except mcpclient.McpError as exc:
        return None, ERRORS["tool_failed"].format(name=call["name"], detail=str(exc))


def ask(request):
    provider = request.get("provider") or {}
    kind = provider.get("type", "")
    try:
        mode, secret = credential(provider)
    except KeyError as exc:
        return fail("secret", ref=str(exc.args[0]))
    except ValueError as exc:
        return fail("login", detail=str(exc))
    tools = request.get("tools") or []
    messages = list(request.get("messages") or [])
    steps = []
    started = time.monotonic()
    for _ in range(MAX_TOOL_STEPS + 1):
        answer = _one_turn(provider, kind, request, messages, secret, tools, mode)
        if not answer.get("ok"):
            return answer
        calls = answer.pop("_calls", [])
        raw = answer.pop("_raw", {})
        if not calls:
            answer["steps"] = steps
            return answer
        if time.monotonic() - started > TOOL_LOOP_SECONDS:
            return fail("tool_time", seconds=TOOL_LOOP_SECONDS)
        messages.append(assistant_turn_message(kind, raw, calls))
        for call in calls:
            text, error = run_tool(tools, call)
            steps.append({"tool": call["name"], "ok": error is None})
            messages.append(tool_result_message(kind, call, text if error is None else error))
    return fail("tool_steps", steps=MAX_TOOL_STEPS)


def _one_turn(provider, kind, request, messages, secret, tools, mode="key"):
    """Một lượt gọi mô hình. Trả về {"ok":True,"text":...,"_calls":[...],"_raw":data} hoặc lỗi."""
    try:
        url, headers, body = build_request(provider, request["model"], messages,
                                           request.get("max_tokens", 1000), secret, tools, mode)
    except (ValueError, KeyError) as exc:
        return fail("config", detail=str(exc))
    timeout = request.get("timeout", DEFAULT_TIMEOUT)
    if kind == "responses":
        return _one_turn_streamed(url, headers, body, timeout)
    for attempt in range(MAX_RETRIES + 1):
        try:
            status, data = post(url, headers, body, timeout)
        except TimeoutError:
            return fail("timeout")
        except urllib.error.URLError as exc:
            if isinstance(getattr(exc, "reason", None), TimeoutError):
                return fail("timeout")
            return fail("network")
        if status in (401, 403):
            return fail("auth")
        if status in RETRY_CODES and attempt < MAX_RETRIES:
            time.sleep(float(os.environ.get("ONEX_AI_RETRY_SLEEP", "1.5")) * (attempt + 1))
            continue
        if status == 429:
            return fail("quota")
        if status >= 400:
            detail = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
            return fail("server", status=status, detail=detail[:300])
        calls = parse_tool_calls(kind, data)
        text, usage = parse_answer(kind, data)
        if text is None and not calls:
            return fail("answer")
        return {"ok": True, "text": text or "", "usage": usage, "_calls": calls, "_raw": data}
    return fail("quota")


def list_models(request):
    """Hỏi nhà cung cấp xem có những mô hình nào, để người dùng không phải tự gõ tên mô hình."""
    provider = request.get("provider") or {}
    kind = provider.get("type", "")
    try:
        mode, secret = credential(provider)
    except KeyError as exc:
        return fail("secret", ref=str(exc.args[0]))
    except ValueError as exc:
        return fail("login", detail=str(exc))
    base = (provider.get("base_url") or "").rstrip("/")
    if kind == "azure":
        # Azure OpenAI không liệt kê mô hình theo kiểu này: tên mô hình là tên deployment do người dùng đặt.
        return fail("config", detail="Azure OpenAI: hãy gõ tên deployment thay vì chọn trong danh sách")
    if kind in OPENAI_WIRE:
        base = base or ("http://127.0.0.1:11434/v1" if kind == "ollama" else "https://api.openai.com/v1")
        url = f"{base}/models"
    elif kind == "anthropic":
        url = (base or "https://api.anthropic.com/v1") + "/models"
    elif kind == "gemini":
        url = (base or "https://generativelanguage.googleapis.com/v1beta") + "/models"
    else:
        return fail("config", detail=f"không hỏi được danh sách mô hình của {kind!r}")
    headers = {"Accept": "application/json"}
    headers.update(_auth_headers(kind, mode, secret))
    if kind == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
    try:
        status, data = get(url, headers, request.get("timeout", DEFAULT_TIMEOUT))
    except TimeoutError:
        return fail("timeout")
    except urllib.error.URLError:
        return fail("network")
    if status in (401, 403):
        return fail("auth")
    if status >= 400:
        detail = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        return fail("server", status=status, detail=detail[:300])
    return {"ok": True, "models": _model_names(data)}


def _model_names(data):
    """Tên mô hình trong câu trả lời, bất kể hãng xếp theo kiểu nào."""
    if not isinstance(data, dict):
        return []
    rows = data.get("data") or data.get("models") or []
    out = []
    for row in rows if isinstance(rows, list) else []:
        name = row.get("id") or row.get("name") or row.get("model") if isinstance(row, dict) else None
        if name:
            out.append(str(name).rsplit("/", 1)[-1])
    return sorted(set(out))


def get(url, headers, timeout):
    """(mã HTTP, dữ liệu) cho một yêu cầu GET."""
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, raw


def oauth_action(action, request):
    """Đăng nhập, lấy mã thiết bị, hỏi lại, hoặc quên thẻ. Thẻ không bao giờ đi ngược ra ngoài tiến trình này."""
    import oauthflow
    provider = request.get("provider") or {}
    config = provider.get("oauth") or {}
    ref = provider.get("secret_ref") or ""
    try:
        if action == "login":
            state, issued = oauthflow.login_browser(config, ref,
                                                    request.get("timeout", oauthflow.LOGIN_TIMEOUT))
            # client_id được cấp KHÔNG phải bí mật: nó là mã nhận dạng ứng dụng, lớp trên ghi vào providers.json.
            return {"ok": True, "state": state, "issued_client_id": issued}
        if action == "device_start":
            started = oauthflow.device_start(config)
            return {"ok": True, "user_code": started["user_code"], "url": started["verification_url"],
                    "device_code": started["device_code"], "interval": started["interval"]}
        if action == "device_poll":
            return {"ok": True, "state": oauthflow.device_poll(config, ref, request.get("device_code", ""),
                                                               request.get("interval", 5),
                                                               request.get("timeout",
                                                                           oauthflow.DEVICE_POLL_TIMEOUT))}
        if action == "logout":
            oauthflow.forget(ref)
            return {"ok": True, "state": "đã quên thẻ của tài khoản này"}
        if action == "status":
            from vn1x import oauth as oauthlib
            return {"ok": True, "state": oauthlib.redacted(oauthflow.read_bundle(ref))}
    except (oauthflow.FlowError, ValueError) as exc:
        return fail("login", detail=str(exc))
    return fail("action", action=action)


def _one_turn_streamed(url, headers, body, timeout):
    """Một lượt với Responses API. Không gọi công cụ ở mốc này (xem README), nên không có vòng lặp."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            status, raw = get_stream(url, headers, body, timeout)
        except TimeoutError:
            return fail("timeout")
        except urllib.error.URLError as exc:
            if isinstance(getattr(exc, "reason", None), TimeoutError):
                return fail("timeout")
            return fail("network")
        if status in (401, 403):
            return fail("auth")
        if status in RETRY_CODES and attempt < MAX_RETRIES:
            time.sleep(float(os.environ.get("ONEX_AI_RETRY_SLEEP", "1.5")) * (attempt + 1))
            continue
        if status == 429:
            return fail("quota")
        if status >= 400:
            return fail("server", status=status, detail=raw[:300])
        text, usage, error = parse_responses_stream(raw)
        if error and "subscription_sharing_usage" in error:
            return fail("plan_limit")
        if error:
            return fail("stream", detail=error)
        return {"ok": True, "text": text or "", "usage": usage, "_calls": [], "_raw": {}}
    return fail("quota")


def main():
    try:
        request = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        print(json.dumps(fail("config", detail=str(exc))), flush=True)
        return 1
    action = request.get("action")
    if action == "ask":
        result = ask(request)
    elif action == "models":
        result = list_models(request)
    elif action in ("login", "device_start", "device_poll", "logout", "status"):
        result = oauth_action(action, request)
    else:
        result = fail("action", action=action)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result.get("ok") else 2


def _add_own_dir():
    """Cho phép `import mcpclient`. Agent Host chạy bằng `python -I host.py`, mà -I bỏ thư mục của script khỏi
    sys.path, nên phải tự thêm lại. Chỉ thêm đúng thư mục của host.py, không thêm thư mục làm việc."""
    own = os.path.dirname(os.path.abspath(__file__))
    if own not in sys.path:
        sys.path.insert(0, own)


_add_own_dir()

if __name__ == "__main__":
    sys.exit(main())
