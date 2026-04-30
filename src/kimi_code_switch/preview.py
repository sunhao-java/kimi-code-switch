from __future__ import annotations

import difflib
from pathlib import Path


def read_file_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def unified_diff(old_text: str, new_text: str, fromfile: str, tofile: str) -> str:
    diff_lines = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )
    )
    if not diff_lines:
        return "# 无变更\n"
    return "\n".join(diff_lines) + "\n"


def extract_compact_diff_lines(diff_text: str) -> dict[str, list[str]]:
    changes: dict[str, list[str]] = {"added": [], "removed": [], "modified": []}
    pending_removed: list[str] = []
    pending_added: list[str] = []

    def flush_pending() -> None:
        pairs = min(len(pending_removed), len(pending_added))
        for index in range(pairs):
            changes["modified"].append(
                f"  ~ {pending_removed[index]} -> {pending_added[index]}"
            )
        for line in pending_added[pairs:]:
            changes["added"].append(f"  + {line}")
        for line in pending_removed[pairs:]:
            changes["removed"].append(f"  - {line}")
        pending_removed.clear()
        pending_added.clear()

    for line in diff_text.splitlines():
        if not line or line.startswith(("---", "+++")):
            continue
        if line.startswith("@@"):
            flush_pending()
            continue
        if line.startswith("+"):
            pending_added.append(line[1:])
        elif line.startswith("-"):
            if pending_added:
                flush_pending()
            pending_removed.append(line[1:])
        else:
            flush_pending()
    flush_pending()
    return changes


def render_compact_sections(changes: dict[str, list[str]]) -> list[str]:
    labels = (
        ("新增", "added"),
        ("删除", "removed"),
        ("修改", "modified"),
    )
    lines: list[str] = []
    for title, key in labels:
        items = changes[key]
        if not items:
            continue
        lines.append(f"  {title}")
        lines.extend(f"    {item.strip()}" for item in items)
    return lines or ["  无变更"]


def build_compact_preview(
    config_diff: str,
    profiles_diff: str,
    source_tab_label: str,
) -> str:
    config_changes = extract_compact_diff_lines(config_diff)
    profile_changes = extract_compact_diff_lines(profiles_diff)
    sections = [
        "仅看变更",
        "",
        f"来源页签：{source_tab_label}",
        "",
        "config.toml",
        *render_compact_sections(config_changes),
        "",
        "config.profiles.toml",
        *render_compact_sections(profile_changes),
    ]
    return "\n".join(sections)
