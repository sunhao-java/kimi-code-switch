from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config_store import load_state
from .panel_settings import DEFAULT_PANEL_SETTINGS_PATH, load_panel_settings
from .tui import ConfigPanelApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kimi-config-switch",
        description="Terminal UI for kimi-code-cli config.toml",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to kimi-code-cli config.toml",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=None,
        help="Optional profile sidecar path. Defaults to ~/.kimi/config.profiles.toml",
    )
    parser.add_argument(
        "--panel-settings",
        type=Path,
        default=DEFAULT_PANEL_SETTINGS_PATH,
        help="Path to kimi-config-switch settings sidecar",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        panel_settings = load_panel_settings(args.panel_settings)
        config_path = args.config.expanduser() if args.config is not None else panel_settings.resolved_config_path()
        profiles_path = (
            args.profiles.expanduser()
            if args.profiles is not None
            else panel_settings.explicit_profiles_path()
        )
        state = load_state(config_path, profiles_path)
        app = ConfigPanelApp(state, panel_settings)
        app.run()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # pragma: no cover
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
