from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kimi_code_switch.__main__ import kimi_code_switch


if __name__ == "__main__":
    raise SystemExit(kimi_code_switch())
