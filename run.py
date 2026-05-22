#!/usr/bin/env python3
"""
Точка входа симулятора.

Режимы запуска:
  - OsteoblastSimulator.exe или python run.py без аргументов → GUI;
  - python run.py --graph-type ... → командная строка для пакетных опытов.

Перед импортом пакета добавляем корень проекта в sys.path, чтобы
работало и из исходников, и из собранного exe.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    # PyInstaller помечает сборку флагом frozen
    frozen = getattr(sys, "frozen", False)

    # Обычному пользователю консоль не нужна — только окно настроек
    if frozen or len(sys.argv) <= 1:
        from osteoblast_sim.app.gui import launch_gui
        launch_gui()
    else:
        from osteoblast_sim.app.cli import main as cli_main
        raise SystemExit(cli_main())


if __name__ == "__main__":
    main()
