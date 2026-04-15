from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
import asyncio

from rich.text import Text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = PROJECT_ROOT / ".vendor"
SRC_ROOT = PROJECT_ROOT / "src"
if str(VENDOR_ROOT) not in sys.path:
    sys.path.insert(0, str(VENDOR_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kimi_code_switch import __version__, _homebrew_cellar_version_from_path
from kimi_code_switch.config_store import (
    build_config_document,
    clone_profile,
    DEFAULT_PROFILE_NAME,
    apply_profile,
    delete_model,
    delete_provider,
    load_state,
    save_state,
    upsert_model,
    upsert_profile,
    upsert_provider,
)
from kimi_code_switch.panel_settings import (
    DEFAULT_SHORTCUT_SCHEME,
    DEFAULT_THEME,
    build_panel_settings_document,
    default_panel_settings,
    load_panel_settings,
    save_panel_settings,
)
from kimi_code_switch.tui import ConfigPanelApp

from textual.widgets import Button, DataTable, Input, Select, Static, TabbedContent


SAMPLE_CONFIG = """
default_model = "kimi_gateway/kimi-k2.5"
default_thinking = true
default_yolo = false
default_plan_mode = false
default_editor = ""
theme = "dark"
show_thinking_stream = false
hooks = []
merge_all_available_skills = false

[models]
[models."kimi_gateway/kimi-k2.5"]
provider = "kimi_gateway"
model = "kimi-k2.5"
max_context_size = 262144
capabilities = ["thinking", "image_in", "video_in"]

[providers]
[providers.kimi_gateway]
type = "kimi"
base_url = "https://example.test/v1"
api_key = "sk-test"

[loop_control]
max_steps_per_turn = 100
""".strip()

EMPTY_CONFIG = ""


class ConfigStoreTests(unittest.TestCase):
    def test_bootstrap_default_profile_from_main_config(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")

            state = load_state(config_path)

            self.assertEqual(state.active_profile, DEFAULT_PROFILE_NAME)
            self.assertIn(DEFAULT_PROFILE_NAME, state.profiles)
            self.assertEqual(
                state.profiles[DEFAULT_PROFILE_NAME].default_model,
                "kimi_gateway/kimi-k2.5",
            )

    def test_apply_profile_updates_main_config_and_persists(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
            state = load_state(config_path)

            upsert_provider(
                state,
                name="alt_gateway",
                provider_type="openai",
                base_url="https://alt.example/v1",
                api_key="sk-alt",
            )
            upsert_model(
                state,
                name="alt_gateway/gpt-4.1",
                provider="alt_gateway",
                model="gpt-4.1",
                max_context_size=128000,
                capabilities=["thinking"],
            )
            upsert_profile(
                state,
                name="work",
                label="Work",
                default_model="alt_gateway/gpt-4.1",
                default_thinking=False,
                default_yolo=True,
                default_plan_mode=True,
                default_editor="vim",
                theme="light",
                show_thinking_stream=True,
                merge_all_available_skills=True,
            )

            apply_profile(state, "work")
            save_state(state)

            saved = tomllib.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["default_model"], "alt_gateway/gpt-4.1")
            self.assertTrue(saved["default_yolo"])
            self.assertEqual(saved["theme"], "light")

    def test_delete_provider_blocked_when_model_still_uses_it(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
            state = load_state(config_path)

            with self.assertRaisesRegex(ValueError, "still used by model"):
                delete_provider(state, "kimi_gateway")

    def test_delete_model_blocked_when_profile_uses_it(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
            state = load_state(config_path)

            with self.assertRaisesRegex(ValueError, "still used by profile"):
                delete_model(state, "kimi_gateway/kimi-k2.5")

    def test_apply_profile_missing_model_error_is_actionable(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
            state = load_state(config_path)
            state.profiles[DEFAULT_PROFILE_NAME].default_model = "kimi-k2.5"

            with self.assertRaisesRegex(
                ValueError,
                "这里需要填写 \\[models\\] 下的模型 key，不是 model 字段值",
            ):
                apply_profile(state, DEFAULT_PROFILE_NAME)

    def test_upsert_profile_missing_model_error_lists_available_keys(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
            state = load_state(config_path)

            with self.assertRaisesRegex(
                ValueError,
                "可用模型 key：kimi_gateway/kimi-k2.5",
            ):
                upsert_profile(
                    state,
                    name="broken",
                    label="Broken",
                    default_model="kimi-k2.5",
                    default_thinking=True,
                    default_yolo=False,
                    default_plan_mode=False,
                    default_editor="",
                    theme="dark",
                    show_thinking_stream=False,
                    merge_all_available_skills=False,
                )

    def test_clone_profile_copies_selected_profile_values(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
            state = load_state(config_path)

            clone_profile(state, "default", "default-copy", "Default Copy")

            source = state.profiles["default"]
            cloned = state.profiles["default-copy"]
            self.assertEqual(cloned.label, "Default Copy")
            self.assertEqual(cloned.default_model, source.default_model)
            self.assertEqual(cloned.default_thinking, source.default_thinking)
            self.assertEqual(cloned.theme, source.theme)

    def test_build_config_document_matches_current_config(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
            state = load_state(config_path)

            document = build_config_document(state)

            self.assertIn('default_model = "kimi_gateway/kimi-k2.5"', document)
            self.assertIn("[providers.kimi_gateway]", document)

    def test_panel_settings_defaults_and_roundtrip(self) -> None:
        with TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "config.panel.toml"

            defaults = load_panel_settings(settings_path)
            self.assertEqual(defaults.theme, DEFAULT_THEME)
            self.assertEqual(defaults.shortcut_scheme, DEFAULT_SHORTCUT_SCHEME)
            self.assertTrue(defaults.follow_config_profiles)

            saved = default_panel_settings(
                settings_path=settings_path,
                config_path=Path(tmp) / "custom-config.toml",
                profiles_path=Path(tmp) / "custom.profiles.toml",
                theme="graphite",
                shortcut_scheme="letters",
            )
            save_panel_settings(saved)

            reloaded = load_panel_settings(settings_path)
            self.assertEqual(
                reloaded.resolved_config_path(),
                Path(tmp) / "custom-config.toml",
            )
            self.assertEqual(
                reloaded.resolved_profiles_path(),
                Path(tmp) / "custom.profiles.toml",
            )
            self.assertEqual(reloaded.theme, "graphite")
            self.assertEqual(reloaded.shortcut_scheme, "letters")

    def test_build_panel_settings_document_contains_current_values(self) -> None:
        settings = default_panel_settings(
            settings_path=Path("/tmp/config.panel.toml"),
            config_path=Path("/tmp/config.toml"),
            profiles_path=Path("/tmp/config.profiles.toml"),
            theme="ember",
            shortcut_scheme="letters",
        )

        document = build_panel_settings_document(settings)

        self.assertIn('config_path = "/tmp/config.toml"', document)
        self.assertIn('theme = "ember"', document)
        self.assertIn('shortcut_scheme = "letters"', document)

    def test_render_homebrew_formula_script_generates_expected_formula(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "kimi-code-switch.rb"

            subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "scripts" / "render_homebrew_formula.py"),
                    "--version",
                    "0.1.0",
                    "--github-repo",
                    "example/kimi-code-switch",
                    "--arm64-sha256",
                    "a" * 64,
                    "--amd64-sha256",
                    "b" * 64,
                    "--output",
                    str(output),
                ],
                check=True,
            )

            formula = output.read_text(encoding="utf-8")
            self.assertIn('homepage "https://github.com/example/kimi-code-switch"', formula)
            self.assertIn('version "0.1.0"', formula)
            self.assertIn("kimi-code-switch-v#{version}-macos-arm64.tar.gz", formula)
            self.assertIn("kimi-code-switch-v#{version}-macos-amd64.tar.gz", formula)

    def test_homebrew_cellar_version_can_be_parsed_from_path(self) -> None:
        parsed = _homebrew_cellar_version_from_path(
            Path("/opt/homebrew/Cellar/kimi-code-switch/1.0.3/bin/kimi-config-panel")
        )

        self.assertEqual(parsed, "1.0.3")

    def test_textual_app_mounts_and_populates_tables(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as _pilot:
                    profiles = app.query_one("#profiles-table", DataTable)
                    providers = app.query_one("#providers-table", DataTable)
                    models = app.query_one("#models-table", DataTable)
                    settings = app.query_one("#settings-table", DataTable)

                    self.assertEqual(profiles.row_count, 1)
                    self.assertEqual(providers.row_count, 1)
                    self.assertEqual(models.row_count, 1)
                    self.assertEqual(settings.row_count, 4)

        asyncio.run(run())

    def test_textual_about_dialog_renders_author_info_and_version(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.action_show_about()
                    await pilot.pause()

                    title = app.screen.query_one("#about-title", Static)
                    version = app.screen.query_one("#about-version", Static)
                    body = app.screen.query_one("#about-body", Static)

                    self.assertIn("关于 Kimi 配置面板", str(title.render()))
                    self.assertIn(__version__, str(version.render()))
                    self.assertIn("Hulk Sun", str(body.render()))
                    self.assertIn("github.com/sunhao-java", str(body.render()))

        asyncio.run(run())

    def test_textual_disables_dependent_actions_when_dependencies_missing(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(EMPTY_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    await pilot.pause()

                    self.assertTrue(app.query_one("#profile-model", Select).disabled)
                    self.assertTrue(app.query_one("#profile-save", Button).disabled)
                    self.assertTrue(app.query_one("#profile-preview", Button).disabled)
                    self.assertTrue(app.query_one("#profile-activate", Button).disabled)

                    self.assertTrue(app.query_one("#model-provider", Select).disabled)
                    self.assertTrue(app.query_one("#model-save", Button).disabled)
                    self.assertTrue(app.query_one("#model-preview", Button).disabled)

        asyncio.run(run())

    def test_textual_can_create_first_provider_then_first_model_without_deadlock(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(EMPTY_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    await pilot.pause()

                    tabs.active = "providers"
                    await pilot.pause()
                    app.query_one("#provider-name", Input).value = "gateway"
                    app.query_one("#provider-type", Input).value = "kimi"
                    app.query_one("#provider-base-url", Input).value = "https://example.test/v1"
                    app.query_one("#provider-api-key", Input).value = "sk-test"
                    await pilot.pause()
                    await pilot.press("ctrl+s")
                    await pilot.pause()

                    tabs.active = "models"
                    await pilot.pause()
                    app.query_one("#model-name", Input).value = "gateway/kimi-k2.5"
                    app.query_one("#model-provider", Select).value = "gateway"
                    app.query_one("#model-remote-name", Input).value = "kimi-k2.5"
                    app.query_one("#model-context-size", Input).value = "262144"
                    app.query_one("#model-capabilities", Input).value = "thinking"
                    await pilot.pause()
                    await pilot.press("ctrl+s")
                    await pilot.pause()

                    self.assertIn("gateway/kimi-k2.5", app.state.main_config["models"])
                    self.assertEqual(
                        app.state.profiles[DEFAULT_PROFILE_NAME].default_model,
                        "gateway/kimi-k2.5",
                    )
                    self.assertEqual(
                        app.state.main_config["default_model"],
                        "gateway/kimi-k2.5",
                    )
                    status = app.query_one("#status", Static)
                    self.assertIn("模型已保存", str(status.render()))

        asyncio.run(run())

    def test_summary_cards_render_text(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    await pilot.pause()
                    summary_model = app.query_one("#summary-model")
                    summary_inventory = app.query_one("#summary-inventory")

                    self.assertIn("当前生效模型", str(summary_model.render()))
                    self.assertIn("资源概览", str(summary_inventory.render()))
                    self.assertIn("F8", str(summary_model.render()))
                    self.assertIn("F9", str(summary_inventory.render()))

        asyncio.run(run())

    def test_ctrl_number_shortcuts_switch_main_tabs(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    await pilot.pause()

                    await pilot.press("ctrl+3")
                    await pilot.pause()
                    self.assertEqual(tabs.active, "models")

                    await pilot.press("ctrl+4")
                    await pilot.pause()
                    self.assertEqual(tabs.active, "preview")

                    await pilot.press("ctrl+5")
                    await pilot.pause()
                    self.assertEqual(tabs.active, "settings")

                    await pilot.press("ctrl+6")
                    await pilot.pause()
                    self.assertEqual(tabs.active, "help")

        asyncio.run(run())

    def test_function_key_shortcuts_focus_summary_cards(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    summary_model = app.query_one("#summary-model")
                    summary_inventory = app.query_one("#summary-inventory")
                    await pilot.pause()

                    await pilot.press("f8")
                    await pilot.pause()
                    self.assertTrue(summary_model.has_focus)

                    await pilot.press("f9")
                    await pilot.pause()
                    self.assertTrue(summary_inventory.has_focus)

        asyncio.run(run())

    def test_enter_moves_from_preview_menu_to_preview_tabs(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    tabs.active = "preview"
                    await pilot.pause()

                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertTrue(app.query_one("#preview-tabs > ContentTabs").has_focus)

        asyncio.run(run())

    def test_tab_switches_preview_subtabs_when_preview_tabs_focused(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    preview_tabs = app.query_one("#preview-tabs", TabbedContent)
                    tabs.active = "preview"
                    await pilot.pause()

                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertEqual(preview_tabs.active, "preview-config")

                    await pilot.press("tab")
                    await pilot.pause()
                    self.assertEqual(preview_tabs.active, "preview-config-diff")

        asyncio.run(run())

    def test_textual_preview_generates_config_and_diff(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    app.action_preview_current()
                    await pilot.pause()

                    self.assertEqual(app.preview_payload["source_tab"], "profiles")
                    self.assertIn('default_model = "kimi_gateway/kimi-k2.5"', app.preview_payload["config_text"])
                    self.assertIn("---", app.preview_payload["config_diff"])
                    self.assertIn("仅看变更", app.preview_payload["compact_text"])

        asyncio.run(run())

    def test_textual_activate_profile_shows_actionable_missing_model_error(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                state.profiles[DEFAULT_PROFILE_NAME].default_model = "kimi-k2.5"
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.action_activate_profile()
                    await pilot.pause()

                    status = app.query_one("#status", Static)
                    self.assertIn("模型 key", str(status.render()))
                    self.assertIn("kimi_gateway/kimi-k2.5", str(status.render()))

        asyncio.run(run())

    def test_textual_save_settings_persists_panel_settings_file(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                settings = default_panel_settings(settings_path=Path(tmp) / "config.panel.toml")
                app = ConfigPanelApp(state, settings)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    tabs.active = "settings"
                    await pilot.pause()

                    app.query_one("#settings-theme").value = "graphite"
                    app.query_one("#settings-shortcut-scheme").value = "letters"
                    await pilot.pause()

                    await pilot.press("ctrl+s")
                    await pilot.pause()

                    saved = load_panel_settings(Path(tmp) / "config.panel.toml")
                    self.assertEqual(saved.theme, "graphite")
                    self.assertEqual(saved.shortcut_scheme, "letters")

        asyncio.run(run())

    def test_tab_switches_main_menu_when_menu_is_focused(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    await pilot.pause()

                    self.assertEqual(tabs.active, "profiles")
                    await pilot.press("tab")
                    await pilot.pause()
                    self.assertEqual(tabs.active, "providers")

        asyncio.run(run())

    def test_enter_moves_from_menu_to_list_to_editor(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    await pilot.pause()
                    menu = app.query_one("#tabs > ContentTabs")
                    profiles_table = app.query_one("#profiles-table", DataTable)
                    profile_name = app.query_one("#profile-name", Input)

                    self.assertTrue(menu.has_focus)

                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertTrue(profiles_table.has_focus)

                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertTrue(profile_name.has_focus)

        asyncio.run(run())

    def test_enter_moves_from_provider_list_to_focusable_editor_field(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    tabs.active = "providers"
                    await pilot.pause()

                    providers_table = app.query_one("#providers-table", DataTable)
                    provider_type = app.query_one("#provider-type", Input)

                    app.set_focus(providers_table)
                    await pilot.pause()
                    self.assertTrue(providers_table.has_focus)

                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertTrue(provider_type.has_focus)

        asyncio.run(run())

    def test_enter_moves_from_model_list_to_focusable_editor_field(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    tabs.active = "models"
                    await pilot.pause()

                    models_table = app.query_one("#models-table", DataTable)
                    model_provider = app.query_one("#model-provider")

                    app.set_focus(models_table)
                    await pilot.pause()
                    self.assertTrue(models_table.has_focus)

                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertTrue(model_provider.has_focus)

        asyncio.run(run())

    def test_summary_card_can_open_target_list(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    summary_model = app.query_one("#summary-model")
                    models_table = app.query_one("#models-table", DataTable)

                    summary_model.action_select_card()
                    await pilot.pause()

                    self.assertEqual(tabs.active, "models")
                    self.assertTrue(models_table.has_focus)

        asyncio.run(run())

    def test_escape_returns_from_editor_to_main_menu(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    await pilot.pause()
                    menu = app.query_one("#tabs > ContentTabs")
                    profile_name = app.query_one("#profile-name", Input)

                    await pilot.press("enter")
                    await pilot.pause()
                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertTrue(profile_name.has_focus)

                    await pilot.press("escape")
                    await pilot.pause()
                    self.assertTrue(menu.has_focus)

        asyncio.run(run())

    def test_escape_returns_from_list_to_main_menu(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    await pilot.pause()
                    menu = app.query_one("#tabs > ContentTabs")
                    profiles_table = app.query_one("#profiles-table", DataTable)

                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertTrue(profiles_table.has_focus)

                    await pilot.press("escape")
                    await pilot.pause()
                    self.assertTrue(menu.has_focus)

        asyncio.run(run())

    def test_shift_tab_returns_from_editor_to_main_menu(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    await pilot.pause()
                    menu = app.query_one("#tabs > ContentTabs")
                    profile_name = app.query_one("#profile-name", Input)

                    await pilot.press("enter")
                    await pilot.pause()
                    await pilot.press("enter")
                    await pilot.pause()
                    self.assertTrue(profile_name.has_focus)

                    await pilot.press("shift+tab")
                    await pilot.pause()
                    self.assertTrue(menu.has_focus)

        asyncio.run(run())

    def test_compact_preview_groups_added_removed_and_modified(self) -> None:
        app = ConfigPanelApp.__new__(ConfigPanelApp)

        diff_text = "\n".join(
            [
                "--- before",
                "+++ after",
                "@@ -1,4 +1,5 @@",
                '-default_model = "old/model"',
                '+default_model = "new/model"',
                ' theme = "dark"',
                '+new_key = "value"',
                '-old_key = "legacy"',
            ]
        )

        changes = ConfigPanelApp._extract_compact_diff_lines(app, diff_text)
        rendered = ConfigPanelApp._render_compact_sections(app, changes)

        self.assertEqual(
            changes,
            {
                "added": ['  + new_key = "value"'],
                "removed": ['  - old_key = "legacy"'],
                "modified": ['  ~ default_model = "old/model" -> default_model = "new/model"'],
            },
        )
        self.assertIn("  新增", rendered)
        self.assertIn("  删除", rendered)
        self.assertIn("  修改", rendered)

    def test_highlight_match_marks_query_ranges(self) -> None:
        app = ConfigPanelApp.__new__(ConfigPanelApp)

        highlighted = ConfigPanelApp._highlight_match(app, "kimi_gateway", "gate")

        self.assertIsInstance(highlighted, Text)
        self.assertEqual(highlighted.plain, "kimi_gateway")
        self.assertTrue(highlighted.spans)
        self.assertEqual(highlighted.spans[0].start, 5)
        self.assertEqual(highlighted.spans[0].end, 9)

    def test_textual_filter_reduces_visible_rows(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                upsert_provider(
                    state,
                    name="second_gateway",
                    provider_type="openai",
                    base_url="https://second.example/v1",
                    api_key="sk-second",
                )
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    providers = app.query_one("#providers-table", DataTable)
                    self.assertEqual(providers.row_count, 2)

                    app.query_one("#providers-filter").value = "second"
                    await pilot.pause()

                    self.assertEqual(providers.row_count, 1)

        asyncio.run(run())

    def test_textual_ctrl_f_focuses_current_filter(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                upsert_provider(
                    state,
                    name="second_gateway",
                    provider_type="openai",
                    base_url="https://second.example/v1",
                    api_key="sk-second",
                )
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    tabs = app.query_one("#tabs", TabbedContent)
                    tabs.active = "providers"
                    await pilot.pause()

                    await pilot.press("ctrl+f")
                    await pilot.pause()
                    self.assertTrue(app.query_one("#providers-filter", Input).has_focus)

        asyncio.run(run())

    def test_textual_escape_clears_current_filter(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                upsert_provider(
                    state,
                    name="second_gateway",
                    provider_type="openai",
                    base_url="https://second.example/v1",
                    api_key="sk-second",
                )
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    providers = app.query_one("#providers-table", DataTable)
                    filter_input = app.query_one("#providers-filter", Input)
                    app.query_one("#tabs", TabbedContent).active = "providers"
                    await pilot.pause()

                    filter_input.focus()
                    filter_input.value = "second"
                    await pilot.pause()
                    self.assertEqual(providers.row_count, 1)

                    await pilot.press("escape")
                    await pilot.pause()

                    self.assertEqual(filter_input.value, "")
                    self.assertTrue(filter_input.has_focus)
                    self.assertEqual(providers.row_count, 2)

        asyncio.run(run())

    def test_textual_filter_highlights_matches_in_table(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.toml"
                config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")
                state = load_state(config_path)
                upsert_provider(
                    state,
                    name="second_gateway",
                    provider_type="openai",
                    base_url="https://second.example/v1",
                    api_key="sk-second",
                )
                app = ConfigPanelApp(state)

                async with app.run_test() as pilot:
                    filter_input = app.query_one("#providers-filter", Input)
                    filter_input.value = "second"
                    await pilot.pause()

                    providers = app.query_one("#providers-table", DataTable)
                    row = providers.get_row_at(0)

                    self.assertIsInstance(row[0], Text)
                    self.assertEqual(row[0].plain, "second_gateway")
                    self.assertTrue(row[0].spans)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
