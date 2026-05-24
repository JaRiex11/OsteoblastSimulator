#!/usr/bin/env python3
"""Точка входа для PyInstaller (BoneLatticeSimulator, --onedir)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    from bone_lattice_sim.ui.app import launch_gui
    launch_gui()


if __name__ == "__main__":
    main()
