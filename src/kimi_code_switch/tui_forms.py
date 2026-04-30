from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from textual.widgets import Button, Checkbox, Input, Select, Static

from .config_store import (
    AppState,
    PROFILE_FILENAME,
    Profile,
    apply_profile,
    clone_state,
    delete_model,
    delete_profile,
    delete_provider,
    load_state,
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
from .themes import (
    SHORTCUT_SCHEMES,
    THEME_LABELS,
    THEME_OPTIONS,
)

if TYPE_CHECKING:
    pass


class FormMixin(object):
    """Mixin providing form CRUD, settings management, and dependency checks."""

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
        profile = self.state.profiles.get(name)
        if profile is None:
            return
        self.selected_profile_name = name
        self._set_profile_form(profile, editable_name=True)

    def _load_provider_form(self, name: str) -> None:
        provider = self.state.main_config["providers"].get(name)
        if provider is None:
            return
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
        model = self.state.main_config["models"].get(name)
        if model is None:
            return
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
