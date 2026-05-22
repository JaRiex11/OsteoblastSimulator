"""Пути проекта (работают и из исходников, и из .exe)."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Корень проекта: папка с run.py или каталог рядом с .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


OUTPUT_DIR = project_root() / "output"


def ensure_output_dir() -> Path:
    """Создать папку output при необходимости."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR
