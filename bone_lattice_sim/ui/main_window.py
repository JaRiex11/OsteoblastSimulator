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

from bone_lattice_sim.experiment import build_initial_from_settings, create_lattice, create_simulation
from bone_lattice_sim.io.settings import load_settings, save_settings
from bone_lattice_sim.io.run_bundle import SimulationRun
from bone_lattice_sim.simulation.stats import StepStats
from bone_lattice_sim.ui.tabs.charts_tab import ChartsTab
from bone_lattice_sim.ui.tabs.config_tab import ConfigTab
from bone_lattice_sim.ui.tabs.export_tab import ExportTab
from bone_lattice_sim.ui.tabs.viewer_tab import ViewerTab
from bone_lattice_sim.ui.worker import SimulationWorker
from bone_lattice_sim.viz.snapshot import build_visual_context, snapshot_from_initial


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Bone Lattice Simulator — 3D colonization")
        self.resize(1024, 780)

        self._worker: SimulationWorker | None = None
        self._last_run: SimulationRun | None = None
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
        self.export_tab = ExportTab()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)

        self.tabs.addTab(self.config_tab, "Конфигурация")
        self.tabs.addTab(self.viewer_tab, "3D Viewer")
        self.tabs.addTab(self.charts_tab, "Графики")
        self.tabs.addTab(self.export_tab, "Экспорт")
        self.tabs.addTab(self.log, "Журнал")
        layout.addWidget(self.tabs)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Готово")

        self.config_tab.set_settings(load_settings())
        self.export_tab.set_run(None)
        saved = load_settings()
        pct = int(saved.get("cell_radius_pct", 24))
        self.viewer_tab.viewer.set_cell_radius_factor(pct / 100.0)
        self.viewer_tab.sync_size_slider(pct / 100.0)
        self.viewer_tab.set_preview_handler(self._preview_lattice)
        self.export_tab.export_done.connect(self._on_export_done)
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
            initial = build_initial_from_settings(lattice, settings)
            context = build_visual_context(lattice)
            snapshot = snapshot_from_initial(lattice, initial)
            self._visual_context = context
            self.viewer_tab.show_lattice(context, snapshot)
            self.tabs.setCurrentWidget(self.viewer_tab)
            self._log(
                f"Предпросмотр: {lattice.n_pores} пор, стартовых клеток: {len(initial)}",
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
        settings["cell_radius_pct"] = self.viewer_tab.slider_size.value()
        save_settings(settings)
        self.charts_tab.reset()
        self.export_tab.set_run(None)
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
        self.viewer_tab.cache_simulation_frame(context, snapshot)
        if self.viewer_tab.live_3d_enabled():
            self.viewer_tab.show_lattice(context, snapshot, fast=True)

    def _on_visual_updated(self, snapshot) -> None:
        if self._visual_context is None:
            return
        self.viewer_tab.cache_simulation_frame(self._visual_context, snapshot)
        if not self.viewer_tab.live_3d_enabled():
            return
        if self.tabs.currentWidget() is not self.viewer_tab:
            return
        self.viewer_tab.update_snapshot(snapshot, fast=True)

    def _on_finished(self, run: SimulationRun) -> None:
        self._last_run = run
        self.charts_tab.load_result(run.result)
        self.export_tab.set_run(run)
        if self._visual_context is not None and run.animation_frames:
            self.viewer_tab.set_animation_frames(
                self._visual_context, run.animation_frames,
            )
            if run.animation_frames:
                last = run.animation_frames[-1]
                self.viewer_tab.show_lattice(
                    self._visual_context, last, reset_camera=False, fast=False,
                )
                self.viewer_tab.cache_simulation_frame(self._visual_context, last)
        self.tabs.setCurrentWidget(self.viewer_tab)

    def _on_summary(self, text: str) -> None:
        self._log("Итог: " + text)
        self.status.showMessage(text)

    def _on_export_done(self, folder: str) -> None:
        self._log(f"Экспорт: {folder}")
        self.status.showMessage(f"Экспорт сохранён: {folder}")

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
        data = self.config_tab.get_settings()
        data["cell_radius_pct"] = self.viewer_tab.slider_size.value()
        save_settings(data)
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        super().closeEvent(event)
