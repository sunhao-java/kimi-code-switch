from __future__ import annotations

from typing import Any


THEME_OPTIONS = (
    ("深海蓝（默认）", "ocean"),
    ("石墨灰", "graphite"),
    ("琥珀终端", "ember"),
)

THEME_LABELS = {value: label for label, value in THEME_OPTIONS}

SHORTCUT_SCHEMES: dict[str, dict[str, Any]] = {
    "default": {
        "label": "标准方案（默认）",
        "description": "保留当前 `Ctrl+数字`、`F6`、`F7~F10` 方案。",
        "aliases": {},
        "lines": [
            "页签：Ctrl+1..6",
            "预览：F6",
            "摘要卡：F7 / F8 / F9",
            "关于：F10",
            "搜索：/ 或 Ctrl+F",
        ],
    },
    "letters": {
        "label": "字母增强",
        "description": "在标准方案上追加一组更像控制台面板的字母快捷键。",
        "aliases": {
            "ctrl+shift+p": "switch_to_profiles",
            "ctrl+shift+r": "switch_to_providers",
            "ctrl+shift+m": "switch_to_models",
            "ctrl+shift+v": "switch_to_preview_tab",
            "ctrl+shift+s": "switch_to_settings",
            "ctrl+shift+h": "switch_to_help",
            "ctrl+shift+o": "preview_current",
        },
        "lines": [
            "页签增强：Ctrl+Shift+P / R / M / V / S / H",
            "预览增强：Ctrl+Shift+O",
            "标准方案快捷键仍然可用",
        ],
    },
}

SHORTCUT_SCHEME_OPTIONS = tuple(
    (str(item["label"]), key) for key, item in SHORTCUT_SCHEMES.items()
)

BASE_APP_CSS = """
    Screen {
        layout: vertical;
        background: #071018;
        color: #e5edf7;
    }

    Header {
        dock: top;
        background: #0a1624;
        color: #f4f8fc;
    }

    Footer {
        dock: bottom;
        background: #0a1624;
        color: #9db0c7;
    }

    #summary-bar {
        dock: top;
        height: 7;
        padding: 1 2 0 2;
    }

    .summary-card {
        width: 1fr;
        height: 6;
        margin-right: 1;
        padding: 1 2;
        background: #0c1727;
        border: round #1f3550;
        color: #d8e5f2;
    }

    .summary-card:focus {
        background: #16314d;
        border: round #f8fafc;
        color: #f8fbff;
        text-style: bold;
    }

    .summary-card.-accent {
        border: round #1297a6;
    }

    .summary-card.-hot {
        border: round #3b82f6;
    }

    .summary-card.-warm {
        border: round #f59e0b;
    }

    #about-open {
        width: 13;
        min-width: 13;
        height: 6;
        margin-left: 1;
        padding: 1 2;
        background: #0c1727;
        color: #d8e5f2;
        border: round #1f3550;
    }

    #about-open:focus {
        background: #16314d;
        border: round #f8fafc;
        color: #f8fbff;
        text-style: bold;
    }

    #tabs {
        height: 1fr;
        background: #08111d;
        padding: 0 1 1 1;
    }

    #tabs > ContentTabs {
        background: #09131f;
        border-bottom: solid #1b3149;
        padding: 0 1;
    }

    #tabs > ContentTabs Tab {
        color: #7f96b3;
        background: transparent;
        padding: 0 2;
        margin-right: 1;
    }

    #tabs > ContentTabs Tab.-active {
        color: #eaf2fb;
        background: #12304b;
        text-style: bold;
    }

    #tabs > ContentTabs:focus {
        background: #0d1927;
        border-bottom: solid #3b82f6;
    }

    #tabs > ContentTabs:focus Tab {
        color: #b7c7d9;
    }

    #tabs > ContentTabs:focus Tab.-active {
        color: #ffffff;
        background: #1d4ed8;
        text-style: bold reverse;
    }

    .workspace {
        height: 1fr;
        padding: 1 2;
    }

    .list-panel {
        width: 1fr;
        border: round #274b73;
        background: #0b1625;
        padding: 1 1 0 1;
        margin-right: 1;
    }

    .list-panel:focus-within {
        border: round #60a5fa;
        background: #0d1b2c;
    }

    .form-panel {
        width: 48;
        min-width: 42;
        border: round #1b7f7b;
        background: #0d1828;
        padding: 1 2;
    }

    .form-panel:focus-within {
        border: round #60a5fa;
        background: #102033;
    }

    .panel-title {
        text-style: bold;
        color: #7dd3fc;
        margin-bottom: 1;
    }

    .filter-input {
        margin-bottom: 1;
    }

    .field-label {
        color: #8ba3c1;
        margin-top: 1;
        margin-bottom: 0;
    }

    .wide-input {
        width: 1fr;
    }

    DataTable {
        height: 1fr;
        background: #09131f;
        color: #e5edf7;
    }

    DataTable > .datatable--header {
        background: #122438;
        color: #f3f8fd;
    }

    DataTable:focus {
        background: #0b1624;
    }

    DataTable:focus > .datatable--cursor {
        background: #1d4ed8;
        color: #f8fbff;
        text-style: bold;
    }

    DataTable:focus > .datatable--fixed-cursor,
    DataTable:focus > .datatable--header-cursor {
        background: #2563eb;
        color: #ffffff;
        text-style: bold;
    }

    Select, Input {
        width: 1fr;
        background: #08111c;
        color: #f3f8fd;
        border: tall #20374f;
    }

    Input:focus {
        background: #10263d;
        border: tall #60a5fa;
        color: #f8fbff;
    }

    Select:focus > SelectCurrent {
        background: #10263d;
        border: tall #60a5fa;
        color: #f8fbff;
    }

    .checkbox-group {
        height: auto;
        margin-top: 1;
    }

    .checkbox-group Checkbox {
        margin-bottom: 1;
    }

    Checkbox:focus {
        background: #10263d;
        border: tall #60a5fa;
        color: #f8fbff;
    }

    .button-bar {
        height: auto;
        margin-top: 1;
    }

    .button-bar Button {
        margin-right: 1;
        min-width: 10;
        background: #112339;
        color: #e5edf7;
        border: none;
    }

    .button-bar Button:focus {
        background: #1d4ed8;
        color: #ffffff;
        text-style: bold;
    }

    Button.-primary {
        background: #38bdf8;
        color: #06111d;
        text-style: bold;
    }

    Button.-error {
        background: #ef4444;
        color: #fff7f7;
    }

    .preview-shell {
        height: 1fr;
        padding: 1 2;
    }

    .preview-meta {
        height: auto;
        padding: 0 0 1 0;
        color: #94a8c0;
    }

    #preview-tabs > ContentTabs {
        background: #09131f;
        border-bottom: solid #1b3149;
        padding: 0 1;
    }

    #preview-tabs > ContentTabs Tab {
        color: #7f96b3;
        background: transparent;
        padding: 0 2;
        margin-right: 1;
    }

    #preview-tabs > ContentTabs Tab.-active {
        color: #eaf2fb;
        background: #12304b;
        text-style: bold;
    }

    #preview-tabs > ContentTabs:focus {
        background: #0d1927;
        border-bottom: solid #3b82f6;
    }

    #preview-tabs > ContentTabs:focus Tab {
        color: #b7c7d9;
    }

    #preview-tabs > ContentTabs:focus Tab.-active {
        color: #ffffff;
        background: #1d4ed8;
        text-style: bold reverse;
    }

    .preview-panel {
        height: 1fr;
        border: round #334e68;
        background: #0b1625;
        padding: 1;
    }

    .preview-panel:focus,
    .preview-panel:focus-within {
        border: round #60a5fa;
        background: #102033;
    }

    #status {
        height: auto;
        color: #6ee7b7;
        padding: 0 2 1 2;
    }

    #help-view {
        padding: 1 2;
    }

    #settings-description,
    #settings-shortcuts-summary,
    #settings-defaults {
        height: auto;
        margin-top: 1;
        padding: 1;
        border: round #274b73;
        background: #09131f;
        color: #d8e5f2;
    }
"""


def _theme_override_css(
    theme_name: str,
    *,
    screen_bg: str,
    text: str,
    header_bg: str,
    footer_text: str,
    card_bg: str,
    card_border: str,
    card_focus_bg: str,
    tab_bg: str,
    tab_focus_border: str,
    tab_active_bg: str,
    tab_active_focus_bg: str,
    tab_text: str,
    tab_active_text: str,
    panel_bg: str,
    panel_focus_bg: str,
    panel_border: str,
    panel_focus_border: str,
    title: str,
    label: str,
    input_bg: str,
    input_focus_bg: str,
    input_border: str,
    input_focus_border: str,
    table_header_bg: str,
    cursor_bg: str,
    button_bg: str,
    button_focus_bg: str,
    primary_button_bg: str,
    primary_button_text: str,
    status: str,
    preview_meta: str,
) -> str:
    return f"""
    Screen.-theme-{theme_name} {{
        background: {screen_bg};
        color: {text};
    }}

    Screen.-theme-{theme_name} Header,
    Screen.-theme-{theme_name} Footer {{
        background: {header_bg};
    }}

    Screen.-theme-{theme_name} Footer {{
        color: {footer_text};
    }}

    Screen.-theme-{theme_name} .summary-card,
    Screen.-theme-{theme_name} #about-open {{
        background: {card_bg};
        border: round {card_border};
        color: {text};
    }}

    Screen.-theme-{theme_name} .summary-card:focus,
    Screen.-theme-{theme_name} #about-open:focus {{
        background: {card_focus_bg};
        border: round {tab_focus_border};
        color: {tab_active_text};
    }}

    Screen.-theme-{theme_name} #tabs,
    Screen.-theme-{theme_name} #preview-tabs > ContentTabs,
    Screen.-theme-{theme_name} #tabs > ContentTabs {{
        background: {tab_bg};
    }}

    Screen.-theme-{theme_name} #tabs > ContentTabs,
    Screen.-theme-{theme_name} #preview-tabs > ContentTabs {{
        border-bottom: solid {panel_border};
    }}

    Screen.-theme-{theme_name} #tabs > ContentTabs Tab,
    Screen.-theme-{theme_name} #preview-tabs > ContentTabs Tab {{
        color: {tab_text};
    }}

    Screen.-theme-{theme_name} #tabs > ContentTabs Tab.-active,
    Screen.-theme-{theme_name} #preview-tabs > ContentTabs Tab.-active {{
        color: {tab_active_text};
        background: {tab_active_bg};
    }}

    Screen.-theme-{theme_name} #tabs > ContentTabs:focus,
    Screen.-theme-{theme_name} #preview-tabs > ContentTabs:focus {{
        background: {tab_bg};
        border-bottom: solid {tab_focus_border};
    }}

    Screen.-theme-{theme_name} #tabs > ContentTabs:focus Tab,
    Screen.-theme-{theme_name} #preview-tabs > ContentTabs:focus Tab {{
        color: {text};
    }}

    Screen.-theme-{theme_name} #tabs > ContentTabs:focus Tab.-active,
    Screen.-theme-{theme_name} #preview-tabs > ContentTabs:focus Tab.-active {{
        background: {tab_active_focus_bg};
    }}

    Screen.-theme-{theme_name} .list-panel,
    Screen.-theme-{theme_name} .form-panel,
    Screen.-theme-{theme_name} .preview-panel {{
        background: {panel_bg};
        border: round {panel_border};
    }}

    Screen.-theme-{theme_name} .list-panel:focus-within,
    Screen.-theme-{theme_name} .form-panel:focus-within,
    Screen.-theme-{theme_name} .preview-panel:focus,
    Screen.-theme-{theme_name} .preview-panel:focus-within {{
        background: {panel_focus_bg};
        border: round {panel_focus_border};
    }}

    Screen.-theme-{theme_name} .panel-title {{
        color: {title};
    }}

    Screen.-theme-{theme_name} .field-label,
    Screen.-theme-{theme_name} .preview-meta {{
        color: {label};
    }}

    Screen.-theme-{theme_name} DataTable {{
        background: {tab_bg};
        color: {text};
    }}

    Screen.-theme-{theme_name} DataTable > .datatable--header {{
        background: {table_header_bg};
        color: {tab_active_text};
    }}

    Screen.-theme-{theme_name} DataTable:focus > .datatable--cursor,
    Screen.-theme-{theme_name} DataTable:focus > .datatable--fixed-cursor,
    Screen.-theme-{theme_name} DataTable:focus > .datatable--header-cursor {{
        background: {cursor_bg};
    }}

    Screen.-theme-{theme_name} Select,
    Screen.-theme-{theme_name} Input {{
        background: {input_bg};
        border: tall {input_border};
        color: {text};
    }}

    Screen.-theme-{theme_name} Input:focus,
    Screen.-theme-{theme_name} Select:focus > SelectCurrent,
    Screen.-theme-{theme_name} Checkbox:focus {{
        background: {input_focus_bg};
        border: tall {input_focus_border};
        color: {tab_active_text};
    }}

    Screen.-theme-{theme_name} .button-bar Button {{
        background: {button_bg};
        color: {text};
    }}

    Screen.-theme-{theme_name} .button-bar Button:focus {{
        background: {button_focus_bg};
        color: {tab_active_text};
    }}

    Screen.-theme-{theme_name} Button.-primary {{
        background: {primary_button_bg};
        color: {primary_button_text};
    }}

    Screen.-theme-{theme_name} #status {{
        color: {status};
    }}

    Screen.-theme-{theme_name} .preview-meta {{
        color: {preview_meta};
    }}
    """


_GRAPHITE_CSS = _theme_override_css(
    "graphite",
    screen_bg="#0b0f14",
    text="#ebf1f5",
    header_bg="#11161d",
    footer_text="#97a6b2",
    card_bg="#141b23",
    card_border="#455768",
    card_focus_bg="#1c2732",
    tab_bg="#10161d",
    tab_focus_border="#93c5fd",
    tab_active_bg="#22303f",
    tab_active_focus_bg="#475569",
    tab_text="#9aaab7",
    tab_active_text="#f8fafc",
    panel_bg="#121922",
    panel_focus_bg="#1a2430",
    panel_border="#49596a",
    panel_focus_border="#93c5fd",
    title="#cbd5e1",
    label="#9fb0c1",
    input_bg="#0f141a",
    input_focus_bg="#16212c",
    input_border="#455768",
    input_focus_border="#93c5fd",
    table_header_bg="#1b2430",
    cursor_bg="#475569",
    button_bg="#1f2937",
    button_focus_bg="#475569",
    primary_button_bg="#cbd5e1",
    primary_button_text="#0f172a",
    status="#86efac",
    preview_meta="#b7c4d1",
)

_EMBER_CSS = _theme_override_css(
    "ember",
    screen_bg="#120d08",
    text="#fff3e8",
    header_bg="#1b120a",
    footer_text="#d8bfa5",
    card_bg="#21160e",
    card_border="#8b5e34",
    card_focus_bg="#392312",
    tab_bg="#1a120b",
    tab_focus_border="#f59e0b",
    tab_active_bg="#5b3112",
    tab_active_focus_bg="#b45309",
    tab_text="#d7b28c",
    tab_active_text="#fff7ed",
    panel_bg="#1f140d",
    panel_focus_bg="#2d1b0f",
    panel_border="#8b5e34",
    panel_focus_border="#fbbf24",
    title="#fbbf24",
    label="#f2c98f",
    input_bg="#160f0a",
    input_focus_bg="#2b180e",
    input_border="#8b5e34",
    input_focus_border="#fbbf24",
    table_header_bg="#3a2415",
    cursor_bg="#b45309",
    button_bg="#4a2d17",
    button_focus_bg="#b45309",
    primary_button_bg="#f59e0b",
    primary_button_text="#1c1308",
    status="#fde68a",
    preview_meta="#f6d2ac",
)


def build_app_css() -> str:
    return BASE_APP_CSS + _GRAPHITE_CSS + _EMBER_CSS
