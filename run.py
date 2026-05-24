#!/usr/bin/env python3
"""
Точка входа проекта.

  python run.py --bone           — 3D GUI (bone_lattice_sim)
  python run.py --bone --cli ... — 3D CLI
  python run.py                  — legacy 2D GUI (osteoblast_sim)
  python -m bone_lattice_sim     — 3D GUI
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--bone":
        args = sys.argv[2:]
        if args and args[0] == "--cli":
            from bone_lattice_sim.cli import main as bone_main
            raise SystemExit(bone_main(args[1:]))
        from bone_lattice_sim.ui.app import launch_gui
        launch_gui()
        return

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
