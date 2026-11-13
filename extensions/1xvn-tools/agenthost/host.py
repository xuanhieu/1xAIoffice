#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""1x Agent Host: tiến trình riêng đứng giữa 1xVnOffice và các mô hình AI.

Vì sao tách tiến trình (theo ai-platform-design.md mục 2): lỗi hay treo ở phần AI không làm sập tài liệu đang mở,
mọi kết nối mạng đi qua một chỗ nên ghi nhật ký và áp chính sách được, và thư viện ngoài không lẫn vào Python của
LibreOffice. Chạy với cờ -I nên không nạp thư viện lạ trong thư mục làm việc.

Giao tiếp: đọc MỘT yêu cầu JSON ở stdin, ghi MỘT trả lời JSON ở stdout, rồi thoát.

  vào : {"action":"ask","provider":{...},"model":"...","messages":[...],"max_tokens":1000,"timeout":60}
  ra  : {"ok":true,"text":"...","usage":{"input":12,"output":34}}
        {"ok":false,"code":"auth","error":"Khoá API bị từ chối..."}

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


def build_request(provider, model, messages, max_tokens, secret):
    """(url, headers, body) cho từng loại nhà cung cấp. Lỗi cấu hình thì ném ValueError."""
    kind = provider.get("type", "")
    base = (provider.get("base_url") or "").rstrip("/")
    system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
    chat = [m for m in messages if m.get("role") != "system"]
    if kind in ("openai", "ollama"):
        base = base or ("http://127.0.0.1:11434/v1" if kind == "ollama" else "https://api.openai.com/v1")
        headers = {"Content-Type": "application/json"}
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False}
        return f"{base}/chat/completions", headers, body
    if kind == "anthropic":
        base = base or "https://api.anthropic.com/v1"
        headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": secret}
        body = {"model": model, "messages": chat, "max_tokens": max_tokens}
        if system:
            body["system"] = system
        return f"{base}/messages", headers, body
    if kind == "gemini":
        base = base or "https://generativelanguage.googleapis.com/v1beta"
        headers = {"Content-Type": "application/json", "x-goog-api-key": secret}
        body = {"contents": [{"role": "user" if m["role"] == "user" else "model",
                              "parts": [{"text": m["content"]}]} for m in chat],
                "generationConfig": {"maxOutputTokens": max_tokens}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        return f"{base}/models/{model}:generateContent", headers, body
    raise ValueError(f"loại nhà cung cấp không hỗ trợ: {kind!r}")


def parse_answer(kind, data):
    """(chữ trả lời, số token). Trả về (None, _) khi không đọc được."""
    try:
        if kind in ("openai", "ollama"):
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


def ask(request):
    provider = request.get("provider") or {}
    kind = provider.get("type", "")
    secret = read_secret(provider.get("secret_ref"))
    if provider.get("secret_ref") and not secret:
        return fail("secret", ref=provider["secret_ref"])
    try:
        url, headers, body = build_request(provider, request["model"], request["messages"],
                                           request.get("max_tokens", 1000), secret)
    except (ValueError, KeyError) as exc:
        return fail("config", detail=str(exc))
    timeout = request.get("timeout", DEFAULT_TIMEOUT)
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
        text, usage = parse_answer(kind, data)
        if text is None:
            return fail("answer")
        return {"ok": True, "text": text, "usage": usage}
    return fail("quota")


def main():
    try:
        request = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        print(json.dumps(fail("config", detail=str(exc))), flush=True)
        return 1
    action = request.get("action")
    result = ask(request) if action == "ask" else fail("config", detail=f"việc không hỗ trợ: {action!r}")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
