"""Вкладка 3D viewer с элементами управления."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
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

        controls = QHBoxLayout()
        self.chk_throats = QCheckBox("Показывать throats")
        self.chk_throats.setChecked(True)
        self.chk_empty = QCheckBox("Показывать пустые поры")
        self.chk_empty.setChecked(False)
        self.chk_empty.setToolTip(
            "Серые сферы — свободные поры. Снимите галочку, чтобы видеть только клетки.",
        )
        self.btn_preview = QPushButton("Предпросмотр решётки")
        self.btn_png = QPushButton("Экспорт PNG")
        self.lbl_step = QLabel("Шаг: —")

        controls.addWidget(self.chk_throats)
        controls.addWidget(self.chk_empty)
        controls.addWidget(self.btn_preview)
        controls.addWidget(self.btn_png)
        controls.addStretch()
        controls.addWidget(self.lbl_step)
        root.addLayout(controls)

        self.lbl_legend = QLabel(VIEWER_LEGEND)
        self.lbl_legend.setWordWrap(True)
        root.addWidget(self.lbl_legend)

        self.viewer = LatticeViewer3D()
        root.addWidget(self.viewer, stretch=1)

        self.chk_throats.toggled.connect(self._on_options_changed)
        self.chk_empty.toggled.connect(self._on_options_changed)
        self._preview_callback = None
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_png.clicked.connect(self._on_export_png)

    def set_preview_handler(self, callback) -> None:
        """callback() — построить решётку из текущих настроек без симуляции."""
        self._preview_callback = callback

    def _on_options_changed(self) -> None:
        self.viewer.set_display_options(
            show_throats=self.chk_throats.isChecked(),
            show_empty=self.chk_empty.isChecked(),
        )

    def _on_preview(self) -> None:
        if self._preview_callback:
            self._preview_callback()

    def _on_export_png(self) -> None:
        out = ensure_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out / f"lattice_view_{ts}.png"
        self.viewer.export_png(path)
        self.lbl_step.setText(f"PNG: {path.name}")

    def clear(self) -> None:
        self.viewer.clear()
        self.lbl_step.setText("Шаг: —")

    def show_lattice(self, context: LatticeVisualContext, snapshot: VisualSnapshot) -> None:
        self.viewer.show_lattice(context, snapshot)
        n = self.viewer.occupied_count(snapshot)
        self.lbl_step.setText(f"Шаг: {snapshot.step} | занятых пор: {n}")

    def update_snapshot(self, snapshot: VisualSnapshot) -> None:
        self.viewer.update_snapshot(snapshot)
        n = self.viewer.occupied_count(snapshot)
        self.lbl_step.setText(f"Шаг: {snapshot.step} | занятых пор: {n}")
