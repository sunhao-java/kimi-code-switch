# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`kimi-code-switch` is a Textual-based terminal UI for managing `kimi-code-cli` configuration: providers, models, and profile switching. It manages three TOML files under `~/.kimi/`: `config.toml` (active config), `config.profiles.toml` (profile definitions), and `config.panel.toml` (panel settings).

## Commands

```bash
# Run the app (dev mode, no install needed)
python3 kimi-code-switch.py

# Install as editable package
python3 -m pip install -e .

# Run all tests
python3 -m unittest tests.test_config_store

# Run a single test
python3 -m unittest tests.test_config_store.ConfigStoreTests.test_name_here
```

No linting or type-checking tools are configured. Tests use standard `unittest` and Textual's async `Pilot` for TUI interaction tests.

## Architecture

**Entry points:**
- `kimi-code-switch.py` — dev shortcut that imports and runs `__main__`
- `src/kimi_code_switch/__main__.py` — CLI entry with argparse, builds `AppState` and launches `ConfigPanelApp`

**Core data flow:** TOML files → `config_store.load_state()` → `AppState` (in-memory) → `tui.py` renders it → user edits → `save_state()` → atomic TOML write back

**Key modules:**

| Module | Role |
|--------|------|
| `config_store.py` | Data model (`AppState`, `Profile`), CRUD operations, atomic file I/O, delete-protection guards |
| `tui.py` | Textual `App` (~1600 lines), all widgets, keyboard navigation, theme system, preview/diff |
| `panel_settings.py` | Panel-level settings (theme, shortcut scheme, config path), separate from main config |
| `toml_utils.py` | Custom TOML serializer preserving readable formatting (sorted keys, blank lines between sections) |
| `_toml.py` | TOML reader shim: `tomllib` (3.11+) or `tomli` (3.9/3.10) |
| `__init__.py` | Vendor path bootstrap (`sys.path.insert` for `.vendor/`), version resolution chain |

**Config model:**
- `AppState` holds `main_config` (raw dict from `config.toml`) and `profiles` (dict of `Profile` dataclasses)
- `PROFILE_KEYS` tuple lists which fields profiles can override in the main config
- Applying a profile copies its `PROFILE_KEYS` values into `main_config` and sets `active_profile`
- Model names in config use `{provider}/{model}` composite keys (e.g. `kimi_gateway/kimi-k2.5`)

## Coding Conventions

- **Python 3.9+** — use `dict[str, Any]` generics, `Optional[X]` not `X | None`, no `slots=True` on dataclasses
- **Import order:** `__future__` → stdlib → third-party → local (all with explicit `from __future__ import annotations`)
- **TUI styling:** CSS strings defined as class-level `CSS` attribute on each widget
- **TUI messages:** custom events inherit `Message` class
- **Keyboard bindings:** defined via `Binding` in `BINDINGS` lists
- **Atomic writes:** `config_store._atomic_write_documents()` writes via temp+rename with rollback

## Key Design Patterns

- **Delete protection:** providers can't be deleted while models reference them; models can't be deleted while profiles reference them; active profile can't be deleted; at least one profile must exist
- **Model key convention:** the `[models]` table key is `{provider_name}/{model_suffix}`, but the form input only takes the suffix — the provider dropdown supplies the prefix
- **Profile bootstrap:** if no `config.profiles.toml` exists, a `default` profile is created from the current `config.toml` values
- **Version detection chain:** Homebrew Cellar path → package metadata → pyproject.toml → "unknown"

## Homebrew Release

Push a `vX.Y.Z` tag to trigger `.github/workflows/release-homebrew.yml`, which builds macOS binaries (amd64/arm64), creates a GitHub Release, and pushes a formula to the `sunhao-java/homebrew-kimi-code-switch` tap.
