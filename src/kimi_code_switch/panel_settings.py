from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ._toml import tomllib
from .config_store import PROFILE_FILENAME
from .toml_utils import dumps_toml


PANEL_SETTINGS_VERSION = 1
PANEL_SETTINGS_FILENAME = "config.panel.toml"
DEFAULT_CONFIG_PATH = Path("~/.kimi/config.toml").expanduser()
DEFAULT_PANEL_SETTINGS_PATH = DEFAULT_CONFIG_PATH.with_name(PANEL_SETTINGS_FILENAME)
DEFAULT_THEME = "ocean"
DEFAULT_SHORTCUT_SCHEME = "default"


@dataclass
class PanelSettings:
    settings_path: Path
    config_path: Path
    profiles_path: Optional[Path] = None
    follow_config_profiles: bool = True
    theme: str = DEFAULT_THEME
    shortcut_scheme: str = DEFAULT_SHORTCUT_SCHEME

    def resolved_config_path(self) -> Path:
        return self.config_path.expanduser()

    def resolved_profiles_path(self) -> Path:
        if self.follow_config_profiles or self.profiles_path is None:
            return self.resolved_config_path().with_name(PROFILE_FILENAME)
        return self.profiles_path.expanduser()

    def explicit_profiles_path(self) -> Optional[Path]:
        if self.follow_config_profiles:
            return None
        return self.resolved_profiles_path()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": PANEL_SETTINGS_VERSION,
            "config_path": str(self.resolved_config_path()),
            "follow_config_profiles": self.follow_config_profiles,
            "profiles_path": (
                ""
                if self.follow_config_profiles
                else str(self.resolved_profiles_path())
            ),
            "theme": self.theme,
            "shortcut_scheme": self.shortcut_scheme,
        }


def default_panel_settings(
    *,
    settings_path: Optional[Path] = None,
    config_path: Optional[Path] = None,
    profiles_path: Optional[Path] = None,
    theme: str = DEFAULT_THEME,
    shortcut_scheme: str = DEFAULT_SHORTCUT_SCHEME,
) -> PanelSettings:
    resolved_settings = (
        settings_path.expanduser()
        if settings_path is not None
        else DEFAULT_PANEL_SETTINGS_PATH
    )
    resolved_config = config_path.expanduser() if config_path is not None else DEFAULT_CONFIG_PATH
    return PanelSettings(
        settings_path=resolved_settings,
        config_path=resolved_config,
        profiles_path=profiles_path.expanduser() if profiles_path is not None else None,
        follow_config_profiles=profiles_path is None,
        theme=theme,
        shortcut_scheme=shortcut_scheme,
    )


def load_panel_settings(settings_path: Optional[Path] = None) -> PanelSettings:
    base = default_panel_settings(settings_path=settings_path)
    data = _read_toml(base.settings_path)
    if not data:
        return base

    config_path_raw = str(data.get("config_path") or base.config_path)
    config_path = Path(config_path_raw).expanduser()

    follow_config_profiles = bool(
        data.get("follow_config_profiles", data.get("profiles_path", "") in {"", None})
    )
    profiles_path_raw = str(data.get("profiles_path") or "").strip()
    profiles_path = Path(profiles_path_raw).expanduser() if profiles_path_raw else None

    theme = str(data.get("theme") or DEFAULT_THEME)
    shortcut_scheme = str(data.get("shortcut_scheme") or DEFAULT_SHORTCUT_SCHEME)

    return PanelSettings(
        settings_path=base.settings_path,
        config_path=config_path,
        profiles_path=profiles_path,
        follow_config_profiles=follow_config_profiles,
        theme=theme,
        shortcut_scheme=shortcut_scheme,
    )


def save_panel_settings(settings: PanelSettings) -> None:
    settings.settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings.settings_path.write_text(
        build_panel_settings_document(settings),
        encoding="utf-8",
    )


def build_panel_settings_document(settings: PanelSettings) -> str:
    return dumps_toml(settings.to_dict())


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return dict(tomllib.load(handle))
