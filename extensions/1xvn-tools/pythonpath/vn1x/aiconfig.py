# SPDX-License-Identifier: MPL-2.0
"""Cấu hình AI mang khoá của chính người dùng (BYOK), thuần Python.

Tệp `providers.json` nằm trong hồ sơ người dùng. **Khoá API không bao giờ được ghi vào tệp này**: trường
`secret_ref` chỉ là tên mục trong kho bí mật của hệ điều hành (Keychain trên macOS), và chỉ tiến trình Agent Host
đọc khoá ra.

Mỗi tính năng gọi mô hình theo VAI TRÒ (soan_thao, nhanh, cuc_bo) chứ không gọi thẳng tên mô hình, nên người dùng
đổi mô hình ở một chỗ.
"""
import json
from pathlib import Path

FILENAME = "providers.json"
KINDS = ("openai", "anthropic", "gemini", "ollama", "azure")
AUTH_MODES = ("key", "oauth", "none")
DEFAULT_ROLE = "soan_thao"
EMPTY = {"providers": [], "roles": {}, "limits": {"max_output_tokens": 2000, "max_requests_per_day": 300}}


class ConfigError(ValueError):
    """Cấu hình thiếu hoặc sai."""


def path_in_profile(profile_dir):
    return Path(profile_dir) / "user" / FILENAME


def load(path):
    """Đọc cấu hình. Chưa có tệp thì trả về cấu hình rỗng, không báo lỗi."""
    file = Path(path)
    if not file.is_file():
        return json.loads(json.dumps(EMPTY))
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ConfigError(f"{FILENAME} không phải JSON hợp lệ: {exc}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{FILENAME} phải là một đối tượng JSON")
    merged = json.loads(json.dumps(EMPTY))
    merged.update(data)
    return merged


def save(path, config):
    """Ghi cấu hình, từ chối nếu có khoá API lẫn trong đó."""
    for provider in config.get("providers", []):
        for field in ("api_key", "key", "secret", "token", "access_token", "refresh_token"):
            if provider.get(field):
                raise ConfigError(f"không được ghi khoá API vào {FILENAME} (nhà cung cấp {provider.get('id')!r}); "
                                  "chỉ ghi secret_ref trỏ tới kho bí mật của hệ điều hành")
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def problems(config):
    """Danh sách điểm sai trong cấu hình, rỗng nghĩa là dùng được."""
    out = []
    ids = set()
    for index, provider in enumerate(config.get("providers", []), 1):
        name = provider.get("id") or f"#{index}"
        if not provider.get("id"):
            out.append(f"nhà cung cấp {name}: thiếu id")
        elif provider["id"] in ids:
            out.append(f"nhà cung cấp {name}: id bị trùng")
        else:
            ids.add(provider["id"])
        if provider.get("type") not in KINDS:
            out.append(f"nhà cung cấp {name}: loại {provider.get('type')!r} không hỗ trợ "
                       f"(chọn một trong {', '.join(KINDS)})")
        if not provider.get("models"):
            out.append(f"nhà cung cấp {name}: chưa khai báo mô hình nào")
        out.extend(_auth_problems(provider, name))
    for role, target in (config.get("roles") or {}).items():
        try:
            resolve(config, role)
        except ConfigError as exc:
            out.append(f"vai trò {role!r} ({target}): {exc}")
    return out


def resolve(config, role=DEFAULT_ROLE):
    """(nhà cung cấp, tên mô hình) cho một vai trò. Vai trò chưa đặt thì dùng nhà cung cấp đầu tiên."""
    providers = config.get("providers") or []
    if not providers:
        raise ConfigError("chưa khai báo nhà cung cấp AI nào")
    target = (config.get("roles") or {}).get(role)
    if not target:
        first = providers[0]
        models = first.get("models") or []
        if not models:
            raise ConfigError(f"nhà cung cấp {first.get('id')!r} chưa khai báo mô hình nào")
        return first, models[0]
    provider_id, _, model = target.partition("/")
    found = next((p for p in providers if p.get("id") == provider_id), None)
    if found is None:
        raise ConfigError(f"không thấy nhà cung cấp {provider_id!r}")
    if not model:
        models = found.get("models") or []
        if not models:
            raise ConfigError(f"nhà cung cấp {provider_id!r} chưa khai báo mô hình nào")
        return found, models[0]
    if found.get("models") and model not in found["models"]:
        raise ConfigError(f"mô hình {model!r} không có trong danh sách của {provider_id!r}")
    return found, model


def add_provider(config, provider_id, kind, models, secret_ref="", base_url="", role=None):
    """Thêm hoặc thay một nhà cung cấp, trả về cấu hình mới. Không nhận khoá API."""
    if kind not in KINDS:
        raise ConfigError(f"loại {kind!r} không hỗ trợ")
    entry = {"id": provider_id, "type": kind, "models": list(models)}
    if secret_ref:
        entry["secret_ref"] = secret_ref
    if base_url:
        entry["base_url"] = base_url
    out = json.loads(json.dumps(config))
    out["providers"] = [p for p in out.get("providers", []) if p.get("id") != provider_id] + [entry]
    if role and models:
        out.setdefault("roles", {})[role] = f"{provider_id}/{models[0]}"
    return out


def auth_mode(provider):
    """Cách xác thực của một nhà cung cấp. Cấu hình cũ chưa có trường `auth` thì suy ra cho tương thích."""
    mode = (provider or {}).get("auth")
    if mode in AUTH_MODES:
        return mode
    provider = provider or {}
    if provider.get("oauth"):
        return "oauth"
    if provider.get("secret_ref"):
        return "key"
    # Suy ra như bản trước khi có trường `auth`: máy chủ cục bộ và máy chủ tự dựng nói hình dạng OpenAI thì
    # không đòi khoá; dịch vụ đám mây thì đòi.
    if provider.get("type") == "ollama" or (provider.get("type") == "openai" and provider.get("base_url")):
        return "none"
    return "key"


def _auth_problems(provider, name):
    """Điểm sai ở phần xác thực của một nhà cung cấp."""
    out = []
    mode = auth_mode(provider)
    if provider.get("auth") and provider["auth"] not in AUTH_MODES:
        out.append(f"nhà cung cấp {name}: cách xác thực {provider['auth']!r} không hỗ trợ "
                   f"(chọn một trong {', '.join(AUTH_MODES)})")
        return out
    if mode in ("key", "oauth") and not provider.get("secret_ref"):
        out.append(f"nhà cung cấp {name}: thiếu secret_ref (tên MỤC trong kho bí mật, không phải giá trị khoá)")
    if provider.get("type") == "ollama" and provider.get("secret_ref"):
        out.append(f"nhà cung cấp {name}: máy chủ cục bộ không cần khoá")
    elif mode == "none" and provider.get("secret_ref"):
        out.append(f"nhà cung cấp {name}: đã chọn 'không cần khoá' thì bỏ secret_ref đi")
    if mode == "oauth":
        config = provider.get("oauth") or {}
        for field in ("authorize_url", "token_url", "client_id"):
            if not config.get(field) and not (field == "authorize_url" and config.get("device_url")):
                out.append(f"nhà cung cấp {name}: cấu hình OAuth thiếu {field}")
        for field in ("access_token", "refresh_token", "client_secret"):
            if config.get(field):  # client_secret_ref (chỉ là TÊN mục) thì được; giá trị thì không
                out.append(f"nhà cung cấp {name}: không được ghi {field} vào {FILENAME}; "
                           f"thẻ nằm trong kho bí mật của hệ điều hành")
    if mode != "oauth" and provider.get("oauth"):
        out.append(f"nhà cung cấp {name}: có khối oauth nhưng auth không phải 'oauth'")
    if provider.get("type") == "azure" and not provider.get("base_url"):
        out.append(f"nhà cung cấp {name}: Azure OpenAI cần base_url của tài nguyên")
    return out


def put_provider(config, entry, role=None):
    """Thêm hoặc thay một nhà cung cấp đã dựng sẵn (xem vn1x.aiproviders.fill). Không nhận khoá hay thẻ."""
    out = json.loads(json.dumps(config))
    out["providers"] = [p for p in out.get("providers", []) if p.get("id") != entry["id"]] + [json.loads(json.dumps(entry))]
    if role and entry.get("models"):
        out.setdefault("roles", {})[role] = f"{entry['id']}/{entry['models'][0]}"
    elif role:
        out.setdefault("roles", {})[role] = entry["id"]
    return out


def remove_provider(config, provider_id):
    """Bỏ một nhà cung cấp và mọi vai trò đang trỏ tới nó."""
    out = json.loads(json.dumps(config))
    out["providers"] = [p for p in out.get("providers", []) if p.get("id") != provider_id]
    out["roles"] = {role: target for role, target in (out.get("roles") or {}).items()
                    if target.partition("/")[0] != provider_id}
    return out
