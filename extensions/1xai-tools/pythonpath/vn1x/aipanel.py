# SPDX-License-Identifier: MPL-2.0
"""Phần không cần office của thanh bên AI (dòng trạng thái), để kiểm được ngoài app."""


def status(config, texts):
    """Dòng trạng thái đầu panel: đang dùng AI nào, hoặc mời gắn tài khoản."""
    providers = (config or {}).get("providers") or []
    if not providers:
        return texts["panel_no_ai"]
    first = providers[0]
    model = (first.get("models") or [""])[0]
    return texts["panel_ai"].format(name=first.get("id", "?") + (f" · {model}" if model else ""))
