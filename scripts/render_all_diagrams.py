# -*- coding: utf-8 -*-
"""Пересборка всех UML-диаграмм классов."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    for name in ("render_planning_diagram.py", "render_actual_diagram.py"):
        script = ROOT / name
        print(f"=== {name} ===")
        subprocess.run([sys.executable, str(script)], check=True)


if __name__ == "__main__":
    main()
