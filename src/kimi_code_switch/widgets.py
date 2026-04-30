from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Static

from . import __version__
from .panel_settings import DEFAULT_THEME

if TYPE_CHECKING:
    from .tui import ConfigPanelApp


def _get_config_panel_app_class():
    from .tui import ConfigPanelApp
    return ConfigPanelApp


ABOUT_LINES = (
    ("作者", "Hulk Sun"),
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
        def __init__(self, card: SummaryCard) -> None:
            self.card = card
            super().__init__()

    def __init__(self, target_tab: str, *, id: str, classes: str) -> None:
        super().__init__("", id=id, classes=classes)
        self.target_tab = target_tab

    def action_select_card(self) -> None:
        self.post_message(self.Selected(self))

    def action_focus_previous_summary(self) -> None:
        app = self.app
        if isinstance(app, _get_config_panel_app_class()):
            app.focus_previous_summary_item()

    def action_focus_next_summary(self) -> None:
        app = self.app
        if isinstance(app, _get_config_panel_app_class()):
            app.focus_next_summary_item()

    def action_focus_main_menu(self) -> None:
        app = self.app
        if isinstance(app, _get_config_panel_app_class()):
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
        if isinstance(app, _get_config_panel_app_class()):
            app.focus_previous_summary_item()

    def key_right(self, event) -> None:
        event.stop()
        app = self.app
        if isinstance(app, _get_config_panel_app_class()):
            app.focus_next_summary_item()

    def key_down(self, event) -> None:
        event.stop()
        app = self.app
        if isinstance(app, _get_config_panel_app_class()):
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
        border: none;
    }

    #about-close:focus {
        border: none;
    }

    AboutDialog.-theme-graphite {
        background: rgba(10, 10, 12, 0.82);
    }

    AboutDialog.-theme-graphite #about-dialog {
        background: #16181d;
        border: round #646b75;
    }

    AboutDialog.-theme-graphite #about-title {
        color: #dde2ea;
    }

    AboutDialog.-theme-graphite .about-section {
        color: #c8ced9;
    }

    AboutDialog.-theme-graphite #about-version {
        color: #a7b0bd;
    }

    AboutDialog.-theme-graphite Button.-primary {
        background: #6d7582;
        color: #0f1115;
    }

    AboutDialog.-theme-ember {
        background: rgba(22, 11, 5, 0.8);
    }

    AboutDialog.-theme-ember #about-dialog {
        background: #25150d;
        border: round #f59e0b;
    }

    AboutDialog.-theme-ember #about-title {
        color: #ffd08a;
    }

    AboutDialog.-theme-ember .about-section {
        color: #f3d7bc;
    }

    AboutDialog.-theme-ember #about-version {
        color: #fbbf24;
    }

    AboutDialog.-theme-ember Button.-primary {
        background: #c97316;
        color: #fff7ed;
    }
    """

    BINDINGS = [Binding("escape", "close_about", "关闭", show=False)]

    def __init__(self, theme_name: str = DEFAULT_THEME) -> None:
        super().__init__()
        if theme_name in {"graphite", "ember"}:
            self.add_class(f"-theme-{theme_name}")

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
