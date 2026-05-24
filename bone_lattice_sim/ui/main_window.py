"""Главное окно приложения."""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from bone_lattice_sim.experiment import create_lattice, create_simulation
from bone_lattice_sim.io.settings import load_settings, save_settings
from bone_lattice_sim.simulation.stats import SimulationResult, StepStats
from bone_lattice_sim.ui.tabs.charts_tab import ChartsTab
from bone_lattice_sim.ui.tabs.config_tab import ConfigTab
from bone_lattice_sim.ui.tabs.viewer_tab import ViewerTab
from bone_lattice_sim.ui.worker import SimulationWorker
from bone_lattice_sim.viz.snapshot import build_visual_context, empty_snapshot


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Bone Lattice Simulator — 3D colonization")
        self.resize(1024, 780)

        self._worker: SimulationWorker | None = None
        self._last_result: SimulationResult | None = None
        self._visual_context = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        btn_row = QHBoxLayout()
        self.btn_run = QPushButton("Запустить симуляцию")
        self.btn_stop = QPushButton("Стоп")
        self.btn_stop.setEnabled(False)
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.tabs = QTabWidget()
        self.config_tab = ConfigTab()
        self.viewer_tab = ViewerTab()
        self.charts_tab = ChartsTab()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)

        self.tabs.addTab(self.config_tab, "Конфигурация")
        self.tabs.addTab(self.viewer_tab, "3D Viewer")
        self.tabs.addTab(self.charts_tab, "Графики")
        self.tabs.addTab(self.log, "Журнал")
        layout.addWidget(self.tabs)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Готово")

        self.config_tab.set_settings(load_settings())
        self.viewer_tab.set_preview_handler(self._preview_lattice)
        self.btn_run.clicked.connect(self._on_run)
        self.btn_stop.clicked.connect(self._on_stop)

    def _log(self, text: str) -> None:
        self.log.append(text)

    def _set_running(self, running: bool) -> None:
        self.btn_run.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.config_tab.setEnabled(not running)
        self.viewer_tab.btn_preview.setEnabled(not running)

    def _preview_lattice(self) -> None:
        """Построить решётку из настроек без запуска симуляции."""
        err = self.config_tab.validate_input()
        if err:
            QMessageBox.warning(self, "Проверьте параметры", err)
            return
        try:
            settings = self.config_tab.get_settings()
            lattice = create_lattice(settings)
            context = build_visual_context(lattice)
            snapshot = empty_snapshot(lattice.n_pores)
            self._visual_context = context
            self.viewer_tab.show_lattice(context, snapshot)
            self.tabs.setCurrentWidget(self.viewer_tab)
            self._log(
                f"Предпросмотр: {lattice.n_pores} пор, preset={lattice.meta.get('preset')}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Предпросмотр", str(exc))

    def _on_run(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        err = self.config_tab.validate_input()
        if err:
            QMessageBox.warning(self, "Проверьте параметры", err)
            return

        settings = self.config_tab.get_settings()
        save_settings(settings)
        self.charts_tab.reset()
        self.viewer_tab.clear()
        self._visual_context = None
        self._log("--- Запуск ---")
        self._set_running(True)
        self.status.showMessage("Симуляция выполняется...")

        self._worker = SimulationWorker(settings, self)
        self._worker.step_updated.connect(self._on_step)
        self._worker.lattice_info.connect(self._on_lattice_info)
        self._worker.visual_ready.connect(self._on_visual_ready)
        self._worker.visual_updated.connect(self._on_visual_updated)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.finished_summary.connect(self._on_summary)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.status.showMessage("Остановка...")
            self._log("Запрошена остановка")

    def _on_step(self, stats: StepStats) -> None:
        self.charts_tab.append_step(stats)
        self.status.showMessage(
            f"Шаг {stats.step}: занятость {stats.occupancy * 100:.1f}%, "
            f"клеток {stats.cell_count}",
        )

    def _on_lattice_info(self, text: str) -> None:
        self._log(text)

    def _on_visual_ready(self, context, snapshot) -> None:
        self._visual_context = context
        self.viewer_tab.show_lattice(context, snapshot)

    def _on_visual_updated(self, snapshot) -> None:
        if self._visual_context is not None:
            self.viewer_tab.update_snapshot(snapshot)

    def _on_finished(self, result: SimulationResult) -> None:
        self._last_result = result
        self.charts_tab.load_result(result)
        self.tabs.setCurrentWidget(self.viewer_tab)

    def _on_summary(self, text: str) -> None:
        self._log("Итог: " + text)
        self.status.showMessage(text)

    def _on_error(self, message: str) -> None:
        self._log("Ошибка: " + message)
        QMessageBox.critical(self, "Ошибка симуляции", message)

    def _on_worker_done(self) -> None:
        self._set_running(False)
        if self._worker is None:
            return
        if not self._worker.isRunning():
            self._worker.deleteLater()
        self._worker = None

    def closeEvent(self, event: QCloseEvent) -> None:
        save_settings(self.config_tab.get_settings())
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        super().closeEvent(event)
