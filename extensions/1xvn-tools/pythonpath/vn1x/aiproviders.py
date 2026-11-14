# SPDX-License-Identifier: MPL-2.0
"""Danh mục nhà cung cấp AI cài sẵn của 1xVnOffice, thuần Python.

Mục đích: người dùng chọn tên nhà cung cấp trong một danh sách thay vì tự gõ base_url và nhớ hình dạng API.

Mỗi mục có:
  id          tên ngắn, cũng là id mặc định của nhà cung cấp trong providers.json
  label       tên hiện cho người dùng
  wire        hình dạng API: openai | anthropic | gemini | azure | ollama
  base_url    địa chỉ mặc định ("" nghĩa là Agent Host tự điền, hoặc người dùng phải tự điền)
  auth        cách xác thực: key (khoá API) | oauth (đăng nhập) | none (máy chủ cục bộ)
  models      vài mô hình gợi ý; danh sách thật lấy bằng cách hỏi nhà cung cấp (xem `can_list_models`)
  note        một dòng nói rõ cần gì

Vì sao không kèm sẵn client_id cho các mục OAuth: client_id của OpenAI/Google/Microsoft gắn với một ứng dụng
đã đăng ký, và cơ quan thường tự đăng ký ứng dụng nội bộ của mình. 1xVnOffice không nhúng client_id của người
khác; người dùng dán client_id của chính họ (hoặc của cơ quan) vào bước cài đặt.
"""

OPENAI_WIRE = ("openai", "azure", "ollama")

PRESETS = [
    # ----- khoá API, hình dạng OpenAI -----
    {"id": "openai", "label": "OpenAI", "wire": "openai", "base_url": "https://api.openai.com/v1",
     "auth": "key", "models": [], "can_list_models": True,
     "note": "Khoá API lấy ở platform.openai.com."},
    {"id": "openrouter", "label": "OpenRouter (nhiều hãng qua một khoá)", "wire": "openai",
     "base_url": "https://openrouter.ai/api/v1", "auth": "key", "models": [], "can_list_models": True,
     "note": "Một khoá dùng được mô hình của nhiều hãng."},
    {"id": "groq", "label": "Groq", "wire": "openai", "base_url": "https://api.groq.com/openai/v1",
     "auth": "key", "models": [], "can_list_models": True, "note": "Khoá API lấy ở console.groq.com."},
    {"id": "deepseek", "label": "DeepSeek", "wire": "openai", "base_url": "https://api.deepseek.com/v1",
     "auth": "key", "models": [], "can_list_models": True, "note": "Khoá API lấy ở platform.deepseek.com."},
    {"id": "mistral", "label": "Mistral", "wire": "openai", "base_url": "https://api.mistral.ai/v1",
     "auth": "key", "models": [], "can_list_models": True, "note": "Khoá API lấy ở console.mistral.ai."},
    {"id": "xai", "label": "xAI (Grok)", "wire": "openai", "base_url": "https://api.x.ai/v1",
     "auth": "key", "models": [], "can_list_models": True, "note": "Khoá API lấy ở console.x.ai."},
    {"id": "together", "label": "Together AI", "wire": "openai", "base_url": "https://api.together.xyz/v1",
     "auth": "key", "models": [], "can_list_models": True, "note": "Khoá API lấy ở api.together.ai."},
    {"id": "fireworks", "label": "Fireworks AI", "wire": "openai",
     "base_url": "https://api.fireworks.ai/inference/v1", "auth": "key", "models": [], "can_list_models": True,
     "note": "Khoá API lấy ở fireworks.ai."},
    {"id": "cerebras", "label": "Cerebras", "wire": "openai", "base_url": "https://api.cerebras.ai/v1",
     "auth": "key", "models": [], "can_list_models": True, "note": "Khoá API lấy ở cloud.cerebras.ai."},

    # ----- khoá API, hình dạng riêng -----
    {"id": "anthropic", "label": "Anthropic (Claude)", "wire": "anthropic",
     "base_url": "https://api.anthropic.com/v1", "auth": "key",
     "models": ["claude-opus-5", "claude-sonnet-5-5", "claude-haiku-5-5"], "can_list_models": True,
     "note": "Khoá API lấy ở console.anthropic.com."},
    {"id": "gemini", "label": "Google Gemini (khoá API)", "wire": "gemini",
     "base_url": "https://generativelanguage.googleapis.com/v1beta", "auth": "key", "models": [],
     "can_list_models": True, "note": "Khoá API lấy ở aistudio.google.com."},

    # ----- đăng nhập OAuth -----
    {"id": "vertex", "label": "Google Cloud Vertex AI (đăng nhập Google)", "wire": "gemini",
     "base_url": "", "auth": "oauth", "models": [], "can_list_models": False,
     "model_path": "publishers/google/models",
     "oauth": {"authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
               "token_url": "https://oauth2.googleapis.com/token",
               "device_url": "https://oauth2.googleapis.com/device/code",
               "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
               "extra_auth_params": {"access_type": "offline", "prompt": "consent"}},
     "needs": ["client_id", "base_url"], "client_secret": True,
     "note": "Cần client_id OAuth loại Desktop trong dự án Google Cloud của bạn, và base_url của Vertex AI "
             "theo dự án và vùng."},
    {"id": "azure", "label": "Azure OpenAI (đăng nhập Microsoft)", "wire": "azure", "base_url": "",
     "auth": "oauth", "models": [], "can_list_models": False,
     "oauth": {"authorize_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
               "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
               "device_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode",
               "scopes": ["https://cognitiveservices.azure.com/.default", "offline_access"]},
     "needs": ["client_id", "tenant", "base_url"],
     "note": "Cần client_id và mã tenant của ứng dụng đã đăng ký trong Entra ID của cơ quan, và địa chỉ "
             "tài nguyên Azure OpenAI."},
    {"id": "azure-key", "label": "Azure OpenAI (khoá API)", "wire": "azure", "base_url": "", "auth": "key",
     "models": [], "can_list_models": False, "needs": ["base_url"],
     "note": "Địa chỉ dạng https://<tên tài nguyên>.openai.azure.com/openai, mô hình là tên deployment."},
    {"id": "oidc", "label": "Cổng AI nội bộ của cơ quan (đăng nhập SSO)", "wire": "openai", "base_url": "",
     "auth": "oauth", "models": [], "can_list_models": True,
     "oauth": {"authorize_url": "", "token_url": "", "scopes": ["openid", "offline_access"]},
     "needs": ["client_id", "authorize_url", "token_url", "base_url"],
     "note": "Dành cho cổng AI dùng chung của cơ quan có đăng nhập một lần (OIDC). Quản trị viên cho bạn "
             "client_id, địa chỉ đăng nhập và địa chỉ cổng."},

    # ----- chạy ngay trên máy, không cần khoá -----
    {"id": "ollama", "label": "Ollama (chạy trên máy này)", "wire": "ollama",
     "base_url": "http://127.0.0.1:11434/v1", "auth": "none", "models": [], "can_list_models": True,
     "note": "Không gửi gì ra mạng. Cần cài Ollama và tải mô hình trước."},
    {"id": "lmstudio", "label": "LM Studio (chạy trên máy này)", "wire": "openai",
     "base_url": "http://127.0.0.1:1234/v1", "auth": "none", "models": [], "can_list_models": True,
     "note": "Không gửi gì ra mạng. Bật máy chủ cục bộ trong LM Studio trước."},
    {"id": "vllm", "label": "vLLM hoặc máy chủ nội bộ (hình dạng OpenAI)", "wire": "openai",
     "base_url": "http://127.0.0.1:8000/v1", "auth": "none", "models": [], "can_list_models": True,
     "needs": ["base_url"], "note": "Máy chủ trong mạng cơ quan nói được hình dạng OpenAI."},
]

BY_ID = {preset["id"]: preset for preset in PRESETS}


def listing(auth=None):
    """Danh mục để hiện cho người dùng, lọc theo cách xác thực nếu cần."""
    return [preset for preset in PRESETS if auth is None or preset["auth"] == auth]


def get(preset_id):
    """Một mục trong danh mục. Ném KeyError khi không có."""
    return BY_ID[preset_id]


def summary(preset):
    """Một dòng mô tả cho hộp chọn."""
    how = {"key": "khoá API", "oauth": "đăng nhập", "none": "chạy trên máy"}[preset["auth"]]
    return f"{preset['label']} — {how}"


def secret_ref(preset_id):
    """Tên mục trong kho bí mật của hệ điều hành. Không phải giá trị khoá, chỉ là tên."""
    return f"1xvnoffice/{preset_id}"


def client_secret_ref(provider_id):
    """Tên mục cất client secret của ứng dụng OAuth. Google cấp secret này cho cả ứng dụng Desktop."""
    return f"{secret_ref(provider_id)}/client_secret"


def missing(preset, values):
    """Những thứ người dùng còn phải điền cho mục này."""
    return [field for field in (preset.get("needs") or []) if not (values or {}).get(field)]


def fill(preset, values):
    """Dựng mục providers.json từ một preset và những gì người dùng điền.

    Không nhận và không trả về giá trị khoá hay thẻ: chỉ có `secret_ref` trỏ tới kho bí mật.
    """
    values = dict(values or {})
    lack = missing(preset, values)
    if lack:
        raise ValueError("còn thiếu: " + ", ".join(lack))
    entry = {"id": values.get("id") or preset["id"], "type": preset["wire"], "auth": preset["auth"],
             "models": list(values.get("models") or preset["models"])}
    base = values.get("base_url") or preset["base_url"]
    if base:
        entry["base_url"] = base.rstrip("/")
    if preset.get("model_path"):
        entry["model_path"] = preset["model_path"]
    if preset["wire"] == "azure":
        entry["api_version"] = values.get("api_version") or "2024-10-21"
    if preset["auth"] != "none":
        entry["secret_ref"] = values.get("secret_ref") or secret_ref(entry["id"])
    if preset["auth"] == "oauth":
        config = dict(preset.get("oauth") or {})
        if preset.get("client_secret"):
            config["client_secret_ref"] = client_secret_ref(entry["id"])
        for field in ("authorize_url", "token_url", "device_url"):
            if values.get(field):
                config[field] = values[field]
            elif config.get(field) and values.get("tenant"):
                config[field] = config[field].replace("{tenant}", values["tenant"])
        if values.get("scopes"):
            config["scopes"] = list(values["scopes"])
        config["client_id"] = values["client_id"]
        entry["oauth"] = config
    return entry
