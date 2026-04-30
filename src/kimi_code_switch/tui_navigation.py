from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from rich.syntax import Syntax
from rich.text import Text
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Input, Select, Static, TabbedContent
from textual.widgets._tabbed_content import ContentTabs

from .config_store import (
    AppState,
    apply_profile,
    build_config_document,
    build_profiles_document,
    clone_state,
    save_state,
    upsert_model,
    upsert_profile,
    upsert_provider,
)
from .preview import (
    build_compact_preview,
    read_file_text,
    unified_diff,
)
from .panel_settings import DEFAULT_SHORTCUT_SCHEME, default_panel_settings
from .themes import (
    SHORTCUT_SCHEMES,
    THEME_LABELS,
)
from .widgets import SummaryCard

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.widgets import TabbedContent

    from .panel_settings import PanelSettings


class NavigationMixin(object):
    """Mixin providing navigation, table refresh, preview, and status methods."""

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
            self.query_one("#about-open", Widget),
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

        current_config = read_file_text(self.state.config_path)
        current_profiles = read_file_text(self.state.profiles_path)
        next_config = build_config_document(draft_state)
        next_profiles = build_profiles_document(draft_state)
        config_diff = unified_diff(
            current_config,
            next_config,
            str(self.state.config_path),
            f"{self.state.config_path} (preview)",
        )
        profiles_diff = unified_diff(
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
            "compact_text": build_compact_preview(config_diff, profiles_diff, self._tab_label(self._preview_source_tab())),
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

    def _matches_query(self, query: str, *parts: str) -> bool:
        if not query:
            return True
        haystack = " ".join(parts).lower()
        return query in haystack

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

    def _cycle_focus_within_row(self, step: int) -> bool:
        focused = self.focused
        if not isinstance(focused, Widget):
            return False
        parent = focused.parent
        if not isinstance(parent, Horizontal):
            return False

        siblings: list[Widget] = []
        for child in parent.children:
            if not getattr(child, "can_focus", False):
                continue
            if getattr(child, "disabled", False):
                continue
            siblings.append(child)

        if len(siblings) < 2 or focused not in siblings:
            return False

        index = siblings.index(focused)
        next_index = (index + step) % len(siblings)
        self.set_focus(siblings[next_index])
        return True

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
        if isinstance(widget, Widget):
            node: Optional[Widget] = widget
            while node is not None:
                if node.has_class("editor-field"):
                    return True
                node = node.parent if isinstance(node.parent, Widget) else None
        return False

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

    def _move_cursor_to_name(
        self, table: DataTable, names: list[str], target_name: Optional[str]
    ) -> None:
        if not names:
            return
        name = target_name if target_name in names else names[0]
        table.move_cursor(row=names.index(name), column=0, animate=False, scroll=True)
