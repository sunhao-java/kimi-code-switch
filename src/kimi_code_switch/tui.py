from __future__ import annotations

import difflib
from pathlib import Path
from typing import Optional, Union

from rich.syntax import Syntax
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)
from textual.widgets._tabbed_content import ContentTabs

from . import __version__
from .config_store import (
    AppState,
    PROFILE_FILENAME,
    Profile,
    apply_profile,
    build_config_document,
    build_profiles_document,
    clone_state,
    delete_model,
    delete_profile,
    delete_provider,
    load_state,
    save_state,
    upsert_model,
    upsert_profile,
    upsert_provider,
)
from .panel_settings import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_SHORTCUT_SCHEME,
    DEFAULT_THEME,
    PanelSettings,
    default_panel_settings,
    save_panel_settings,
)


THEME_OPTIONS = (
    ("深海蓝（默认）", "ocean"),
    ("石墨灰", "graphite"),
    ("琥珀终端", "ember"),
)

THEME_LABELS = {value: label for label, value in THEME_OPTIONS}

SHORTCUT_SCHEMES: dict[str, dict[str, object]] = {
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

ABOUT_LINES = (
    ("英文名", "Hulk Sun"),
    ("GitHub", "https://github.com/sunhao-java"),
    ("博客", "https://www.crazy-coder.cn"),
    ("邮箱", "sunhao.java@gmail.com"),
)


class SummaryCard(Static, can_focus=True):
    BINDINGS = [
        Binding("enter", "select_card", "进入", show=False),
        Binding("left", "focus_previous_summary", "上一个", show=False),
        Binding("right", "focus_next_summary", "下一个", show=False),
        Binding("down", "focus_main_menu", "返回页签", show=False),
    ]

    class Selected(Message):
        def __init__(self, card: "SummaryCard") -> None:
            self.card = card
            super().__init__()

    def __init__(self, target_tab: str, *, id: str, classes: str) -> None:
        super().__init__("", id=id, classes=classes)
        self.target_tab = target_tab

    def action_select_card(self) -> None:
        self.post_message(self.Selected(self))

    def action_focus_previous_summary(self) -> None:
        app = self.app
        if isinstance(app, ConfigPanelApp):
            app.focus_previous_summary_item()

    def action_focus_next_summary(self) -> None:
        app = self.app
        if isinstance(app, ConfigPanelApp):
            app.focus_next_summary_item()

    def action_focus_main_menu(self) -> None:
        app = self.app
        if isinstance(app, ConfigPanelApp):
            app.focus_main_menu_from_summary()

    def key_left(self, event) -> None:
        event.stop()
        self.action_focus_previous_summary()

    def key_right(self, event) -> None:
        event.stop()
        self.action_focus_next_summary()

    def key_down(self, event) -> None:
        event.stop()
        self.action_focus_main_menu()

    def on_click(self) -> None:
        self.post_message(self.Selected(self))


class AboutButton(Button):
    def key_left(self, event) -> None:
        event.stop()
        app = self.app
        if isinstance(app, ConfigPanelApp):
            app.focus_previous_summary_item()

    def key_right(self, event) -> None:
        event.stop()
        app = self.app
        if isinstance(app, ConfigPanelApp):
            app.focus_next_summary_item()

    def key_down(self, event) -> None:
        event.stop()
        app = self.app
        if isinstance(app, ConfigPanelApp):
            app.focus_main_menu_from_summary()


class AboutDialog(ModalScreen[None]):
    CSS = """
    AboutDialog {
        align: center middle;
        background: rgba(2, 6, 23, 0.72);
    }

    #about-dialog {
        width: 72;
        max-width: 90%;
        height: auto;
        padding: 1 2;
        background: #0d1828;
        border: round #3b82f6;
    }

    #about-title {
        color: #7dd3fc;
        text-style: bold;
        margin-bottom: 1;
    }

    .about-section {
        margin-top: 1;
        color: #d8e5f2;
    }

    #about-version {
        color: #fbbf24;
        text-style: bold;
    }

    #about-close {
        margin-top: 1;
        width: 16;
    }
    """

    BINDINGS = [Binding("escape", "close_about", "关闭", show=False)]

    def compose(self) -> ComposeResult:
        info_lines = "\n".join(f"{label}：{value}" for label, value in ABOUT_LINES)
        with Vertical(id="about-dialog"):
            yield Static("关于 Kimi 配置面板", id="about-title")
            yield Static(f"版本号：{__version__}", id="about-version", classes="about-section")
            yield Static(info_lines, id="about-body", classes="about-section")
            yield Static("按 Esc 或点击下方按钮关闭。", classes="about-section")
            yield Button("关闭", id="about-close", variant="primary")

    def action_close_about(self) -> None:
        self.dismiss()

    def on_button_pressed(self, _: Button.Pressed) -> None:
        self.dismiss()


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


class ConfigPanelApp(App[None]):
    ENABLE_COMMAND_PALETTE = False

    MAIN_TAB_SHORTCUTS = {
        "profiles": "Ctrl+1",
        "providers": "Ctrl+2",
        "models": "Ctrl+3",
        "preview": "Ctrl+4",
        "settings": "Ctrl+5",
        "help": "Ctrl+6",
    }

    SUMMARY_SHORTCUTS = {
        "profiles": "F7",
        "models": "F8",
        "providers": "F9",
        "about": "F10",
    }

    CSS = """
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
    """ + _theme_override_css(
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
    ) + _theme_override_css(
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

    BINDINGS = [
        ("q", "quit", "退出"),
        Binding("ctrl+1", "switch_to_profiles", "配置Profile页", show=False),
        Binding("ctrl+2", "switch_to_providers", "提供方页", show=False),
        Binding("ctrl+3", "switch_to_models", "模型页", show=False),
        Binding("ctrl+4", "switch_to_preview_tab", "预览页", show=False),
        Binding("ctrl+5", "switch_to_settings", "设置页", show=False),
        Binding("ctrl+6", "switch_to_help", "帮助页", show=False),
        Binding("f7", "focus_profile_summary", "当前配置Profile", show=False),
        Binding("f8", "focus_model_summary", "当前生效模型", show=False),
        Binding("f9", "focus_inventory_summary", "提供方", show=False),
        Binding("f10", "show_about", "关于", show=True),
        Binding("left", "previous_summary_item", "上一个摘要", show=False),
        Binding("right", "next_summary_item", "下一个摘要", show=False),
        Binding("tab", "next_menu", "下一项", show=False, priority=True),
        Binding("shift+tab", "previous_menu", "上一项", show=False, priority=True),
        ("/", "focus_filter", "搜索"),
        ("ctrl+f", "focus_filter", "搜索"),
        ("escape", "clear_filter", "清空搜索"),
        Binding("enter", "activate_context", "进入", show=False),
        ("ctrl+n", "new_item", "新建"),
        ("ctrl+s", "save_item", "保存"),
        ("ctrl+d", "delete_item", "删除"),
        ("ctrl+c", "clone_profile", "克隆"),
        ("ctrl+a", "activate_profile", "启用"),
        ("f6", "preview_current", "预览"),
    ]

    def __init__(
        self,
        state: AppState,
        panel_settings: Optional[PanelSettings] = None,
    ) -> None:
        super().__init__()
        self.state = state
        self.panel_settings = panel_settings or default_panel_settings(
            config_path=state.config_path,
            profiles_path=state.profiles_path,
        )
        self.title = "Kimi 配置面板"
        self.sub_title = "提供方、模型、配置Profile与面板设置"

        self.selected_profile_name: Optional[str] = None
        self.selected_provider_name: Optional[str] = None
        self.selected_model_name: Optional[str] = None
        self.selected_settings_key = "config_path"
        self.last_editor_tab = "profiles"
        self.preview_payload: dict[str, str] = {}

        self.provider_name_locked = False
        self.model_name_locked = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="summary-bar"):
            yield SummaryCard("profiles", id="summary-profile", classes="summary-card -hot")
            yield SummaryCard("providers", id="summary-inventory", classes="summary-card -warm")
            yield SummaryCard("models", id="summary-model", classes="summary-card -accent")
            yield AboutButton(f"关于 {self.SUMMARY_SHORTCUTS['about']}", id="about-open")
        with TabbedContent(initial="profiles", id="tabs"):
            with TabPane("配置Profile Ctrl+1", id="profiles"):
                with Horizontal(classes="workspace"):
                    with Vertical(classes="list-panel"):
                        yield Static("配置Profile列表", classes="panel-title")
                        yield Input(
                            placeholder="搜索配置Profile名称 / 标签",
                            id="profiles-filter",
                            classes="filter-input",
                        )
                        yield DataTable(id="profiles-table")
                    with VerticalScroll(classes="form-panel"):
                        yield Static("配置Profile编辑器", classes="panel-title")
                        yield Label("配置Profile名称", classes="field-label")
                        yield Input(id="profile-name", classes="wide-input")
                        yield Label("显示名称", classes="field-label")
                        yield Input(id="profile-label", classes="wide-input")
                        yield Label("默认模型", classes="field-label")
                        yield Select([], id="profile-model", allow_blank=True)
                        yield Label("默认编辑器", classes="field-label")
                        yield Input(id="profile-editor", classes="wide-input")
                        yield Label("主题", classes="field-label")
                        yield Input(id="profile-theme", classes="wide-input")
                        with Vertical(classes="checkbox-group"):
                            yield Checkbox("开启思考模式", id="profile-thinking")
                            yield Checkbox("开启 YOLO", id="profile-yolo")
                            yield Checkbox("开启计划模式", id="profile-plan-mode")
                            yield Checkbox("显示思考流", id="profile-show-thinking")
                            yield Checkbox(
                                "合并全部可用技能",
                                id="profile-merge-skills",
                            )
                        with Horizontal(classes="button-bar"):
                            yield Button("新建", id="profile-new")
                            yield Button("预览", id="profile-preview")
                            yield Button("保存", id="profile-save", variant="primary")
                            yield Button("克隆", id="profile-clone")
                            yield Button("启用", id="profile-activate")
                            yield Button("删除", id="profile-delete", variant="error")

            with TabPane("提供方 Ctrl+2", id="providers"):
                with Horizontal(classes="workspace"):
                    with Vertical(classes="list-panel"):
                        yield Static("提供方列表", classes="panel-title")
                        yield Input(
                            placeholder="搜索提供方名称 / 地址 / 类型",
                            id="providers-filter",
                            classes="filter-input",
                        )
                        yield DataTable(id="providers-table")
                    with VerticalScroll(classes="form-panel"):
                        yield Static("提供方编辑器", classes="panel-title")
                        yield Label("提供方名称", classes="field-label")
                        yield Input(id="provider-name", classes="wide-input")
                        yield Label("提供方类型", classes="field-label")
                        yield Input(id="provider-type", classes="wide-input")
                        yield Label("基础地址", classes="field-label")
                        yield Input(id="provider-base-url", classes="wide-input")
                        yield Label("接口密钥", classes="field-label")
                        yield Input(id="provider-api-key", password=True, classes="wide-input")
                        with Horizontal(classes="button-bar"):
                            yield Button("新建", id="provider-new")
                            yield Button("预览", id="provider-preview")
                            yield Button("保存", id="provider-save", variant="primary")
                            yield Button("删除", id="provider-delete", variant="error")

            with TabPane("模型 Ctrl+3", id="models"):
                with Horizontal(classes="workspace"):
                    with Vertical(classes="list-panel"):
                        yield Static("模型列表", classes="panel-title")
                        yield Input(
                            placeholder="搜索模型名称 / provider / 远端模型",
                            id="models-filter",
                            classes="filter-input",
                        )
                        yield DataTable(id="models-table")
                    with VerticalScroll(classes="form-panel"):
                        yield Static("模型编辑器", classes="panel-title")
                        yield Label("所属提供方", classes="field-label")
                        yield Select([], id="model-provider", allow_blank=True)
                        yield Label("模型名称（不含提供方前缀）", classes="field-label")
                        yield Input(id="model-name", classes="wide-input")
                        yield Label("远端模型 ID", classes="field-label")
                        yield Input(id="model-remote-name", classes="wide-input")
                        yield Label("最大上下文", classes="field-label")
                        yield Input(id="model-context-size", classes="wide-input")
                        yield Label("能力列表", classes="field-label")
                        yield Input(
                            id="model-capabilities",
                            placeholder="thinking, image_in, video_in",
                            classes="wide-input",
                        )
                        with Horizontal(classes="button-bar"):
                            yield Button("新建", id="model-new")
                            yield Button("预览", id="model-preview")
                            yield Button("保存", id="model-save", variant="primary")
                            yield Button("删除", id="model-delete", variant="error")

            with TabPane("预览 Ctrl+4", id="preview"):
                with Vertical(classes="preview-shell"):
                    yield Static("", id="preview-meta", classes="preview-meta")
                    with TabbedContent(initial="preview-config", id="preview-tabs"):
                        with TabPane("config.toml", id="preview-config"):
                            with VerticalScroll(classes="preview-panel"):
                                yield Static("", id="preview-config-body")
                        with TabPane("配置 Diff", id="preview-config-diff"):
                            with VerticalScroll(classes="preview-panel"):
                                yield Static("", id="preview-config-diff-body")
                        with TabPane("profiles", id="preview-profiles"):
                            with VerticalScroll(classes="preview-panel"):
                                yield Static("", id="preview-profiles-body")
                        with TabPane("配置Profile Diff", id="preview-profiles-diff"):
                            with VerticalScroll(classes="preview-panel"):
                                yield Static("", id="preview-profiles-diff-body")
                        with TabPane("仅看变更", id="preview-compact"):
                            with VerticalScroll(classes="preview-panel"):
                                yield Static("", id="preview-compact-body")

            with TabPane("设置 Ctrl+5", id="settings"):
                with Horizontal(classes="workspace"):
                    with Vertical(classes="list-panel"):
                        yield Static("设置列表", classes="panel-title")
                        yield DataTable(id="settings-table")
                    with VerticalScroll(classes="form-panel"):
                        yield Static("面板设置", classes="panel-title")
                        yield Label("Kimi 主配置文件", classes="field-label")
                        yield Input(id="settings-config-path", classes="wide-input")
                        yield Checkbox(
                            "配置Profile路径跟随主配置目录",
                            id="settings-follow-profiles",
                        )
                        yield Label("配置Profile sidecar 文件", classes="field-label")
                        yield Input(id="settings-profiles-path", classes="wide-input")
                        yield Label("TUI 主题", classes="field-label")
                        yield Select(THEME_OPTIONS, id="settings-theme", allow_blank=False)
                        yield Label("快捷键方案", classes="field-label")
                        yield Select(
                            SHORTCUT_SCHEME_OPTIONS,
                            id="settings-shortcut-scheme",
                            allow_blank=False,
                        )
                        yield Static("", id="settings-description")
                        yield Static("", id="settings-shortcuts-summary")
                        yield Static("", id="settings-defaults")
                        with Horizontal(classes="button-bar"):
                            yield Button("恢复默认值", id="settings-reset")
                            yield Button("重新载入", id="settings-reload")
                            yield Button("保存设置", id="settings-save", variant="primary")

            with TabPane("帮助 Ctrl+6", id="help"):
                with VerticalScroll(id="help-view"):
                    yield Static("", id="help-body")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._configure_tables()
        self._configure_settings_table()
        self._refresh_select_options()
        self._refresh_all_tables()
        self._load_initial_forms()
        self._load_settings_form()
        self._refresh_settings_table()
        self._apply_theme()
        self._refresh_summary()
        self._refresh_help()
        self.call_after_refresh(self._focus_main_menu)
        self._set_status("界面已就绪。")

    def action_new_item(self) -> None:
        tab = self._active_tab()
        if tab == "profiles":
            self._new_profile_draft()
        elif tab == "providers":
            self._new_provider_draft()
        elif tab == "models":
            self._new_model_draft()

    def action_save_item(self) -> None:
        tab = self._active_tab()
        if tab == "profiles":
            self._save_profile_form()
        elif tab == "providers":
            self._save_provider_form()
        elif tab == "models":
            self._save_model_form()
        elif tab == "settings":
            self._save_settings_form()

    def action_delete_item(self) -> None:
        tab = self._active_tab()
        if tab == "profiles":
            self._delete_selected_profile()
        elif tab == "providers":
            self._delete_selected_provider()
        elif tab == "models":
            self._delete_selected_model()

    def action_clone_profile(self) -> None:
        if self._active_tab() != "profiles":
            self._set_status("克隆操作只适用于配置Profile页。", error=True)
            return
        self._clone_profile_draft()

    def action_activate_profile(self) -> None:
        if self._active_tab() != "profiles":
            self._set_status("启用操作只适用于配置Profile页。", error=True)
            return
        self._activate_selected_profile()

    def action_preview_current(self) -> None:
        self._open_preview()

    def action_show_about(self) -> None:
        self.push_screen(AboutDialog())

    def action_switch_to_profiles(self) -> None:
        self._switch_main_tab("profiles")

    def action_switch_to_providers(self) -> None:
        self._switch_main_tab("providers")

    def action_switch_to_models(self) -> None:
        self._switch_main_tab("models")

    def action_switch_to_preview_tab(self) -> None:
        self._switch_main_tab("preview")

    def action_switch_to_settings(self) -> None:
        self._switch_main_tab("settings")

    def action_switch_to_help(self) -> None:
        self._switch_main_tab("help")

    def action_focus_profile_summary(self) -> None:
        self._focus_summary_card("profiles")

    def action_focus_model_summary(self) -> None:
        self._focus_summary_card("models")

    def action_focus_inventory_summary(self) -> None:
        self._focus_summary_card("providers")

    def action_previous_summary_item(self) -> None:
        if self._is_summary_widget(self.focused):
            self.focus_previous_summary_item()

    def action_next_summary_item(self) -> None:
        if self._is_summary_widget(self.focused):
            self.focus_next_summary_item()

    def action_focus_summary_from_menu(self) -> None:
        if self.focused is not self._main_tabs_widget():
            self.action_cursor_up()
            return
        target_tab = self._active_tab()
        if target_tab == "models":
            self._focus_summary_card("models")
        elif target_tab == "providers":
            self._focus_summary_card("providers")
        else:
            self._focus_summary_card("profiles")

    def action_activate_context(self) -> None:
        focused = self.focused
        if focused is self._main_tabs_widget():
            if self._active_tab() == "preview":
                self._focus_preview_tabs()
                return
            self._focus_current_list()
            return
        if isinstance(focused, SummaryCard):
            self._activate_summary_card(focused)
            return
        if focused is self._preview_tabs_widget():
            self._focus_preview_panel()
            return
        if isinstance(focused, DataTable):
            self._focus_current_editor()
            return
        if isinstance(focused, Input):
            focused_id = focused.id or ""
            if focused_id in {"profiles-filter", "providers-filter", "models-filter"}:
                self._focus_current_list()

    def action_next_menu(self) -> None:
        tabs = self._main_tabs_widget()
        if self.focused is tabs:
            tabs.action_next_tab()
            return
        preview_tabs = self._preview_tabs_widget_optional()
        if preview_tabs is not None and self.focused is preview_tabs:
            preview_tabs.action_next_tab()
            return
        self.action_focus_next()

    def action_previous_menu(self) -> None:
        tabs = self._main_tabs_widget()
        focused = self.focused
        if focused is tabs:
            self.action_focus_previous()
            return
        preview_tabs = self._preview_tabs_widget_optional()
        if preview_tabs is not None and focused is preview_tabs:
            self._focus_main_menu()
            return
        if focused is self._current_list_widget() or self._is_filter_widget(focused):
            self._focus_main_menu()
            return
        if self._is_editor_widget(focused):
            self._focus_main_menu()
            self._set_status(f"已从{self._tab_label(self._active_tab())}编辑区返回顶部菜单。")
            return
        self.action_focus_previous()

    def action_focus_filter(self) -> None:
        target_tab = self._preview_source_tab()
        if target_tab not in {"profiles", "providers", "models"}:
            self._set_status("当前页没有可用搜索框。", error=True)
            return
        if self._active_tab() != target_tab:
            self.query_one("#tabs", TabbedContent).active = target_tab
            self.call_after_refresh(lambda: self._focus_filter(target_tab))
            return
        self._focus_filter(target_tab)

    def action_clear_filter(self) -> None:
        filter_widget = self._current_filter_widget()
        if filter_widget is not None and filter_widget.has_focus and filter_widget.value:
            filter_widget.value = ""
            self.set_focus(filter_widget)
            filter_widget.cursor_position = 0
            self._set_status(f"已清空{self._tab_label(self._filter_tab_id(filter_widget.id or ''))}搜索。")
            return
        if filter_widget is not None and filter_widget.has_focus:
            self._focus_main_menu()
            self._set_status(f"已从{self._tab_label(self._active_tab())}列表返回顶部菜单。")
            return
        if self.focused is self._current_list_widget():
            self._focus_main_menu()
            self._set_status(f"已从{self._tab_label(self._active_tab())}列表返回顶部菜单。")
            return
        preview_tabs = self._preview_tabs_widget_optional()
        if preview_tabs is not None and self.focused is preview_tabs:
            self._focus_main_menu()
            self._set_status("已从预览下层标签返回顶部菜单。")
            return
        if self._is_editor_widget(self.focused):
            self._focus_main_menu()
            self._set_status(f"已从{self._tab_label(self._active_tab())}编辑区返回顶部菜单。")
            return
        if self._is_preview_panel_widget(self.focused):
            self._focus_main_menu()
            self._set_status("已从预览内容返回顶部菜单。")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "about-open": self.action_show_about,
            "profile-new": self._new_profile_draft,
            "profile-preview": self._open_preview,
            "profile-save": self._save_profile_form,
            "profile-clone": self._clone_profile_draft,
            "profile-activate": self._activate_selected_profile,
            "profile-delete": self._delete_selected_profile,
            "provider-new": self._new_provider_draft,
            "provider-preview": self._open_preview,
            "provider-save": self._save_provider_form,
            "provider-delete": self._delete_selected_provider,
            "model-new": self._new_model_draft,
            "model-preview": self._open_preview,
            "model-save": self._save_model_form,
            "model-delete": self._delete_selected_model,
            "settings-reset": self._reset_settings_form,
            "settings-reload": self._reload_state_from_settings,
            "settings-save": self._save_settings_form,
        }
        action = actions.get(event.button.id or "")
        if action is not None:
            action()

    def on_input_changed(self, event: Input.Changed) -> None:
        widget_id = event.input.id or ""
        if widget_id == "profiles-filter":
            self._refresh_profiles_table(self.selected_profile_name or self.state.active_profile)
        elif widget_id == "providers-filter":
            self._refresh_providers_table(self.selected_provider_name)
        elif widget_id == "models-filter":
            self._refresh_models_table(self.selected_model_name)
        elif widget_id == "settings-config-path":
            self._sync_profiles_path_input()
            self._refresh_settings_table()
            self._refresh_settings_description()
        elif widget_id == "settings-profiles-path":
            self._refresh_settings_table()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        table_id = event.data_table.id or ""
        name = event.row_key.value or ""
        if table_id == "profiles-table" and self.query_one_optional("#profile-name", Input):
            self._load_profile_form(name)
        elif table_id == "providers-table" and self.query_one_optional(
            "#provider-name", Input
        ):
            self._load_provider_form(name)
        elif table_id == "models-table" and self.query_one_optional("#model-name", Input):
            self._load_model_form(name)
        elif table_id == "settings-table":
            self.selected_settings_key = name

    def on_data_table_row_selected(self, _: DataTable.RowSelected) -> None:
        self._focus_current_editor()

    def on_summary_card_selected(self, event: SummaryCard.Selected) -> None:
        self._activate_summary_card(event.card)

    def on_tabbed_content_tab_activated(self, _: TabbedContent.TabActivated) -> None:
        active = self._active_tab()
        if active not in {"preview", "help"}:
            self.last_editor_tab = active
        self.call_after_refresh(self._sync_visible_form)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if (event.checkbox.id or "") == "settings-follow-profiles":
            self._sync_profiles_path_input()
            self._refresh_settings_table()
            self._refresh_settings_description()

    def on_select_changed(self, event: Select.Changed) -> None:
        widget_id = event.select.id or ""
        if widget_id == "settings-theme":
            self._refresh_settings_description()
            self._refresh_settings_table()
        elif widget_id == "settings-shortcut-scheme":
            self._refresh_settings_description()
            self._refresh_settings_table()

    def on_key(self, event) -> None:
        if getattr(event, "key", "") == "down" and self._is_summary_widget(self.focused):
            event.stop()
            self.focus_main_menu_from_summary()
            return

        if getattr(event, "key", "") in {"left", "right"} and self._is_summary_widget(
            self.focused
        ):
            event.stop()
            if getattr(event, "key", "") == "left":
                self.focus_previous_summary_item()
            else:
                self.focus_next_summary_item()
            return

        if getattr(event, "key", "") == "up" and self.focused is self._main_tabs_widget():
            event.stop()
            self.action_focus_summary_from_menu()
            return

        scheme = SHORTCUT_SCHEMES.get(
            self.panel_settings.shortcut_scheme,
            SHORTCUT_SCHEMES[DEFAULT_SHORTCUT_SCHEME],
        )
        action_name = dict(scheme.get("aliases", {})).get(getattr(event, "key", ""))
        if not action_name:
            return
        event.stop()
        self.run_action(action_name)

    def _configure_tables(self) -> None:
        profiles_table = self.query_one("#profiles-table", DataTable)
        profiles_table.cursor_type = "row"
        profiles_table.zebra_stripes = True
        profiles_table.add_columns("名称", "标签", "默认模型", "当前生效")

        providers_table = self.query_one("#providers-table", DataTable)
        providers_table.cursor_type = "row"
        providers_table.zebra_stripes = True
        providers_table.add_columns("名称", "类型", "基础地址")

        models_table = self.query_one("#models-table", DataTable)
        models_table.cursor_type = "row"
        models_table.zebra_stripes = True
        models_table.add_columns("名称", "提供方", "远端模型", "上下文")

    def _configure_settings_table(self) -> None:
        settings_table = self.query_one("#settings-table", DataTable)
        settings_table.cursor_type = "row"
        settings_table.zebra_stripes = True
        settings_table.add_columns("项目", "当前值", "默认值")

    def _refresh_all_tables(self) -> None:
        self._refresh_profiles_table(self.selected_profile_name or self.state.active_profile)
        self._refresh_providers_table(self.selected_provider_name)
        self._refresh_models_table(
            self.selected_model_name or str(self.state.main_config.get("default_model", ""))
        )

    def _refresh_profiles_table(self, select_name: Optional[str] = None) -> None:
        table = self.query_one("#profiles-table", DataTable)
        table.clear(columns=False)
        query = self.query_one("#profiles-filter", Input).value.strip().lower()
        names: list[str] = []
        for name, profile in self.state.profiles.items():
            if not self._matches_query(query, name, profile.label, profile.default_model):
                continue
            names.append(name)
            table.add_row(
                self._highlight_match(name, query),
                self._highlight_match(profile.label, query),
                self._highlight_match(profile.default_model, query),
                self._highlight_match("是" if name == self.state.active_profile else "", query),
                key=name,
            )
        self._move_cursor_to_name(table, names, select_name or self.state.active_profile)

    def _refresh_providers_table(self, select_name: Optional[str] = None) -> None:
        table = self.query_one("#providers-table", DataTable)
        table.clear(columns=False)
        query = self.query_one("#providers-filter", Input).value.strip().lower()
        names: list[str] = []
        for name, provider in self.state.main_config["providers"].items():
            if not self._matches_query(
                query,
                name,
                str(provider.get("type", "")),
                str(provider.get("base_url", "")),
            ):
                continue
            names.append(name)
            table.add_row(
                self._highlight_match(name, query),
                self._highlight_match(str(provider.get("type", "")), query),
                self._highlight_match(str(provider.get("base_url", "")), query),
                key=name,
            )
        self._move_cursor_to_name(table, names, select_name)

    def _refresh_models_table(self, select_name: Optional[str] = None) -> None:
        table = self.query_one("#models-table", DataTable)
        table.clear(columns=False)
        query = self.query_one("#models-filter", Input).value.strip().lower()
        names: list[str] = []
        for name, model in self.state.main_config["models"].items():
            if not self._matches_query(
                query,
                name,
                str(model.get("provider", "")),
                str(model.get("model", "")),
                ", ".join(model.get("capabilities", [])),
            ):
                continue
            names.append(name)
            table.add_row(
                self._highlight_match(name, query),
                self._highlight_match(str(model.get("provider", "")), query),
                self._highlight_match(str(model.get("model", "")), query),
                self._highlight_match(str(model.get("max_context_size", "")), query),
                key=name,
            )
        self._move_cursor_to_name(table, names, select_name)

    def _refresh_settings_table(self) -> None:
        table = self.query_one_optional("#settings-table", DataTable)
        if table is None:
            return
        table.clear(columns=False)
        current = self._panel_settings_from_form()
        default = default_panel_settings(settings_path=self.panel_settings.settings_path)
        rows = [
            (
                "config_path",
                "Kimi 主配置文件",
                str(current.resolved_config_path()),
                str(default.resolved_config_path()),
            ),
            (
                "profiles_path",
                "配置Profile sidecar",
                "跟随主配置目录"
                if current.follow_config_profiles
                else str(current.resolved_profiles_path()),
                str(default.resolved_profiles_path()),
            ),
            (
                "theme",
                "TUI 主题",
                THEME_LABELS.get(current.theme, current.theme),
                THEME_LABELS.get(default.theme, default.theme),
            ),
            (
                "shortcut_scheme",
                "快捷键方案",
                str(SHORTCUT_SCHEMES.get(current.shortcut_scheme, {}).get("label", current.shortcut_scheme)),
                str(
                    SHORTCUT_SCHEMES.get(
                        default.shortcut_scheme,
                        {},
                    ).get("label", default.shortcut_scheme)
                ),
            ),
        ]
        keys = [key for key, _, _, _ in rows]
        for key, title, value, default_value in rows:
            table.add_row(title, value, default_value, key=key)
        self._move_cursor_to_name(table, keys, self.selected_settings_key)

    def _refresh_select_options(self) -> None:
        model_select = self.query_one("#profile-model", Select)
        model_options = [(name, name) for name in self.state.main_config["models"].keys()]
        model_select.set_options(model_options)
        model_select.disabled = not model_options

        provider_select = self.query_one("#model-provider", Select)
        provider_options = [
            (name, name) for name in self.state.main_config["providers"].keys()
        ]
        provider_select.set_options(provider_options)
        provider_select.disabled = not provider_options
        self._refresh_dependency_controls()

    def _load_initial_forms(self) -> None:
        if self.state.profiles:
            self._load_profile_form(self.state.active_profile)
        else:
            self._new_profile_draft()

        providers = list(self.state.main_config["providers"].keys())
        if providers:
            self._load_provider_form(providers[0])
        else:
            self._new_provider_draft()

        default_model = str(self.state.main_config.get("default_model", ""))
        models = list(self.state.main_config["models"].keys())
        if default_model in self.state.main_config["models"]:
            self._load_model_form(default_model)
        elif models:
            self._load_model_form(models[0])
        else:
            self._new_model_draft()

    def _load_settings_form(self) -> None:
        config_input = self.query_one("#settings-config-path", Input)
        config_input.value = str(self.panel_settings.resolved_config_path())

        follow_checkbox = self.query_one("#settings-follow-profiles", Checkbox)
        follow_checkbox.value = self.panel_settings.follow_config_profiles

        profiles_input = self.query_one("#settings-profiles-path", Input)
        profiles_input.value = (
            ""
            if self.panel_settings.follow_config_profiles
            else str(self.panel_settings.resolved_profiles_path())
        )

        self._set_select_value_for_options(
            "#settings-theme",
            self.panel_settings.theme,
            [value for _, value in THEME_OPTIONS],
        )
        self._set_select_value_for_options(
            "#settings-shortcut-scheme",
            self.panel_settings.shortcut_scheme,
            list(SHORTCUT_SCHEMES.keys()),
        )
        self._sync_profiles_path_input()
        self._refresh_settings_description()

    def _sync_profiles_path_input(self) -> None:
        follow_checkbox = self.query_one_optional("#settings-follow-profiles", Checkbox)
        profiles_input = self.query_one_optional("#settings-profiles-path", Input)
        if follow_checkbox is None or profiles_input is None:
            return
        if follow_checkbox.value:
            config_path = self._input_path("#settings-config-path", DEFAULT_CONFIG_PATH)
            profiles_input.value = str(config_path.with_name(PROFILE_FILENAME))
            profiles_input.disabled = True
        else:
            profiles_input.disabled = False

    def _refresh_settings_description(self) -> None:
        description = self.query_one_optional("#settings-description", Static)
        shortcuts = self.query_one_optional("#settings-shortcuts-summary", Static)
        defaults = self.query_one_optional("#settings-defaults", Static)
        if description is None or shortcuts is None or defaults is None:
            return
        theme = self._select_value("#settings-theme") or DEFAULT_THEME
        shortcut_scheme = self._select_value("#settings-shortcut-scheme") or DEFAULT_SHORTCUT_SCHEME
        theme_text = {
            "ocean": "深海蓝：当前主视觉，偏冷色、信息密度高。",
            "graphite": "石墨灰：更克制、更偏工程控制台。",
            "ember": "琥珀终端：暖色高对比，更接近经典 console panel。",
        }.get(theme, theme)
        shortcut_info = SHORTCUT_SCHEMES.get(
            shortcut_scheme,
            SHORTCUT_SCHEMES[DEFAULT_SHORTCUT_SCHEME],
        )
        description.update(
            "\n".join(
                [
                    "当前设置说明",
                    f"主题：{theme_text}",
                    f"快捷键：{shortcut_info['description']}",
                    f"面板设置文件：{self.panel_settings.settings_path}",
                ]
            )
        )
        shortcuts.update(
            "\n".join(
                [
                    "当前快捷键摘要",
                    *[f"  {line}" for line in shortcut_info["lines"]],
                ]
            )
        )
        default = default_panel_settings(settings_path=self.panel_settings.settings_path)
        defaults.update(
            "\n".join(
                [
                    "默认值",
                    f"  主配置：{default.resolved_config_path()}",
                    f"  配置Profile：{default.resolved_profiles_path()}",
                    f"  主题：{THEME_LABELS.get(default.theme, default.theme)}",
                    "  快捷键：标准方案（Ctrl+1..6 / F6 / F7~F10）",
                ]
            )
        )

    def _load_profile_form(self, name: str) -> None:
        profile = self.state.profiles[name]
        self.selected_profile_name = name
        self._set_profile_form(profile, editable_name=True)

    def _load_provider_form(self, name: str) -> None:
        provider = self.state.main_config["providers"][name]
        self.selected_provider_name = name
        self.provider_name_locked = True
        self._set_provider_form(
            name=name,
            provider_type=str(provider.get("type", "")),
            base_url=str(provider.get("base_url", "")),
            api_key=str(provider.get("api_key", "")),
            lock_name=True,
        )

    def _load_model_form(self, name: str) -> None:
        model = self.state.main_config["models"][name]
        self.selected_model_name = name
        self.model_name_locked = True
        self._set_model_form(
            name=name,
            provider=str(model.get("provider", "")),
            remote_model=str(model.get("model", "")),
            max_context_size=str(model.get("max_context_size", 262144)),
            capabilities=", ".join(model.get("capabilities", [])),
            lock_name=True,
        )

    def _new_profile_draft(self) -> None:
        self.selected_profile_name = None
        default_model = self._first_model_name()
        self._set_profile_form(
            Profile(
                name="",
                label="",
                default_model=default_model,
                default_thinking=True,
                default_yolo=False,
                default_plan_mode=False,
                default_editor="",
                theme="dark",
                show_thinking_stream=False,
                merge_all_available_skills=False,
            ),
            editable_name=True,
        )
        self.query_one("#profile-name", Input).focus()
        dependency_message = self._profile_dependency_message()
        if dependency_message:
            self._set_status(dependency_message, error=True)
            return
        self._set_status("已创建新的配置Profile草稿。")

    def _clone_profile_draft(self) -> None:
        dependency_message = self._profile_dependency_message()
        if dependency_message:
            self._set_status(dependency_message, error=True)
            return
        source = self._profile_from_form()
        source_name = self.query_one("#profile-name", Input).value.strip() or "profile"
        source.label = self.query_one("#profile-label", Input).value.strip() or "配置Profile"
        source.name = self._unique_profile_name(source_name)
        source.label = f"{source.label} 副本"
        self.selected_profile_name = None
        self._set_profile_form(source, editable_name=True)
        self.query_one("#profile-name", Input).focus()
        self._set_status("已克隆当前配置Profile，请保存为新配置。")

    def _new_provider_draft(self) -> None:
        self.selected_provider_name = None
        self.provider_name_locked = False
        self._set_provider_form(
            name="",
            provider_type="kimi",
            base_url="",
            api_key="",
            lock_name=False,
        )
        self.query_one("#provider-name", Input).focus()
        self._set_status("已创建新的提供方草稿。")

    def _new_model_draft(self) -> None:
        self.selected_model_name = None
        self.model_name_locked = False
        self._set_model_form(
            name="",
            provider=self._first_provider_name(),
            remote_model="",
            max_context_size="262144",
            capabilities="",
            lock_name=False,
        )
        self.query_one("#model-provider", Select).focus()
        dependency_message = self._model_dependency_message()
        if dependency_message:
            self._set_status(dependency_message, error=True)
            return
        self._set_status("已创建新的模型草稿。")

    def _save_profile_form(self) -> None:
        dependency_message = self._profile_dependency_message()
        if dependency_message:
            self._set_status(dependency_message, error=True)
            return
        data = self._profile_payload_from_form()
        if not data["name"]:
            self._set_status("配置Profile名称不能为空。", error=True)
            return
        if not data["default_model"]:
            self._set_status("请先选择默认模型。", error=True)
            return

        candidate = clone_state(self.state)
        try:
            upsert_profile(candidate, **data)
            if candidate.active_profile == data["name"]:
                apply_profile(candidate, data["name"])
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        if not self._save_state_or_report(candidate):
            return
        self.state = candidate
        self.selected_profile_name = data["name"]
        self._refresh_profiles_table(data["name"])
        self._load_profile_form(data["name"])
        self._refresh_summary()
        self._set_status(f"配置Profile已保存：{data['name']}")

    def _save_provider_form(self) -> None:
        name = self.query_one("#provider-name", Input).value.strip()
        provider_type = self.query_one("#provider-type", Input).value.strip()
        base_url = self.query_one("#provider-base-url", Input).value.strip()
        api_key = self.query_one("#provider-api-key", Input).value.strip()

        if not name:
            self._set_status("提供方名称不能为空。", error=True)
            return
        if self.provider_name_locked and self.selected_provider_name != name:
            self._set_status("当前不支持重命名提供方，请新建一个。", error=True)
            return

        candidate = clone_state(self.state)
        upsert_provider(
            candidate,
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key=api_key,
        )
        if not self._save_state_or_report(candidate):
            return
        self.state = candidate
        self.selected_provider_name = name
        self.provider_name_locked = True
        self._refresh_select_options()
        self._refresh_providers_table(name)
        self._refresh_models_table(self.selected_model_name)
        self._load_provider_form(name)
        self._refresh_summary()
        self._set_status(f"提供方已保存：{name}")

    def _save_model_form(self) -> None:
        dependency_message = self._model_dependency_message()
        if dependency_message:
            self._set_status(dependency_message, error=True)
            return
        provider = self._select_value("#model-provider")
        name = self._model_key_from_form(provider=provider)
        remote_model = self.query_one("#model-remote-name", Input).value.strip()
        max_context_size_raw = self.query_one("#model-context-size", Input).value.strip()
        capabilities_raw = self.query_one("#model-capabilities", Input).value.strip()

        if not name:
            self._set_status("模型名称不能为空。", error=True)
            return
        if self.model_name_locked and self.selected_model_name != name:
            self._set_status("当前不支持重命名模型，请新建一个。", error=True)
            return
        if not provider:
            self._set_status("请先选择提供方。", error=True)
            return

        try:
            max_context_size = int(max_context_size_raw)
        except ValueError:
            self._set_status("最大上下文必须是整数。", error=True)
            return

        capabilities = [item.strip() for item in capabilities_raw.split(",") if item.strip()]
        candidate = clone_state(self.state)
        try:
            upsert_model(
                candidate,
                name=name,
                provider=provider,
                model=remote_model,
                max_context_size=max_context_size,
                capabilities=capabilities,
            )
            self._sync_active_profile_for_model_change(candidate, name)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        if not self._save_state_or_report(candidate):
            return
        self.state = candidate
        self.selected_model_name = name
        self.model_name_locked = True
        self._refresh_select_options()
        self._refresh_models_table(name)
        self._refresh_profiles_table(self.selected_profile_name)
        self._load_model_form(name)
        self._refresh_summary()
        self._set_status(f"模型已保存：{name}")

    def _delete_selected_profile(self) -> None:
        if not self.selected_profile_name:
            self._set_status("请先选择要删除的配置Profile。", error=True)
            return
        candidate = clone_state(self.state)
        try:
            delete_profile(candidate, self.selected_profile_name)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        if not self._save_state_or_report(candidate):
            return
        self.state = candidate
        self.selected_profile_name = None
        self._refresh_profiles_table(self.state.active_profile)
        if self.state.active_profile in self.state.profiles:
            self._load_profile_form(self.state.active_profile)
        self._refresh_summary()
        self._set_status("配置Profile已删除。")

    def _delete_selected_provider(self) -> None:
        if not self.selected_provider_name:
            self._set_status("请先选择要删除的提供方。", error=True)
            return
        candidate = clone_state(self.state)
        try:
            delete_provider(candidate, self.selected_provider_name)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        if not self._save_state_or_report(candidate):
            return
        self.state = candidate
        self.selected_provider_name = None
        self.provider_name_locked = False
        self._refresh_select_options()
        self._refresh_providers_table(None)
        providers = list(self.state.main_config["providers"].keys())
        if providers:
            self._load_provider_form(providers[0])
        else:
            self._new_provider_draft()
        self._refresh_summary()
        self._set_status("提供方已删除。")

    def _delete_selected_model(self) -> None:
        if not self.selected_model_name:
            self._set_status("请先选择要删除的模型。", error=True)
            return
        candidate = clone_state(self.state)
        try:
            delete_model(candidate, self.selected_model_name)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        if not self._save_state_or_report(candidate):
            return
        self.state = candidate
        self.selected_model_name = None
        self.model_name_locked = False
        self._refresh_select_options()
        self._refresh_models_table(None)
        models = list(self.state.main_config["models"].keys())
        if models:
            self._load_model_form(models[0])
        else:
            self._new_model_draft()
        self._refresh_summary()
        self._set_status("模型已删除。")

    def _activate_selected_profile(self) -> None:
        dependency_message = self._profile_dependency_message()
        if dependency_message:
            self._set_status(dependency_message, error=True)
            return
        name = self.query_one("#profile-name", Input).value.strip() or self.selected_profile_name
        if not name:
            self._set_status("请先选择或保存配置Profile。", error=True)
            return
        if name not in self.state.profiles:
            self._set_status("请先保存配置Profile，再执行启用。", error=True)
            return
        candidate = clone_state(self.state)
        try:
            apply_profile(candidate, name)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        if not self._save_state_or_report(candidate):
            return
        self.state = candidate
        self.selected_profile_name = name
        self._refresh_profiles_table(name)
        self._refresh_summary()
        self._set_status(f"当前生效配置Profile：{name}")

    def _set_profile_form(self, profile: Profile, *, editable_name: bool) -> None:
        self.query_one("#profile-name", Input).value = profile.name
        self.query_one("#profile-name", Input).disabled = not editable_name
        self.query_one("#profile-label", Input).value = profile.label
        self._set_select_value("#profile-model", profile.default_model)
        self.query_one("#profile-editor", Input).value = profile.default_editor
        self.query_one("#profile-theme", Input).value = profile.theme
        self.query_one("#profile-thinking", Checkbox).value = profile.default_thinking
        self.query_one("#profile-yolo", Checkbox).value = profile.default_yolo
        self.query_one("#profile-plan-mode", Checkbox).value = profile.default_plan_mode
        self.query_one("#profile-show-thinking", Checkbox).value = (
            profile.show_thinking_stream
        )
        self.query_one("#profile-merge-skills", Checkbox).value = (
            profile.merge_all_available_skills
        )

    def _set_provider_form(
        self,
        *,
        name: str,
        provider_type: str,
        base_url: str,
        api_key: str,
        lock_name: bool,
    ) -> None:
        name_input = self.query_one("#provider-name", Input)
        name_input.value = name
        name_input.disabled = lock_name
        self.query_one("#provider-type", Input).value = provider_type
        self.query_one("#provider-base-url", Input).value = base_url
        self.query_one("#provider-api-key", Input).value = api_key

    def _set_model_form(
        self,
        *,
        name: str,
        provider: str,
        remote_model: str,
        max_context_size: str,
        capabilities: str,
        lock_name: bool,
    ) -> None:
        name_input = self.query_one("#model-name", Input)
        name_input.value = self._model_name_suffix(name, provider)
        name_input.disabled = lock_name
        self._set_select_value("#model-provider", provider)
        self.query_one("#model-remote-name", Input).value = remote_model
        self.query_one("#model-context-size", Input).value = max_context_size
        self.query_one("#model-capabilities", Input).value = capabilities

    def _set_settings_form(self, settings: PanelSettings) -> None:
        self.panel_settings = settings
        self._load_settings_form()
        self._refresh_settings_table()

    def _profile_payload_from_form(self) -> dict[str, object]:
        return {
            "name": self.query_one("#profile-name", Input).value.strip(),
            "label": self.query_one("#profile-label", Input).value.strip(),
            "default_model": self._select_value("#profile-model"),
            "default_thinking": self.query_one("#profile-thinking", Checkbox).value,
            "default_yolo": self.query_one("#profile-yolo", Checkbox).value,
            "default_plan_mode": self.query_one("#profile-plan-mode", Checkbox).value,
            "default_editor": self.query_one("#profile-editor", Input).value.strip(),
            "theme": self.query_one("#profile-theme", Input).value.strip() or "dark",
            "show_thinking_stream": self.query_one(
                "#profile-show-thinking", Checkbox
            ).value,
            "merge_all_available_skills": self.query_one(
                "#profile-merge-skills", Checkbox
            ).value,
        }

    def _panel_settings_from_form(self) -> PanelSettings:
        config_path = self._input_path("#settings-config-path", DEFAULT_CONFIG_PATH)
        follow_profiles = self.query_one("#settings-follow-profiles", Checkbox).value
        profiles_default = config_path.with_name(PROFILE_FILENAME)
        profiles_path = (
            None
            if follow_profiles
            else self._input_path("#settings-profiles-path", profiles_default)
        )
        theme = self._select_value("#settings-theme") or DEFAULT_THEME
        shortcut_scheme = (
            self._select_value("#settings-shortcut-scheme") or DEFAULT_SHORTCUT_SCHEME
        )
        return PanelSettings(
            settings_path=self.panel_settings.settings_path,
            config_path=config_path,
            profiles_path=profiles_path,
            follow_config_profiles=follow_profiles,
            theme=theme,
            shortcut_scheme=shortcut_scheme,
        )

    def _save_settings_form(self) -> None:
        candidate = self._panel_settings_from_form()
        try:
            state = load_state(
                candidate.resolved_config_path(),
                candidate.explicit_profiles_path(),
            )
        except Exception as exc:
            self._set_status(f"设置保存失败：{exc}", error=True)
            return

        self._apply_panel_settings(candidate, state)
        self._set_status("面板设置已保存并生效。")

    def _reset_settings_form(self) -> None:
        defaults = default_panel_settings(settings_path=self.panel_settings.settings_path)
        self._set_settings_form(defaults)
        self._set_status("已恢复设置表单默认值，保存后生效。")

    def _reload_state_from_settings(self) -> None:
        candidate = self._panel_settings_from_form()
        try:
            state = load_state(
                candidate.resolved_config_path(),
                candidate.explicit_profiles_path(),
            )
        except Exception as exc:
            self._set_status(f"重新载入失败：{exc}", error=True)
            return

        self._apply_panel_settings(candidate, state, persist=False)
        self._set_status("已根据当前设置重新载入配置。")

    def _apply_panel_settings(
        self,
        settings: PanelSettings,
        state: AppState,
        *,
        persist: bool = True,
    ) -> None:
        if persist:
            save_panel_settings(settings)
        self.panel_settings = settings
        self.state = state
        self.selected_profile_name = None
        self.selected_provider_name = None
        self.selected_model_name = None
        self.provider_name_locked = False
        self.model_name_locked = False
        self._refresh_select_options()
        self._refresh_all_tables()
        self._load_initial_forms()
        self._load_settings_form()
        self._refresh_settings_table()
        self._apply_theme()
        self._refresh_summary()
        self._refresh_help()

    def _apply_theme(self) -> None:
        screen = self.screen
        for theme_name in ("graphite", "ember"):
            screen.remove_class(f"-theme-{theme_name}")
        if self.panel_settings.theme in {"graphite", "ember"}:
            screen.add_class(f"-theme-{self.panel_settings.theme}")

    def _profile_from_form(self) -> Profile:
        payload = self._profile_payload_from_form()
        return Profile(**payload)

    def _set_select_value(self, selector: str, value: str) -> None:
        select = self.query_one(selector, Select)
        if select.disabled:
            return
        if selector == "#profile-model":
            options = list(self.state.main_config["models"].keys())
        elif selector == "#model-provider":
            options = list(self.state.main_config["providers"].keys())
        else:
            options = []
        if value in options:
            select.value = value
        elif options:
            select.value = options[0]

    def _set_select_value_for_options(
        self,
        selector: str,
        value: str,
        options: list[str],
    ) -> None:
        select = self.query_one(selector, Select)
        if select.disabled:
            return
        if value in options:
            select.value = value
        elif options:
            select.value = options[0]

    def _select_value(self, selector: str) -> str:
        select = self.query_one(selector, Select)
        value = select.value
        if value in (None, Select.BLANK, Select.NULL):
            return ""
        return str(value)

    def _input_path(self, selector: str, default_path: Path) -> Path:
        raw = self.query_one(selector, Input).value.strip()
        if not raw:
            return default_path.expanduser()
        return Path(raw).expanduser()

    def _move_cursor_to_name(
        self, table: DataTable, names: list[str], target_name: Optional[str]
    ) -> None:
        if not names:
            return
        name = target_name if target_name in names else names[0]
        table.move_cursor(row=names.index(name), column=0, animate=False, scroll=True)

    def _unique_profile_name(self, base_name: str) -> str:
        candidate = f"{base_name}-copy"
        index = 2
        while candidate in self.state.profiles:
            candidate = f"{base_name}-copy-{index}"
            index += 1
        return candidate

    def _first_model_name(self) -> str:
        return next(iter(self.state.main_config["models"]), "")

    def _first_provider_name(self) -> str:
        return next(iter(self.state.main_config["providers"]), "")

    def _model_key_from_form(self, *, provider: str) -> str:
        if self.model_name_locked and self.selected_model_name:
            return self.selected_model_name
        suffix = self.query_one("#model-name", Input).value.strip()
        if provider and suffix.startswith(f"{provider}/"):
            suffix = suffix[len(provider) + 1 :]
        elif "/" in suffix:
            suffix = suffix.split("/", 1)[1]
        if not provider or not suffix:
            return suffix
        return f"{provider}/{suffix}"

    def _model_name_suffix(self, model_name: str, provider: str) -> str:
        if provider and model_name.startswith(f"{provider}/"):
            return model_name[len(provider) + 1 :]
        if "/" in model_name:
            return model_name.split("/", 1)[1]
        return model_name

    def _active_tab(self) -> str:
        return self.query_one("#tabs", TabbedContent).active

    def _main_tabs_widget(self) -> ContentTabs:
        return self.query_one("#tabs > ContentTabs", ContentTabs)

    def _preview_tabs_widget(self) -> ContentTabs:
        return self.query_one("#preview-tabs > ContentTabs", ContentTabs)

    def _preview_tabs_widget_optional(self) -> Optional[ContentTabs]:
        return self.query_one_optional("#preview-tabs > ContentTabs", ContentTabs)

    def _focus_main_menu(self) -> None:
        self.set_focus(self._main_tabs_widget())

    def focus_main_menu_from_summary(self) -> None:
        self._focus_main_menu()
        self._set_status("已从顶部摘要返回页签菜单。")

    def _switch_main_tab(self, tab_id: str) -> None:
        self.query_one("#tabs", TabbedContent).active = tab_id
        self._focus_main_menu()
        self._set_status(f"已切换到{self._tab_label(tab_id)}。")

    def _focus_summary_card(self, tab_id: str) -> None:
        selector = {
            "profiles": "#summary-profile",
            "models": "#summary-model",
            "providers": "#summary-inventory",
        }.get(tab_id)
        if not selector:
            return
        widget = self.query_one(selector, SummaryCard)
        self.set_focus(widget)
        self._set_status(f"已聚焦{self._tab_label(tab_id)}摘要卡，按回车进入列表。")

    def focus_previous_summary_item(self) -> None:
        self._focus_relative_summary_item(-1)

    def focus_next_summary_item(self) -> None:
        self._focus_relative_summary_item(1)

    def _focus_relative_summary_item(self, offset: int) -> None:
        items = self._summary_widgets()
        focused = self.focused
        if focused not in items:
            return
        next_index = (items.index(focused) + offset) % len(items)
        self.set_focus(items[next_index])

    def _summary_widgets(self) -> list[Widget]:
        return [
            self.query_one("#summary-profile", SummaryCard),
            self.query_one("#summary-inventory", SummaryCard),
            self.query_one("#summary-model", SummaryCard),
            self.query_one("#about-open", Button),
        ]

    def _is_summary_widget(self, widget: object) -> bool:
        return widget in self._summary_widgets()

    def _activate_summary_card(self, card: SummaryCard) -> None:
        self.query_one("#tabs", TabbedContent).active = card.target_tab
        self.call_after_refresh(self._focus_current_list)

    def _focus_current_list(self) -> None:
        table = self._current_list_widget()
        if table is None:
            return
        self.set_focus(table)
        self._set_status(f"已进入{self._tab_label(self._active_tab())}列表。")

    def _focus_current_editor(self) -> None:
        widget = self._editor_entry_widget(self._active_tab())
        if widget is None:
            return
        self.set_focus(widget)
        self._set_status(f"已进入{self._tab_label(self._active_tab())}编辑区。")

    def _focus_preview_tabs(self) -> None:
        preview_tabs = self._preview_tabs_widget_optional()
        if preview_tabs is None:
            return
        self.set_focus(preview_tabs)
        self._set_status("已进入预览下层标签。")

    def _focus_preview_panel(self) -> None:
        panel = self._current_preview_panel()
        if panel is None:
            return
        self.set_focus(panel)
        self._set_status("已进入预览内容区。")

    def _current_preview_panel(self) -> Optional[VerticalScroll]:
        preview_active = self.query_one("#preview-tabs", TabbedContent).active
        selector = {
            "preview-config": "#preview-config .preview-panel",
            "preview-config-diff": "#preview-config-diff .preview-panel",
            "preview-profiles": "#preview-profiles .preview-panel",
            "preview-profiles-diff": "#preview-profiles-diff .preview-panel",
            "preview-compact": "#preview-compact .preview-panel",
        }.get(preview_active)
        if not selector:
            return None
        return self.query_one(selector, VerticalScroll)

    def _current_list_widget(self) -> Optional[DataTable]:
        selector = {
            "profiles": "#profiles-table",
            "providers": "#providers-table",
            "models": "#models-table",
            "settings": "#settings-table",
        }.get(self._active_tab())
        if not selector:
            return None
        return self.query_one(selector, DataTable)

    def _editor_entry_widget(self, tab_id: str) -> Optional[Widget]:
        if tab_id == "settings":
            return self._settings_entry_widget()
        candidates = {
            "profiles": [
                "#profile-name",
                "#profile-label",
                "#profile-model",
                "#profile-editor",
                "#profile-theme",
            ],
            "providers": [
                "#provider-name",
                "#provider-type",
                "#provider-base-url",
                "#provider-api-key",
            ],
            "models": [
                "#model-provider",
                "#model-name",
                "#model-remote-name",
                "#model-context-size",
                "#model-capabilities",
            ],
        }.get(tab_id, [])
        for selector in candidates:
            widget = self.query_one(selector)
            if not getattr(widget, "disabled", False):
                return widget
        return None

    def _settings_entry_widget(self) -> Optional[Widget]:
        selected_key = self.selected_settings_key or "config_path"
        candidates = {
            "config_path": ["#settings-config-path"],
            "profiles_path": ["#settings-follow-profiles", "#settings-profiles-path"],
            "theme": ["#settings-theme"],
            "shortcut_scheme": ["#settings-shortcut-scheme"],
        }.get(selected_key, ["#settings-config-path"])
        for selector in candidates:
            widget = self.query_one(selector)
            if selector == "#settings-profiles-path" and getattr(widget, "disabled", False):
                continue
            return widget
        return self.query_one("#settings-config-path", Input)

    def _set_status(self, message: str, *, error: bool = False) -> None:
        widget = self.query_one("#status", Static)
        widget.update(message)
        widget.styles.color = "red" if error else "green"

    def _save_state_or_report(self, state: AppState) -> bool:
        try:
            save_state(state)
        except (OSError, TypeError, ValueError) as exc:
            self._set_status(f"保存失败：{exc}", error=True)
            return False
        return True

    def _profile_dependency_message(self) -> Optional[str]:
        if self.state.main_config["models"]:
            return None
        return "当前还没有模型，请先在“模型”页创建模型后再保存、预览或启用配置Profile。"

    def _model_dependency_message(self) -> Optional[str]:
        if self.state.main_config["providers"]:
            return None
        return "当前还没有提供方，请先在“提供方”页创建提供方后再保存或预览模型。"

    def _dependency_message_for_tab(self, tab_id: str) -> Optional[str]:
        if tab_id == "profiles":
            return self._profile_dependency_message()
        if tab_id == "models":
            return self._model_dependency_message()
        return None

    def _refresh_dependency_controls(self) -> None:
        profile_blocked = self._profile_dependency_message() is not None
        model_blocked = self._model_dependency_message() is not None

        for selector in ("#profile-preview", "#profile-save", "#profile-clone", "#profile-activate"):
            self.query_one(selector, Button).disabled = profile_blocked

        for selector in ("#model-preview", "#model-save"):
            self.query_one(selector, Button).disabled = model_blocked

    def _sync_active_profile_for_model_change(
        self,
        state: AppState,
        fallback_model_name: str,
    ) -> None:
        active_profile = state.profiles.get(state.active_profile)
        if active_profile is None:
            return
        if active_profile.default_model not in state.main_config["models"]:
            active_profile.default_model = fallback_model_name
        apply_profile(state, state.active_profile)

    def _help_text(self) -> str:
        shortcut_info = SHORTCUT_SCHEMES.get(
            self.panel_settings.shortcut_scheme,
            SHORTCUT_SCHEMES[DEFAULT_SHORTCUT_SCHEME],
        )
        return "\n".join(
            [
                f"主配置文件：{self.state.config_path}",
                f"配置Profile文件：{self.state.profiles_path}",
                f"面板设置文件：{self.panel_settings.settings_path}",
                f"TUI 主题：{THEME_LABELS.get(self.panel_settings.theme, self.panel_settings.theme)}",
                f"快捷键方案：{shortcut_info['label']}",
                "",
                "快捷键：",
                "  q         退出",
                "  Ctrl+1~6  切换配置Profile / 提供方 / 模型 / 预览 / 设置 / 帮助",
                "  F7~F9      聚焦上方摘要卡，回车进入对应列表",
                "  F10        打开关于信息",
                "  ↑         顶部页签聚焦时，进入对应的上方摘要卡",
                "  Tab       顶部菜单切换；预览下层标签内切换预览页签；其他场景切到下一项",
                "  Shift+Tab 列表/编辑区回顶部菜单，其他场景回上一项",
                "  Enter     菜单进入列表；预览页进入下层标签；列表进入右侧编辑区",
                "  Ctrl+N    当前页新建草稿",
                "  Ctrl+S    保存当前表单",
                "  Ctrl+D    删除当前选中项",
                "  Ctrl+C    克隆当前配置Profile",
                "  Ctrl+A    启用当前配置Profile",
                "  F6        查看预览与 diff",
                "  /, Ctrl+F 聚焦当前列表搜索框",
                "  Esc       列表/编辑/预览区回顶部菜单；搜索框有内容时先清空",
                "  顶部关于   查看作者信息、主页、博客、邮箱和当前版本",
                "",
                "当前快捷键方案补充：",
                *[f"  {line}" for line in shortcut_info["lines"]],
                "",
                "说明：",
                "  配置Profile用于维护多套默认组合，并将当前生效项写回 config.toml。",
                "  提供方和模型一旦创建后名称固定，如需改名请新建。",
                "  模型的提供方前缀通过下拉选择，名称输入框只填写后缀。",
                "  列表支持实时搜索过滤，预览页可先看生成结果再保存。",
                "  设置页可调整配置路径、主题风格和快捷键方案，并提供默认值参考。",
            ]
        )

    def _refresh_help(self) -> None:
        self.query_one("#help-body", Static).update(self._help_text())

    def _sync_visible_form(self) -> None:
        tab = self._active_tab()
        if tab == "profiles" and self.selected_profile_name:
            self._load_profile_form(self.selected_profile_name)
        elif tab == "providers" and self.selected_provider_name:
            self._load_provider_form(self.selected_provider_name)
        elif tab == "models" and self.selected_model_name:
            self._load_model_form(self.selected_model_name)
        elif tab == "settings":
            self._load_settings_form()
            self._refresh_settings_table()
        elif tab == "preview":
            self._render_preview()
        elif tab == "help":
            self._refresh_help()

    def _refresh_summary(self) -> None:
        active_profile = self.state.active_profile or "未设置"
        active_model = str(self.state.main_config.get("default_model", "")) or "未设置"
        active_model_config = self.state.main_config["models"].get(active_model, {})
        active_provider = str(active_model_config.get("provider", "")) or "未设置"

        self.query_one("#summary-profile", SummaryCard).update(
            f"当前配置Profile ({self.SUMMARY_SHORTCUTS['profiles']})\n"
            f"{active_profile}\n"
            f"回车进入列表 · 共 {len(self.state.profiles)} 个"
        )
        self.query_one("#summary-model", SummaryCard).update(
            f"当前生效模型 ({self.SUMMARY_SHORTCUTS['models']})\n"
            f"{active_model}\n"
            f"提供方：{active_provider} · 回车进入列表"
        )
        self.query_one("#summary-inventory", SummaryCard).update(
            f"提供方 ({self.SUMMARY_SHORTCUTS['providers']})\n"
            f"{len(self.state.main_config['providers'])} 个提供方\n"
            f"{len(self.state.main_config['models'])} 个模型 · 回车进入列表"
        )

    def _open_preview(self) -> None:
        dependency_message = self._dependency_message_for_tab(self._preview_source_tab())
        if dependency_message:
            self._set_status(dependency_message, error=True)
            return
        self.query_one("#tabs", TabbedContent).active = "preview"
        self.call_after_refresh(self._render_preview)

    def _render_preview(self) -> None:
        try:
            source_tab = self._preview_source_tab()
            draft_state = self._build_draft_state_for_preview(source_tab)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return

        current_config = self._read_file_text(self.state.config_path)
        current_profiles = self._read_file_text(self.state.profiles_path)
        next_config = build_config_document(draft_state)
        next_profiles = build_profiles_document(draft_state)
        config_diff = self._unified_diff(
            current_config,
            next_config,
            str(self.state.config_path),
            f"{self.state.config_path} (preview)",
        )
        profiles_diff = self._unified_diff(
            current_profiles,
            next_profiles,
            str(self.state.profiles_path),
            f"{self.state.profiles_path} (preview)",
        )

        self.preview_payload = {
            "source_tab": source_tab,
            "config_text": next_config,
            "config_diff": config_diff,
            "profiles_text": next_profiles,
            "profiles_diff": profiles_diff,
            "compact_text": self._build_compact_preview(config_diff, profiles_diff),
        }

        self.query_one("#preview-meta", Static).update(
            f"当前预览来源：{self._tab_label(source_tab)}。"
            "这里展示保存后将写入的文件内容。"
        )
        self.query_one("#preview-config-body", Static).update(
            Syntax(next_config, "toml", theme="github-dark", line_numbers=True)
        )
        self.query_one("#preview-config-diff-body", Static).update(
            Syntax(config_diff, "diff", theme="github-dark", line_numbers=False)
        )
        self.query_one("#preview-profiles-body", Static).update(
            Syntax(next_profiles, "toml", theme="github-dark", line_numbers=True)
        )
        self.query_one("#preview-profiles-diff-body", Static).update(
            Syntax(profiles_diff, "diff", theme="github-dark", line_numbers=False)
        )
        self.query_one("#preview-compact-body", Static).update(
            self.preview_payload["compact_text"]
        )
        self._set_status("预览已刷新。")

    def _build_draft_state_for_preview(self, source_tab: str) -> AppState:
        draft_state = clone_state(self.state)

        if source_tab == "profiles":
            payload = self._profile_payload_from_form()
            name = str(payload["name"]).strip()
            if not name:
                raise ValueError("预览前必须填写配置Profile名称。")
            if not payload["default_model"]:
                raise ValueError("预览前请先选择默认模型。")
            upsert_profile(draft_state, **payload)
            if draft_state.active_profile == name:
                apply_profile(draft_state, name)
            return draft_state

        if source_tab == "providers":
            name = self.query_one("#provider-name", Input).value.strip()
            if not name:
                raise ValueError("预览前必须填写提供方名称。")
            if self.provider_name_locked and self.selected_provider_name != name:
                raise ValueError("当前不支持重命名提供方，请新建一个。")
            upsert_provider(
                draft_state,
                name=name,
                provider_type=self.query_one("#provider-type", Input).value.strip(),
                base_url=self.query_one("#provider-base-url", Input).value.strip(),
                api_key=self.query_one("#provider-api-key", Input).value.strip(),
            )
            return draft_state

        if source_tab == "models":
            dependency_message = self._model_dependency_message()
            if dependency_message:
                raise ValueError(dependency_message)
            provider = self._select_value("#model-provider")
            name = self._model_key_from_form(provider=provider)
            if not name:
                raise ValueError("预览前必须填写模型名称。")
            if self.model_name_locked and self.selected_model_name != name:
                raise ValueError("当前不支持重命名模型，请新建一个。")
            if not provider:
                raise ValueError("预览前请先选择提供方。")
            max_context_size_raw = self.query_one("#model-context-size", Input).value.strip()
            try:
                max_context_size = int(max_context_size_raw)
            except ValueError as exc:
                raise ValueError("预览前请填写正确的最大上下文整数值。") from exc
            capabilities_raw = self.query_one("#model-capabilities", Input).value.strip()
            upsert_model(
                draft_state,
                name=name,
                provider=provider,
                model=self.query_one("#model-remote-name", Input).value.strip(),
                max_context_size=max_context_size,
                capabilities=[
                    item.strip() for item in capabilities_raw.split(",") if item.strip()
                ],
            )
            self._sync_active_profile_for_model_change(draft_state, name)
            return draft_state

        return draft_state

    def _preview_source_tab(self) -> str:
        active = self._active_tab()
        if active in {"preview", "help"}:
            if self.last_editor_tab in {"profiles", "providers", "models"}:
                return self.last_editor_tab
            return "profiles"
        return active

    def _read_file_text(self, path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _unified_diff(
        self, old_text: str, new_text: str, fromfile: str, tofile: str
    ) -> str:
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

    def _build_compact_preview(self, config_diff: str, profiles_diff: str) -> str:
        config_changes = self._extract_compact_diff_lines(config_diff)
        profile_changes = self._extract_compact_diff_lines(profiles_diff)
        sections = [
            "仅看变更",
            "",
            f"来源页签：{self._tab_label(self._preview_source_tab())}",
            "",
            "config.toml",
            *self._render_compact_sections(config_changes),
            "",
            "config.profiles.toml",
            *self._render_compact_sections(profile_changes),
        ]
        return "\n".join(sections)

    def _extract_compact_diff_lines(self, diff_text: str) -> dict[str, list[str]]:
        changes = {"added": [], "removed": [], "modified": []}
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

    def _matches_query(self, query: str, *parts: str) -> bool:
        if not query:
            return True
        haystack = " ".join(parts).lower()
        return query in haystack

    def _render_compact_sections(self, changes: dict[str, list[str]]) -> list[str]:
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

    def _highlight_match(self, value: str, query: str) -> Union[str, Text]:
        if not value or not query:
            return value
        lowered_value = value.lower()
        lowered_query = query.lower()
        text = Text(value)
        start = 0
        matched = False
        while True:
            index = lowered_value.find(lowered_query, start)
            if index < 0:
                break
            matched = True
            text.stylize("bold #08111c on #f59e0b", index, index + len(query))
            start = index + len(query)
        return text if matched else value

    def _focus_filter(self, tab_id: str) -> None:
        filter_id = {
            "profiles": "#profiles-filter",
            "providers": "#providers-filter",
            "models": "#models-filter",
        }.get(tab_id)
        if not filter_id:
            self._set_status("当前页没有可用搜索框。", error=True)
            return
        widget = self.query_one(filter_id, Input)
        widget.focus()
        widget.cursor_position = len(widget.value)
        self._set_status(f"已聚焦{self._tab_label(tab_id)}搜索框。")

    def _current_filter_widget(self) -> Optional[Input]:
        focused = self.focused
        if self._is_filter_widget(focused):
            if isinstance(focused, Input):
                return focused
            return None

        tab_id = self._preview_source_tab()
        filter_id = self._filter_id_for_tab(tab_id)
        if not filter_id:
            return None
        return self.query_one(filter_id, Input)

    def _filter_id_for_tab(self, tab_id: str) -> Optional[str]:
        return {
            "profiles": "#profiles-filter",
            "providers": "#providers-filter",
            "models": "#models-filter",
        }.get(tab_id)

    def _filter_tab_id(self, widget_id: str) -> str:
        return {
            "profiles-filter": "profiles",
            "providers-filter": "providers",
            "models-filter": "models",
        }.get(widget_id, self._preview_source_tab())

    def _is_filter_widget(self, widget: object) -> bool:
        return isinstance(widget, Input) and (widget.id or "") in {
            "profiles-filter",
            "providers-filter",
            "models-filter",
        }

    def _is_editor_widget(self, widget: object) -> bool:
        if self._active_tab() not in {"profiles", "providers", "models", "settings"}:
            return False
        if widget is None:
            return False
        if self._is_filter_widget(widget):
            return False
        widget_id = getattr(widget, "id", "") or ""
        if widget_id in {
            "profile-name",
            "profile-label",
            "profile-model",
            "profile-editor",
            "profile-theme",
            "profile-thinking",
            "profile-yolo",
            "profile-plan-mode",
            "profile-show-thinking",
            "profile-merge-skills",
            "profile-new",
            "profile-preview",
            "profile-save",
            "profile-clone",
            "profile-activate",
            "profile-delete",
            "provider-name",
            "provider-type",
            "provider-base-url",
            "provider-api-key",
            "provider-new",
            "provider-preview",
            "provider-save",
            "provider-delete",
            "model-name",
            "model-provider",
            "model-remote-name",
            "model-context-size",
            "model-capabilities",
            "model-new",
            "model-preview",
            "model-save",
            "model-delete",
            "settings-config-path",
            "settings-follow-profiles",
            "settings-profiles-path",
            "settings-theme",
            "settings-shortcut-scheme",
            "settings-reset",
            "settings-reload",
            "settings-save",
        }:
            return True
        return isinstance(widget, (Input, Select, Checkbox, Button))

    def _is_preview_panel_widget(self, widget: object) -> bool:
        if self._active_tab() != "preview":
            return False
        return isinstance(widget, VerticalScroll)

    def _tab_label(self, tab_id: str) -> str:
        labels = {
            "profiles": "配置Profile",
            "providers": "提供方",
            "models": "模型",
            "preview": "预览",
            "settings": "设置",
            "help": "帮助",
        }
        return labels.get(tab_id, tab_id)
