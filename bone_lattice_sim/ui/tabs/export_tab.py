"""Вкладка экспорта результатов симуляции."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from bone_lattice_sim.io.export import export_full_run
from bone_lattice_sim.io.run_bundle import SimulationRun
from bone_lattice_sim.paths import ensure_output_dir


class ExportTab(QWidget):
    """Кнопки экспорта после завершённого прогона."""

    export_done = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.lbl_status = QLabel(
            "После симуляции нажмите «Экспорт всего» — в папку output/run_… "
            "сохранятся CSV, JSON, VTK, PNG."
        )
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.btn_all = QPushButton("Экспорт всего (CSV + JSON + VTK + PNG)")
        self.btn_all.clicked.connect(self._export_all)
        layout.addWidget(self.btn_all)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(200)
        layout.addWidget(self.log)

        self._run: SimulationRun | None = None

    def set_run(self, run: SimulationRun | None) -> None:
        self._run = run
        if run is None:
            self.lbl_status.setText("Нет данных — сначала выполните симуляцию.")
            self.btn_all.setEnabled(False)
        else:
            self.lbl_status.setText(
                f"Готово к экспорту: {run.result.final_cell_count} клеток, "
                f"занятость {run.result.final_occupancy * 100:.1f}%."
            )
            self.btn_all.setEnabled(True)

    def _export_all(self) -> None:
        if self._run is None:
            QMessageBox.information(self, "Экспорт", "Сначала запустите симуляцию.")
            return
        try:
            paths = export_full_run(self._run)
            folder = paths["timeseries.csv"].parent
            lines = [f"Папка: {folder}", ""]
            for name, p in paths.items():
                lines.append(f"  {name}: {p.name}")
            text = "\n".join(lines)
            self.log.setPlainText(text)
            self.export_done.emit(str(folder))
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))
