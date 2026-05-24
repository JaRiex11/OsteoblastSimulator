#!/usr/bin/env python3
"""
Точка входа проекта.

  python run.py              — legacy 2D GUI (osteoblast_sim)
  python run.py --bone       — новый 3D CLI (bone_lattice_sim, Спринт 1)
  python -m bone_lattice_sim — то же, что --bone
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--bone":
        from bone_lattice_sim.cli import main as bone_main
        raise SystemExit(bone_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--legacy":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from osteoblast_sim.app.cli import main as cli_main
        raise SystemExit(cli_main())

    frozen = getattr(sys, "frozen", False)
    if frozen or len(sys.argv) <= 1:
        from osteoblast_sim.app.gui import launch_gui
        launch_gui()
    else:
        from osteoblast_sim.app.cli import main as cli_main
        raise SystemExit(cli_main())


if __name__ == "__main__":
    main()
