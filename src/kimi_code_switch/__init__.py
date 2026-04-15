"""kimi-code-cli config switcher."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys
import tomllib


PACKAGE_NAME = "kimi-code-switch"


def _bootstrap_vendor_path() -> None:
    project_root = Path(__file__).resolve().parents[2]
    vendor_path = project_root / ".vendor"
    if vendor_path.exists() and str(vendor_path) not in sys.path:
        sys.path.insert(0, str(vendor_path))


_bootstrap_vendor_path()


def _homebrew_cellar_version_from_path(path: Path) -> str | None:
    parts = path.parts
    for index, part in enumerate(parts):
        if part != "Cellar":
            continue
        if index + 2 >= len(parts):
            return None
        formula_name = parts[index + 1]
        formula_version = parts[index + 2]
        if formula_name == PACKAGE_NAME and formula_version:
            return formula_version
    return None


def _version_from_homebrew() -> str | None:
    executable = Path(sys.argv[0]).expanduser()
    try:
        resolved = executable.resolve()
    except OSError:
        resolved = executable
    return _homebrew_cellar_version_from_path(resolved)


def _version_from_metadata() -> str | None:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return None


def _version_from_pyproject() -> str | None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject.exists():
        return None
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    return str(data.get("project", {}).get("version", "")).strip() or None


def get_runtime_version() -> str:
    for resolver in (_version_from_homebrew, _version_from_metadata, _version_from_pyproject):
        detected = resolver()
        if detected:
            return detected
    return "unknown"


__version__ = get_runtime_version()
