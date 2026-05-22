#!/usr/bin/env python3
"""
Точка входа симулятора.

  Двойной щелчок / OsteoblastSimulator.exe  ->  окно GUI
  python run.py                               ->  GUI
  python run.py --help                        ->  командная строка
"""

from __future__ import annotations

import sys
from pathlib import Path

# Корень проекта в PYTHONPATH
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    frozen = getattr(sys, "frozen", False)
    # Без аргументов или .exe — только GUI
    if frozen or len(sys.argv) <= 1:
        from osteoblast_sim.app.gui import launch_gui
        launch_gui()
    else:
        from osteoblast_sim.app.cli import main as cli_main
        raise SystemExit(cli_main())


if __name__ == "__main__":
    main()
