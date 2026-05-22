"""
Единые пути к файлам проекта.

Зачем: при запуске из .exe (PyInstaller) рабочая папка — каталог с exe,
а не папка с исходниками. Этот модуль определяет «корень» в обоих случаях,
чтобы output/ и gui_settings.json всегда лежали рядом с программой.
"""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """
    Корень проекта.

    Как: sys.frozen выставляется PyInstaller — тогда корень = папка exe.
    Иначе корень = родитель пакета osteoblast_sim (где лежит run.py).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


# Сюда складываются CSV и PNG из экспериментов
OUTPUT_DIR = project_root() / "output"


def ensure_output_dir() -> Path:
    """Создать output/, если её ещё нет, и вернуть путь."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR
