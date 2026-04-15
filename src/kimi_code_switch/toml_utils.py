from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def dumps_toml(data: Mapping[str, Any]) -> str:
    lines: list[str] = []
    _write_table(lines, [], data)
    return "\n".join(lines).rstrip() + "\n"


def _write_table(lines: list[str], path: list[str], table: Mapping[str, Any]) -> None:
    scalar_items: list[tuple[str, Any]] = []
    table_items: list[tuple[str, Mapping[str, Any]]] = []

    for key, value in table.items():
        if value is None:
            continue
        if isinstance(value, Mapping):
            table_items.append((key, value))
        else:
            scalar_items.append((key, value))

    if path:
        lines.append(f"[{'.'.join(_format_key(part) for part in path)}]")

    for key, value in scalar_items:
        lines.append(f"{_format_key(key)} = {_format_value(value)}")

    if scalar_items and table_items:
        lines.append("")

    for index, (key, value) in enumerate(table_items):
        _write_table(lines, [*path, key], value)
        if index != len(table_items) - 1:
            lines.append("")


def _format_key(key: str) -> str:
    if _BARE_KEY_RE.fullmatch(key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    raise TypeError(f"Unsupported TOML value: {type(value)!r}")
