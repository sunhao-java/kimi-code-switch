from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from os import getpid
from pathlib import Path
from typing import Any, Optional

from ._toml import tomllib
from .toml_utils import dumps_toml


PROFILE_VERSION = 1
PROFILE_FILENAME = "config.profiles.toml"
DEFAULT_PROFILE_NAME = "default"
PROFILE_KEYS = (
    "default_model",
    "default_thinking",
    "default_yolo",
    "default_plan_mode",
    "default_editor",
    "theme",
    "show_thinking_stream",
    "merge_all_available_skills",
)
DEFAULTS: dict[str, Any] = {
    "default_model": "",
    "default_thinking": True,
    "default_yolo": False,
    "default_plan_mode": False,
    "default_editor": "",
    "theme": "dark",
    "show_thinking_stream": False,
    "merge_all_available_skills": False,
}


@dataclass
class Profile:
    name: str
    label: str
    default_model: str
    default_thinking: bool = True
    default_yolo: bool = False
    default_plan_mode: bool = False
    default_editor: str = ""
    theme: str = "dark"
    show_thinking_stream: bool = False
    merge_all_available_skills: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("name", None)
        return data


@dataclass
class AppState:
    config_path: Path
    profiles_path: Path
    main_config: dict[str, Any]
    profiles: dict[str, Profile] = field(default_factory=dict)
    active_profile: str = DEFAULT_PROFILE_NAME


def load_state(config_path: Path, profiles_path: Optional[Path] = None) -> AppState:
    resolved_config = config_path.expanduser()
    resolved_profiles = (
        profiles_path.expanduser()
        if profiles_path is not None
        else resolved_config.with_name(PROFILE_FILENAME)
    )

    main_config = _normalize_main_config(_read_toml(resolved_config))
    profiles_data = _read_toml(resolved_profiles)

    if profiles_data.get("version") == PROFILE_VERSION and "profiles" in profiles_data:
        profiles = {
            name: _profile_from_dict(name, raw)
            for name, raw in profiles_data["profiles"].items()
        }
        active_profile = str(
            profiles_data.get("active_profile") or _pick_active_profile(main_config, profiles)
        )
    else:
        profiles = bootstrap_profiles(main_config)
        active_profile = _pick_active_profile(main_config, profiles)

    if not profiles:
        profiles = bootstrap_profiles(main_config)
        active_profile = _pick_active_profile(main_config, profiles)

    active_profile = _ensure_active_profile(active_profile, profiles)
    return AppState(
        config_path=resolved_config,
        profiles_path=resolved_profiles,
        main_config=main_config,
        profiles=profiles,
        active_profile=active_profile,
    )


def save_state(state: AppState) -> None:
    if state.config_path == state.profiles_path:
        raise ValueError("Config path and profiles path must be different.")

    profiles_document = build_profiles_document(state)
    config_document = build_config_document(state)

    state.config_path.parent.mkdir(parents=True, exist_ok=True)
    state.profiles_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_documents(
        [
            (state.config_path, config_document),
            (state.profiles_path, profiles_document),
        ]
    )


def clone_state(state: AppState) -> AppState:
    return AppState(
        config_path=state.config_path,
        profiles_path=state.profiles_path,
        main_config=deepcopy(state.main_config),
        profiles=deepcopy(state.profiles),
        active_profile=state.active_profile,
    )


def build_config_document(state: AppState) -> str:
    return dumps_toml(state.main_config)


def build_profiles_document(state: AppState) -> str:
    return dumps_toml(
        {
            "version": PROFILE_VERSION,
            "active_profile": state.active_profile,
            "profiles": {name: profile.to_dict() for name, profile in state.profiles.items()},
        }
    )


def bootstrap_profiles(main_config: dict[str, Any]) -> dict[str, Profile]:
    profile = Profile(
        name=DEFAULT_PROFILE_NAME,
        label="Default",
        default_model=str(main_config.get("default_model", DEFAULTS["default_model"])),
        default_thinking=bool(
            main_config.get("default_thinking", DEFAULTS["default_thinking"])
        ),
        default_yolo=bool(main_config.get("default_yolo", DEFAULTS["default_yolo"])),
        default_plan_mode=bool(
            main_config.get("default_plan_mode", DEFAULTS["default_plan_mode"])
        ),
        default_editor=str(main_config.get("default_editor", DEFAULTS["default_editor"])),
        theme=str(main_config.get("theme", DEFAULTS["theme"])),
        show_thinking_stream=bool(
            main_config.get(
                "show_thinking_stream",
                DEFAULTS["show_thinking_stream"],
            )
        ),
        merge_all_available_skills=bool(
            main_config.get(
                "merge_all_available_skills",
                DEFAULTS["merge_all_available_skills"],
            )
        ),
    )
    return {profile.name: profile}


def apply_profile(state: AppState, profile_name: str) -> None:
    profile = state.profiles.get(profile_name)
    if profile is None:
        raise ValueError(f"Profile not found: {profile_name}")
    if profile.default_model not in state.main_config["models"]:
        raise ValueError(
            _format_missing_model_error(
                profile.default_model,
                state.main_config["models"],
                context=f"配置Profile {profile.name}",
            )
        )

    for key in PROFILE_KEYS:
        state.main_config[key] = getattr(profile, key)
    state.active_profile = profile_name


def upsert_provider(
    state: AppState,
    name: str,
    provider_type: str,
    base_url: str,
    api_key: str,
) -> None:
    state.main_config["providers"][name] = {
        "type": provider_type,
        "base_url": base_url,
        "api_key": api_key,
    }


def delete_provider(state: AppState, name: str) -> None:
    for model_name, model in state.main_config["models"].items():
        if str(model.get("provider")) == name:
            raise ValueError(
                f"Provider {name} is still used by model {model_name}."
            )
    state.main_config["providers"].pop(name, None)


def upsert_model(
    state: AppState,
    name: str,
    provider: str,
    model: str,
    max_context_size: int,
    capabilities: list[str],
) -> None:
    if provider not in state.main_config["providers"]:
        raise ValueError(f"Provider not found: {provider}")
    state.main_config["models"][name] = {
        "provider": provider,
        "model": model,
        "max_context_size": max_context_size,
        "capabilities": capabilities,
    }


def delete_model(state: AppState, name: str) -> None:
    for profile in state.profiles.values():
        if profile.default_model == name:
            raise ValueError(f"Model {name} is still used by profile {profile.name}.")
    if str(state.main_config.get("default_model", "")) == name:
        raise ValueError(f"Model {name} is still used as the current default model.")
    state.main_config["models"].pop(name, None)


def upsert_profile(
    state: AppState,
    name: str,
    label: str,
    default_model: str,
    default_thinking: bool,
    default_yolo: bool,
    default_plan_mode: bool,
    default_editor: str,
    theme: str,
    show_thinking_stream: bool,
    merge_all_available_skills: bool,
) -> None:
    if default_model not in state.main_config["models"]:
        raise ValueError(
            _format_missing_model_error(
                default_model,
                state.main_config["models"],
                context=f"配置Profile {name or '（未命名）'}",
            )
        )

    state.profiles[name] = Profile(
        name=name,
        label=label,
        default_model=default_model,
        default_thinking=default_thinking,
        default_yolo=default_yolo,
        default_plan_mode=default_plan_mode,
        default_editor=default_editor,
        theme=theme,
        show_thinking_stream=show_thinking_stream,
        merge_all_available_skills=merge_all_available_skills,
    )


def clone_profile(state: AppState, source_name: str, target_name: str, label: str) -> None:
    if source_name not in state.profiles:
        raise ValueError(f"Profile not found: {source_name}")
    if target_name in state.profiles:
        raise ValueError(f"Profile already exists: {target_name}")

    source = state.profiles[source_name]
    state.profiles[target_name] = Profile(
        name=target_name,
        label=label,
        default_model=source.default_model,
        default_thinking=source.default_thinking,
        default_yolo=source.default_yolo,
        default_plan_mode=source.default_plan_mode,
        default_editor=source.default_editor,
        theme=source.theme,
        show_thinking_stream=source.show_thinking_stream,
        merge_all_available_skills=source.merge_all_available_skills,
    )


def delete_profile(state: AppState, name: str) -> None:
    if name == state.active_profile:
        raise ValueError("Cannot delete the active profile.")
    if len(state.profiles) <= 1:
        raise ValueError("At least one profile is required.")
    state.profiles.pop(name, None)


def _normalize_main_config(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for key, value in DEFAULTS.items():
        normalized.setdefault(key, value)
    normalized.setdefault("hooks", [])
    normalized.setdefault("models", {})
    normalized.setdefault("providers", {})
    normalized.setdefault("loop_control", {})
    normalized.setdefault("background", {})
    normalized.setdefault("notifications", {})
    normalized.setdefault("services", {})
    normalized.setdefault("mcp", {})
    return normalized


def _pick_active_profile(
    main_config: dict[str, Any], profiles: dict[str, Profile]
) -> str:
    current_model = str(main_config.get("default_model", ""))
    for name, profile in profiles.items():
        if profile.default_model == current_model:
            matches = all(main_config.get(key) == getattr(profile, key) for key in PROFILE_KEYS)
            if matches:
                return name
    return next(iter(profiles), DEFAULT_PROFILE_NAME)


def _profile_from_dict(name: str, raw: dict[str, Any]) -> Profile:
    return Profile(
        name=name,
        label=str(raw.get("label", name)),
        default_model=str(raw.get("default_model", DEFAULTS["default_model"])),
        default_thinking=bool(raw.get("default_thinking", DEFAULTS["default_thinking"])),
        default_yolo=bool(raw.get("default_yolo", DEFAULTS["default_yolo"])),
        default_plan_mode=bool(raw.get("default_plan_mode", DEFAULTS["default_plan_mode"])),
        default_editor=str(raw.get("default_editor", DEFAULTS["default_editor"])),
        theme=str(raw.get("theme", DEFAULTS["theme"])),
        show_thinking_stream=bool(
            raw.get("show_thinking_stream", DEFAULTS["show_thinking_stream"])
        ),
        merge_all_available_skills=bool(
            raw.get(
                "merge_all_available_skills",
                DEFAULTS["merge_all_available_skills"],
            )
        ),
    )


def _ensure_active_profile(active_profile: str, profiles: dict[str, Profile]) -> str:
    if active_profile in profiles:
        return active_profile
    return next(iter(profiles), DEFAULT_PROFILE_NAME)


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return dict(data)


def _atomic_write_documents(documents: list[tuple[Path, str]]) -> None:
    temporary_paths: list[tuple[Path, Path]] = []
    replaced_paths: list[tuple[Path, Optional[Path]]] = []
    process_id = getpid()

    try:
        for index, (path, text) in enumerate(documents):
            temporary_path = path.with_name(f".{path.name}.{process_id}.{index}.tmp")
            temporary_path.write_text(text, encoding="utf-8")
            temporary_paths.append((path, temporary_path))

        for index, (path, temporary_path) in enumerate(temporary_paths):
            backup_path = None
            if path.exists():
                backup_path = path.with_name(f".{path.name}.{process_id}.{index}.bak")
                path.replace(backup_path)
            temporary_path.replace(path)
            replaced_paths.append((path, backup_path))
    except Exception:
        for path, backup_path in reversed(replaced_paths):
            if path.exists():
                path.unlink()
            if backup_path is not None and backup_path.exists():
                backup_path.replace(path)
        raise
    finally:
        for _, temporary_path in temporary_paths:
            if temporary_path.exists():
                temporary_path.unlink()
        for _, backup_path in replaced_paths:
            if backup_path is not None and backup_path.exists():
                backup_path.unlink()


def _format_missing_model_error(
    model_name: str,
    models: dict[str, Any],
    *,
    context: str,
) -> str:
    normalized_name = model_name or "（空）"
    model_keys = list(models.keys())
    if model_keys:
        preview = "、".join(model_keys[:3])
        if len(model_keys) > 3:
            preview = f"{preview} 等 {len(model_keys)} 个"
        available_hint = f"可用模型 key：{preview}。"
    else:
        available_hint = "当前还没有任何模型，请先在“模型”页创建模型。"

    return (
        f"{context}引用的默认模型不存在：{normalized_name}。"
        "这里需要填写 [models] 下的模型 key，不是 model 字段值。"
        f"{available_hint}"
        "请先创建对应模型，或把配置Profile默认模型改成现有模型。"
    )
