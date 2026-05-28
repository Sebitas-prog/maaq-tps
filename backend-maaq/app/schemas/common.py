from typing import Any


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"ok": True, "data": data}
    if meta is not None:
        response["meta"] = meta
    return response
