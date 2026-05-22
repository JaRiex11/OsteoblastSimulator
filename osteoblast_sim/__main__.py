"""Запуск: python -m osteoblast_sim (из корня проекта)."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from run import main  # noqa: E402

if __name__ == "__main__":
    main()
