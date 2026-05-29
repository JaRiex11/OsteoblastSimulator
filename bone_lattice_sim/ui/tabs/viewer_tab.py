"""Вкладка 3D viewer с элементами управления."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from bone_lattice_sim.paths import ensure_output_dir
from bone_lattice_sim.ui.help_text import VIEWER_LEGEND
from bone_lattice_sim.viz.snapshot import LatticeVisualContext, VisualSnapshot
from bone_lattice_sim.viz.viewer_3d import LatticeViewer3D


class ViewerTab(QWidget):
    """3D визуализация + опции отображения и экспорт PNG."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)

        row1 = QHBoxLayout()
        self.chk_throats = QCheckBox("Throats")
        self.chk_throats.setChecked(True)
        self.chk_empty = QCheckBox("Пустые поры")
        self.chk_empty.setChecked(False)
        self.chk_empty.setToolTip("Серые сферы — свободные поры.")
        self.btn_preview = QPushButton("Предпросмотр (стартовые клетки)")
        self.btn_restore = QPushButton("Последний кадр симуляции")
        self.btn_restore.setEnabled(False)
        self.btn_restore.setToolTip(
            "Вернуть отображение после последнего прогона (если был предпросмотр).",
        )
        self.btn_png = QPushButton("Экспорт PNG")
        row1.addWidget(self.chk_throats)
        row1.addWidget(self.chk_empty)
        row1.addWidget(self.btn_preview)
        row1.addWidget(self.btn_restore)
        row1.addWidget(self.btn_png)
        row1.addStretch()
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Размер клеток:"))
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(6, 42)
        self.slider_size.setValue(24)
        self.slider_size.setToolTip(
            "Радиус сферы клетки относительно шага сетки (6–42%). "
            "Уменьшите, если сферы сливаются.",
        )
        self.lbl_size = QLabel("24%")
        self.lbl_size.setMinimumWidth(36)
        row2.addWidget(self.slider_size, stretch=1)
        row2.addWidget(self.lbl_size)
        self.lbl_step = QLabel("Шаг: —")
        row2.addWidget(self.lbl_step)
        root.addLayout(row2)

        row_anim = QHBoxLayout()
        self.chk_live_3d = QCheckBox("Живое 3D во время симуляции")
        self.chk_live_3d.setChecked(True)
        self.chk_live_3d.setToolTip(
            "Перерисовка 3D по ходу прогона (интервал — «3D каждые K» в конфигурации). "
            "Работает только пока открыта эта вкладка. Снять галочку — обновление в конце.",
        )
        self.btn_anim_play = QPushButton("▶ Анимация")
        self.btn_anim_play.setEnabled(False)
        self.btn_anim_stop = QPushButton("■ Стоп")
        self.btn_anim_stop.setEnabled(False)
        self.slider_anim = QSlider(Qt.Orientation.Horizontal)
        self.slider_anim.setEnabled(False)
        self.slider_anim.setToolTip("Позиция кадра анимации")
        self.lbl_anim = QLabel("Кадр: —")
        row_anim.addWidget(self.chk_live_3d)
        row_anim.addWidget(self.btn_anim_play)
        row_anim.addWidget(self.btn_anim_stop)
        row_anim.addWidget(self.slider_anim, stretch=1)
        row_anim.addWidget(self.lbl_anim)
        root.addLayout(row_anim)

        self.lbl_legend = QLabel(VIEWER_LEGEND)
        self.lbl_legend.setWordWrap(True)
        root.addWidget(self.lbl_legend)

        self.viewer = LatticeViewer3D()
        self.viewer.set_cell_radius_factor(0.24)
        root.addWidget(self.viewer, stretch=1)

        self._preview_callback = None
        self._sim_cache: tuple[LatticeVisualContext, VisualSnapshot] | None = None
        self._anim_context: LatticeVisualContext | None = None
        self._anim_frames: list[VisualSnapshot] = []
        self._anim_index = 0
        self._anim_scene_ready = False
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self.chk_throats.toggled.connect(self._on_options_changed)
        self.chk_empty.toggled.connect(self._on_options_changed)
        self.slider_size.valueChanged.connect(self._on_size_changed)
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_restore.clicked.connect(self._on_restore)
        self.btn_png.clicked.connect(self._on_export_png)
        self.btn_anim_play.clicked.connect(self._start_animation)
        self.btn_anim_stop.clicked.connect(self._stop_animation)
        self.slider_anim.valueChanged.connect(self._on_anim_slider)

    def set_preview_handler(self, callback) -> None:
        self._preview_callback = callback

    def cache_simulation_frame(
        self, context: LatticeVisualContext, snapshot: VisualSnapshot,
    ) -> None:
        """Сохранить кадр симуляции для кнопки «Последний кадр»."""
        if self.viewer.occupied_count(snapshot) > 0:
            self._sim_cache = (context, snapshot)
            self.btn_restore.setEnabled(True)

    def _on_size_changed(self, value: int) -> None:
        self.lbl_size.setText(f"{value}%")
        self.viewer.set_cell_radius_factor(value / 100.0)
        self.viewer.refresh_cells()

    def _on_options_changed(self) -> None:
        self.viewer.set_display_options(
            show_throats=self.chk_throats.isChecked(),
            show_empty=self.chk_empty.isChecked(),
        )

    def _on_preview(self) -> None:
        if self._preview_callback:
            self._preview_callback()

    def _on_restore(self) -> None:
        if self._sim_cache is None:
            return
        context, snapshot = self._sim_cache
        self.show_lattice(context, snapshot, reset_camera=False)

    def _on_export_png(self) -> None:
        out = ensure_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out / f"lattice_view_{ts}.png"
        self.viewer.export_png(path)
        self.lbl_step.setText(f"PNG: {path.name}")

    def clear(self) -> None:
        self._stop_animation()
        self._anim_frames.clear()
        self._anim_context = None
        self._anim_scene_ready = False
        self._setup_animation_controls()
        self.viewer.clear()
        self.lbl_step.setText("Шаг: —")

    def set_animation_frames(
        self,
        context: LatticeVisualContext | None,
        frames: list[VisualSnapshot],
    ) -> None:
        self._anim_context = context
        self._anim_frames = list(frames)
        self._anim_scene_ready = self.viewer.has_lattice_context
        self._setup_animation_controls()

    def _setup_animation_controls(self) -> None:
        n = len(self._anim_frames)
        enabled = n > 1 and self._anim_context is not None
        self.btn_anim_play.setEnabled(enabled)
        self.btn_anim_stop.setEnabled(False)
        self.slider_anim.setEnabled(enabled)
        if enabled:
            self.slider_anim.blockSignals(True)
            self.slider_anim.setRange(0, n - 1)
            self.slider_anim.setValue(0)
            self.slider_anim.blockSignals(False)
            self.lbl_anim.setText(f"Кадр: 0 / {n - 1}")
        else:
            self.lbl_anim.setText("Кадр: —")

    def live_3d_enabled(self) -> bool:
        return self.chk_live_3d.isChecked()

    def _ensure_anim_scene(self) -> None:
        """Один раз строим throats и фиксируем камеру; дальше только update_snapshot."""
        if self._anim_scene_ready or not self._anim_frames or self._anim_context is None:
            return
        self.show_lattice(
            self._anim_context,
            self._anim_frames[0],
            reset_camera=True,
            fast=True,
        )
        self._anim_scene_ready = True

    def _start_animation(self) -> None:
        if not self._anim_frames or self._anim_context is None:
            return
        self._ensure_anim_scene()
        self._anim_index = self.slider_anim.value()
        self._anim_timer.start(150)
        self.btn_anim_play.setEnabled(False)
        self.btn_anim_stop.setEnabled(True)

    def _stop_animation(self) -> None:
        self._anim_timer.stop()
        self._setup_animation_controls()

    def _on_anim_tick(self) -> None:
        if not self._anim_frames or self._anim_context is None:
            self._stop_animation()
            return
        if self._anim_index >= len(self._anim_frames) - 1:
            self._stop_animation()
            return
        self._anim_index += 1
        self.slider_anim.blockSignals(True)
        self.slider_anim.setValue(self._anim_index)
        self.slider_anim.blockSignals(False)
        self._show_anim_frame(self._anim_index)

    def _on_anim_slider(self, value: int) -> None:
        if not self._anim_frames or self._anim_context is None:
            return
        self._anim_index = value
        self._show_anim_frame(value)

    def _show_anim_frame(self, index: int) -> None:
        if self._anim_context is None:
            return
        snap = self._anim_frames[index]
        self.viewer.set_fast_mode(True)
        if not self._anim_scene_ready:
            self.show_lattice(self._anim_context, snap, reset_camera=True, fast=True)
            self._anim_scene_ready = True
        else:
            self.viewer.update_snapshot(snap)
        n = self.viewer.occupied_count(snap)
        self.lbl_step.setText(f"Анимация шаг {snap.step} | занятых пор: {n}")
        self.lbl_anim.setText(f"Кадр: {index} / {len(self._anim_frames) - 1}")

    def show_lattice(
        self,
        context: LatticeVisualContext,
        snapshot: VisualSnapshot,
        *,
        reset_camera: bool = True,
        fast: bool = False,
    ) -> None:
        self.viewer.set_fast_mode(fast)
        self.viewer.show_lattice(context, snapshot, reset_camera=reset_camera)
        n = self.viewer.occupied_count(snapshot)
        self.lbl_step.setText(f"Шаг: {snapshot.step} | занятых пор: {n}")

    def update_snapshot(self, snapshot: VisualSnapshot, *, fast: bool = True) -> None:
        self.viewer.set_fast_mode(fast)
        self.viewer.update_snapshot(snapshot)
        n = self.viewer.occupied_count(snapshot)
        self.lbl_step.setText(f"Шаг: {snapshot.step} | занятых пор: {n}")

    def sync_size_slider(self, factor: float) -> None:
        pct = int(round(factor * 100))
        pct = max(6, min(42, pct))
        self.slider_size.blockSignals(True)
        self.slider_size.setValue(pct)
        self.slider_size.blockSignals(False)
        self.lbl_size.setText(f"{pct}%")
