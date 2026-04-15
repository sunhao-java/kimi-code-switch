from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config_store import load_state
from .tui import ConfigPanelApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kimi-config-panel",
        description="Terminal UI for kimi-code-cli config.toml",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("~/.kimi/config.toml").expanduser(),
        help="Path to kimi-code-cli config.toml",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=None,
        help="Optional profile sidecar path. Defaults to ~/.kimi/config.profiles.toml",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        state = load_state(args.config, args.profiles)
        app = ConfigPanelApp(state)
        app.run()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # pragma: no cover
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
