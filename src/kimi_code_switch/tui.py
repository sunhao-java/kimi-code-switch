from __future__ import annotations

from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
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

from .config_store import AppState
from .panel_settings import (
    DEFAULT_SHORTCUT_SCHEME,
    PanelSettings,
    default_panel_settings,
)
from .themes import (
    SHORTCUT_SCHEME_OPTIONS,
    SHORTCUT_SCHEMES,
    THEME_OPTIONS,
    build_app_css,
)
from .tui_forms import FormMixin
from .tui_navigation import NavigationMixin
from .widgets import AboutButton, AboutDialog, SummaryCard


class ConfigPanelApp(FormMixin, NavigationMixin, App[None]):
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
        "models": "F9",
        "providers": "F8",
        "about": "F10",
    }

    CSS = build_app_css()

    BINDINGS = [
        ("q", "quit", "退出"),
        Binding("ctrl+1", "switch_to_profiles", "配置Profile页", show=False),
        Binding("ctrl+2", "switch_to_providers", "提供方页", show=False),
        Binding("ctrl+3", "switch_to_models", "模型页", show=False),
        Binding("ctrl+4", "switch_to_preview_tab", "预览页", show=False),
        Binding("ctrl+5", "switch_to_settings", "设置页", show=False),
        Binding("ctrl+6", "switch_to_help", "帮助页", show=False),
        Binding("f7", "focus_profile_summary", "当前配置Profile", show=False),
        Binding("f8", "focus_inventory_summary", "提供方", show=False),
        Binding("f9", "focus_model_summary", "当前生效模型", show=False),
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
                    with VerticalScroll(classes="form-panel editor-field"):
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
                    with VerticalScroll(classes="form-panel editor-field"):
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
                    with VerticalScroll(classes="form-panel editor-field"):
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
                    with VerticalScroll(classes="form-panel editor-field"):
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
        self.call_after_refresh(lambda: self._focus_summary_card("profiles"))
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
        self.push_screen(AboutDialog(self.panel_settings.theme))

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
        if self._cycle_focus_within_row(1):
            return
        self.action_focus_next()

    def action_previous_menu(self) -> None:
        tabs = self._main_tabs_widget()
        focused = self.focused
        if focused is tabs:
            tabs.action_previous_tab()
            return
        preview_tabs = self._preview_tabs_widget_optional()
        if preview_tabs is not None and focused is preview_tabs:
            preview_tabs.action_previous_tab()
            return
        if self._cycle_focus_within_row(-1):
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
            self._focus_current_list()
            self._set_status(f"已从{self._tab_label(self._active_tab())}编辑区返回列表。")
            return
        if self._is_preview_panel_widget(self.focused):
            self._focus_preview_tabs()
            self._set_status("已从预览内容返回预览页签。")
            return
        if self.focused is self._main_tabs_widget():
            self.action_focus_summary_from_menu()

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
        key = event.key

        if key == "down" and self._is_summary_widget(self.focused):
            event.stop()
            self.focus_main_menu_from_summary()
            return

        if key in {"left", "right"} and self._is_summary_widget(self.focused):
            event.stop()
            if key == "left":
                self.focus_previous_summary_item()
            else:
                self.focus_next_summary_item()
            return

        if key == "up" and self.focused is self._main_tabs_widget():
            event.stop()
            self.action_focus_summary_from_menu()
            return

        scheme = SHORTCUT_SCHEMES.get(
            self.panel_settings.shortcut_scheme,
            SHORTCUT_SCHEMES[DEFAULT_SHORTCUT_SCHEME],
        )
        action_name = dict(scheme.get("aliases", {})).get(key)
        if not action_name:
            return
        event.stop()
        self.run_action(action_name)

    def key_down(self, event) -> None:
        if self._is_summary_widget(self.focused):
            event.stop()
            self.focus_main_menu_from_summary()

    def key_up(self, event) -> None:
        if self.focused is self._main_tabs_widget():
            event.stop()
            self.action_focus_summary_from_menu()
