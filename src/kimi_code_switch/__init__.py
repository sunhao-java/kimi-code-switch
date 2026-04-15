"""kimi-code-cli config switcher."""

from __future__ import annotations

from pathlib import Path
import sys


def _bootstrap_vendor_path() -> None:
    project_root = Path(__file__).resolve().parents[2]
    vendor_path = project_root / ".vendor"
    if vendor_path.exists() and str(vendor_path) not in sys.path:
        sys.path.insert(0, str(vendor_path))


_bootstrap_vendor_path()
