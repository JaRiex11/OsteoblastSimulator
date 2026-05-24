"""Запуск PySide6 GUI."""

from __future__ import annotations

import sys


def launch_gui() -> None:
    from PySide6.QtWidgets import QApplication

    from bone_lattice_sim.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("BoneLatticeSimulator")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
