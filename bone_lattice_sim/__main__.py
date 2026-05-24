"""python -m bone_lattice_sim — GUI по умолчанию, CLI при аргументах."""

from bone_lattice_sim.cli import main as cli_main
from bone_lattice_sim.ui.app import launch_gui
import sys


def main() -> None:
    if len(sys.argv) > 1:
        raise SystemExit(cli_main())
    launch_gui()


if __name__ == "__main__":
    main()
