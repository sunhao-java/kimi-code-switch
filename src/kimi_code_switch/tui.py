from __future__ import annotations

import difflib

from rich.syntax import Syntax
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
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

from .config_store import (
    AppState,
    Profile,
    apply_profile,
    build_config_document,
    build_profiles_document,
    clone_state,
    delete_model,
    delete_profile,
    delete_provider,
    save_state,
    upsert_model,
    upsert_profile,
    upsert_provider,
)


class SummaryCard(Static, can_focus=True):
    BINDINGS = [Binding("enter", "select_card", "进入", show=False)]

    class Selected(Message):
        def __init__(self, card: "SummaryCard") -> None:
            self.card = card
            super().__init__()

    def __init__(self, target_tab: str, *, id: str, classes: str) -> None:
        super().__init__("", id=id, classes=classes)
        self.target_tab = target_tab

    def action_select_card(self) -> None:
        self.post_message(self.Selected(self))

    def on_click(self) -> None:
        self.post_message(self.Selected(self))


class ConfigPanelApp(App[None]):
    ENABLE_COMMAND_PALETTE = False

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
        background: #122438;
        border: round #7dd3fc;
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

    #tabs {
        height: 1fr;
        background: #08111d;
        padding: 0 1 1 1;
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

    .form-panel {
        width: 48;
        min-width: 42;
        border: round #1b7f7b;
        background: #0d1828;
        padding: 1 2;
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

    Select, Input {
        width: 1fr;
        background: #08111c;
        color: #f3f8fd;
        border: tall #20374f;
    }

    .checkbox-group {
        height: auto;
        margin-top: 1;
    }

    .checkbox-group Checkbox {
        margin-bottom: 1;
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

    .preview-panel {
        height: 1fr;
        border: round #334e68;
        background: #0b1625;
        padding: 1;
    }

    #status {
        height: auto;
        color: #6ee7b7;
        padding: 0 2 1 2;
    }

    #help-view {
        padding: 1 2;
    }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
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

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.title = "Kimi 配置面板"
        self.sub_title = "提供方、模型与配置档切换"

        self.selected_profile_name: str | None = None
        self.selected_provider_name: str | None = None
        self.selected_model_name: str | None = None
        self.last_editor_tab = "profiles"
        self.preview_payload: dict[str, str] = {}

        self.provider_name_locked = False
        self.model_name_locked = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="summary-bar"):
            yield SummaryCard("profiles", id="summary-profile", classes="summary-card -hot")
            yield SummaryCard("models", id="summary-model", classes="summary-card -accent")
            yield SummaryCard("providers", id="summary-inventory", classes="summary-card -warm")
        with TabbedContent(initial="profiles", id="tabs"):
            with TabPane("配置档", id="profiles"):
                with Horizontal(classes="workspace"):
                    with Vertical(classes="list-panel"):
                        yield Static("配置档列表", classes="panel-title")
                        yield Input(
                            placeholder="搜索配置档名称 / 标签",
                            id="profiles-filter",
                            classes="filter-input",
                        )
                        yield DataTable(id="profiles-table")
                    with Vertical(classes="form-panel"):
                        yield Static("配置档编辑器", classes="panel-title")
                        yield Label("配置档名称", classes="field-label")
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

            with TabPane("提供方", id="providers"):
                with Horizontal(classes="workspace"):
                    with Vertical(classes="list-panel"):
                        yield Static("提供方列表", classes="panel-title")
                        yield Input(
                            placeholder="搜索提供方名称 / 地址 / 类型",
                            id="providers-filter",
                            classes="filter-input",
                        )
                        yield DataTable(id="providers-table")
                    with Vertical(classes="form-panel"):
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

            with TabPane("模型", id="models"):
                with Horizontal(classes="workspace"):
                    with Vertical(classes="list-panel"):
                        yield Static("模型列表", classes="panel-title")
                        yield Input(
                            placeholder="搜索模型名称 / provider / 远端模型",
                            id="models-filter",
                            classes="filter-input",
                        )
                        yield DataTable(id="models-table")
                    with Vertical(classes="form-panel"):
                        yield Static("模型编辑器", classes="panel-title")
                        yield Label("模型名称", classes="field-label")
                        yield Input(id="model-name", classes="wide-input")
                        yield Label("所属提供方", classes="field-label")
                        yield Select([], id="model-provider", allow_blank=True)
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

            with TabPane("预览", id="preview"):
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
                        with TabPane("配置档 Diff", id="preview-profiles-diff"):
                            with VerticalScroll(classes="preview-panel"):
                                yield Static("", id="preview-profiles-diff-body")
                        with TabPane("仅看变更", id="preview-compact"):
                            with VerticalScroll(classes="preview-panel"):
                                yield Static("", id="preview-compact-body")

            with TabPane("帮助", id="help"):
                with VerticalScroll(id="help-view"):
                    yield Static(self._help_text())
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._configure_tables()
        self._refresh_select_options()
        self._refresh_all_tables()
        self._load_initial_forms()
        self._refresh_summary()
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
            self._set_status("克隆操作只适用于配置档页。", error=True)
            return
        self._clone_profile_draft()

    def action_activate_profile(self) -> None:
        if self._active_tab() != "profiles":
            self._set_status("启用操作只适用于配置档页。", error=True)
            return
        self._activate_selected_profile()

    def action_preview_current(self) -> None:
        self._open_preview()

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

    def on_data_table_row_selected(self, _: DataTable.RowSelected) -> None:
        self._focus_current_editor()

    def on_summary_card_selected(self, event: SummaryCard.Selected) -> None:
        self._activate_summary_card(event.card)

    def on_tabbed_content_tab_activated(self, _: TabbedContent.TabActivated) -> None:
        active = self._active_tab()
        if active not in {"preview", "help"}:
            self.last_editor_tab = active
        self.call_after_refresh(self._sync_visible_form)

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

    def _refresh_all_tables(self) -> None:
        self._refresh_profiles_table(self.selected_profile_name or self.state.active_profile)
        self._refresh_providers_table(self.selected_provider_name)
        self._refresh_models_table(
            self.selected_model_name or str(self.state.main_config.get("default_model", ""))
        )

    def _refresh_profiles_table(self, select_name: str | None = None) -> None:
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

    def _refresh_providers_table(self, select_name: str | None = None) -> None:
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

    def _refresh_models_table(self, select_name: str | None = None) -> None:
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
        self._set_status("已创建新的配置档草稿。")

    def _clone_profile_draft(self) -> None:
        source = self._profile_from_form()
        source_name = self.query_one("#profile-name", Input).value.strip() or "profile"
        source.label = self.query_one("#profile-label", Input).value.strip() or "配置档"
        source.name = self._unique_profile_name(source_name)
        source.label = f"{source.label} 副本"
        self.selected_profile_name = None
        self._set_profile_form(source, editable_name=True)
        self.query_one("#profile-name", Input).focus()
        self._set_status("已克隆当前配置档，请保存为新配置。")

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
        self.query_one("#model-name", Input).focus()
        self._set_status("已创建新的模型草稿。")

    def _save_profile_form(self) -> None:
        data = self._profile_payload_from_form()
        if not data["name"]:
            self._set_status("配置档名称不能为空。", error=True)
            return
        if not data["default_model"]:
            self._set_status("请先选择默认模型。", error=True)
            return

        upsert_profile(self.state, **data)
        if self.state.active_profile == data["name"]:
            apply_profile(self.state, data["name"])
        save_state(self.state)
        self.selected_profile_name = data["name"]
        self._refresh_profiles_table(data["name"])
        self._load_profile_form(data["name"])
        self._refresh_summary()
        self._set_status(f"配置档已保存：{data['name']}")

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

        upsert_provider(
            self.state,
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key=api_key,
        )
        save_state(self.state)
        self.selected_provider_name = name
        self.provider_name_locked = True
        self._refresh_select_options()
        self._refresh_providers_table(name)
        self._refresh_models_table(self.selected_model_name)
        self._load_provider_form(name)
        self._refresh_summary()
        self._set_status(f"提供方已保存：{name}")

    def _save_model_form(self) -> None:
        name = self.query_one("#model-name", Input).value.strip()
        provider = self._select_value("#model-provider")
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
        upsert_model(
            self.state,
            name=name,
            provider=provider,
            model=remote_model,
            max_context_size=max_context_size,
            capabilities=capabilities,
        )
        if self.state.active_profile in self.state.profiles:
            apply_profile(self.state, self.state.active_profile)
        save_state(self.state)
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
            self._set_status("请先选择要删除的配置档。", error=True)
            return
        try:
            delete_profile(self.state, self.selected_profile_name)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        save_state(self.state)
        self.selected_profile_name = None
        self._refresh_profiles_table(self.state.active_profile)
        if self.state.active_profile in self.state.profiles:
            self._load_profile_form(self.state.active_profile)
        self._refresh_summary()
        self._set_status("配置档已删除。")

    def _delete_selected_provider(self) -> None:
        if not self.selected_provider_name:
            self._set_status("请先选择要删除的提供方。", error=True)
            return
        try:
            delete_provider(self.state, self.selected_provider_name)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        save_state(self.state)
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
        try:
            delete_model(self.state, self.selected_model_name)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        save_state(self.state)
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
        name = self.query_one("#profile-name", Input).value.strip() or self.selected_profile_name
        if not name:
            self._set_status("请先选择或保存配置档。", error=True)
            return
        if name not in self.state.profiles:
            self._set_status("请先保存配置档，再执行启用。", error=True)
            return
        apply_profile(self.state, name)
        save_state(self.state)
        self.selected_profile_name = name
        self._refresh_profiles_table(name)
        self._refresh_summary()
        self._set_status(f"当前生效配置档：{name}")

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
        name_input.value = name
        name_input.disabled = lock_name
        self._set_select_value("#model-provider", provider)
        self.query_one("#model-remote-name", Input).value = remote_model
        self.query_one("#model-context-size", Input).value = max_context_size
        self.query_one("#model-capabilities", Input).value = capabilities

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

    def _select_value(self, selector: str) -> str:
        select = self.query_one(selector, Select)
        value = select.value
        if value in (None, Select.BLANK, Select.NULL):
            return ""
        return str(value)

    def _move_cursor_to_name(
        self, table: DataTable, names: list[str], target_name: str | None
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

    def _active_tab(self) -> str:
        return self.query_one("#tabs", TabbedContent).active

    def _main_tabs_widget(self) -> ContentTabs:
        return self.query_one("#tabs > ContentTabs", ContentTabs)

    def _preview_tabs_widget(self) -> ContentTabs:
        return self.query_one("#preview-tabs > ContentTabs", ContentTabs)

    def _preview_tabs_widget_optional(self) -> ContentTabs | None:
        return self.query_one_optional("#preview-tabs > ContentTabs", ContentTabs)

    def _focus_main_menu(self) -> None:
        self.set_focus(self._main_tabs_widget())

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

    def _current_preview_panel(self) -> VerticalScroll | None:
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

    def _current_list_widget(self) -> DataTable | None:
        selector = {
            "profiles": "#profiles-table",
            "providers": "#providers-table",
            "models": "#models-table",
        }.get(self._active_tab())
        if not selector:
            return None
        return self.query_one(selector, DataTable)

    def _editor_entry_widget(self, tab_id: str) -> Widget | None:
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
                "#model-name",
                "#model-provider",
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

    def _set_status(self, message: str, *, error: bool = False) -> None:
        widget = self.query_one("#status", Static)
        widget.update(message)
        widget.styles.color = "red" if error else "green"

    def _help_text(self) -> str:
        return "\n".join(
            [
                f"主配置文件：{self.state.config_path}",
                f"配置档文件：{self.state.profiles_path}",
                "",
                "快捷键：",
                "  q         退出",
                "  Tab       顶部菜单切换；预览下层标签内切换预览页签；其他场景切到下一项",
                "  Shift+Tab 列表/编辑区回顶部菜单，其他场景回上一项",
                "  Enter     菜单进入列表；预览页进入下层标签；列表进入右侧编辑区",
                "  Ctrl+N    当前页新建草稿",
                "  Ctrl+S    保存当前表单",
                "  Ctrl+D    删除当前选中项",
                "  Ctrl+C    克隆当前配置档",
                "  Ctrl+A    启用当前配置档",
                "  F6        查看预览与 diff",
                "  /, Ctrl+F 聚焦当前列表搜索框",
                "  Esc       列表/编辑/预览区回顶部菜单；搜索框有内容时先清空",
                "",
                "说明：",
                "  配置档用于维护多套默认组合，并将当前生效项写回 config.toml。",
                "  提供方和模型一旦创建后名称固定，如需改名请新建。",
                "  模型与提供方选择都通过下拉完成，无需手输。",
                "  列表支持实时搜索过滤，预览页可先看生成结果再保存。",
            ]
        )

    def _sync_visible_form(self) -> None:
        tab = self._active_tab()
        if tab == "profiles" and self.selected_profile_name:
            self._load_profile_form(self.selected_profile_name)
        elif tab == "providers" and self.selected_provider_name:
            self._load_provider_form(self.selected_provider_name)
        elif tab == "models" and self.selected_model_name:
            self._load_model_form(self.selected_model_name)
        elif tab == "preview":
            self._render_preview()

    def _refresh_summary(self) -> None:
        active_profile = self.state.active_profile or "未设置"
        active_model = str(self.state.main_config.get("default_model", "")) or "未设置"
        active_model_config = self.state.main_config["models"].get(active_model, {})
        active_provider = str(active_model_config.get("provider", "")) or "未设置"

        self.query_one("#summary-profile", SummaryCard).update(
            "当前配置档\n"
            f"{active_profile}\n"
            f"共 {len(self.state.profiles)} 个配置档\n"
            "回车进入配置档列表"
        )
        self.query_one("#summary-model", SummaryCard).update(
            "当前生效模型\n"
            f"{active_model}\n"
            f"提供方：{active_provider}\n"
            "回车进入模型列表"
        )
        self.query_one("#summary-inventory", SummaryCard).update(
            "资源概览\n"
            f"{len(self.state.main_config['providers'])} 个提供方\n"
            f"{len(self.state.main_config['models'])} 个模型\n"
            "回车进入提供方列表"
        )

    def _open_preview(self) -> None:
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
                raise ValueError("预览前必须填写配置档名称。")
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
            name = self.query_one("#model-name", Input).value.strip()
            provider = self._select_value("#model-provider")
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
            if draft_state.active_profile in draft_state.profiles:
                apply_profile(draft_state, draft_state.active_profile)
            return draft_state

        return draft_state

    def _preview_source_tab(self) -> str:
        active = self._active_tab()
        if active in {"preview", "help"}:
            return self.last_editor_tab
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

    def _highlight_match(self, value: str, query: str) -> str | Text:
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

    def _current_filter_widget(self) -> Input | None:
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

    def _filter_id_for_tab(self, tab_id: str) -> str | None:
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
        if self._active_tab() not in {"profiles", "providers", "models"}:
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
        }:
            return True
        return isinstance(widget, (Input, Select, Checkbox, Button))

    def _is_preview_panel_widget(self, widget: object) -> bool:
        if self._active_tab() != "preview":
            return False
        return isinstance(widget, VerticalScroll)

    def _tab_label(self, tab_id: str) -> str:
        labels = {
            "profiles": "配置档",
            "providers": "提供方",
            "models": "模型",
            "preview": "预览",
            "help": "帮助",
        }
        return labels.get(tab_id, tab_id)
