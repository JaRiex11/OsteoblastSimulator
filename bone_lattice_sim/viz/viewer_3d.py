"""
3D-визуализация поровой сети (PyVista + pyvistaqt).

Поры — точки/сферы с цветом по типу клетки; throats — линии (опционально).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from bone_lattice_sim.viz.snapshot import LatticeVisualContext, VisualSnapshot

# RGB 0..1
COLORS = {
    -1: (0.82, 0.82, 0.85),   # пустая пора
    0: (0.18, 0.75, 0.35),    # osteoblast
    1: (0.25, 0.55, 0.95),    # MSC
    2: (0.92, 0.30, 0.28),    # fibroblast
}

POINT_SIZE_EMPTY = 6.0
POINT_SIZE_OCCUPIED = 14.0


def _rgb_array(codes: np.ndarray) -> np.ndarray:
    out = np.zeros((len(codes), 3), dtype=np.float32)
    for code, rgb in COLORS.items():
        mask = codes == code
        out[mask] = rgb
    return out


def _throat_lines_mesh(coords: np.ndarray, edges: np.ndarray) -> pv.PolyData:
    if edges.size == 0:
        return pv.PolyData(coords)
    cells = np.hstack([np.full((len(edges), 1), 2, dtype=np.int64), edges]).ravel()
    return pv.PolyData(coords, lines=cells)


class LatticeViewer3D(QWidget):
    """Интерактивный 3D viewer внутри PyQt."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter)
        self.plotter.set_background("#1e1e2e")

        self._context: LatticeVisualContext | None = None
        self._show_throats = True
        self._show_empty = True
        self._last_snapshot: VisualSnapshot | None = None

    def set_display_options(self, *, show_throats: bool, show_empty: bool) -> None:
        self._show_throats = show_throats
        self._show_empty = show_empty
        if self._context is not None and self._last_snapshot is not None:
            self.update_snapshot(self._last_snapshot)

    def clear(self) -> None:
        self.plotter.clear()
        self._context = None
        self._last_snapshot = None

    def show_lattice(self, context: LatticeVisualContext, snapshot: VisualSnapshot) -> None:
        self._context = context
        self._last_snapshot = snapshot
        self.plotter.clear()
        self._draw_throats(context)
        self._draw_pores(context, snapshot)
        self.plotter.reset_camera()
        self.plotter.render()

    def update_snapshot(self, snapshot: VisualSnapshot) -> None:
        if self._context is None:
            return
        self._last_snapshot = snapshot
        try:
            self.plotter.remove_actor("pores", reset_camera=False, render=False)
        except (KeyError, ValueError):
            pass
        self._draw_pores(self._context, snapshot)
        self.plotter.render()

    def _draw_throats(self, context: LatticeVisualContext) -> None:
        if not self._show_throats:
            return
        mesh = _throat_lines_mesh(context.coords, context.edges)
        self.plotter.add_mesh(
            mesh,
            name="throats",
            color="#555566",
            line_width=1,
            opacity=0.35,
            render_lines_as_tubes=False,
        )

    def _draw_pores(self, context: LatticeVisualContext, snapshot: VisualSnapshot) -> None:
        codes = snapshot.pore_types
        mask = np.ones(len(codes), dtype=bool)
        if not self._show_empty:
            mask = codes >= 0

        if not np.any(mask):
            return

        idx = np.where(mask)[0]
        pts = context.coords[idx]
        sel_codes = codes[idx]
        rgb = _rgb_array(sel_codes)

        cloud = pv.PolyData(pts)
        cloud["rgb"] = rgb
        sizes = np.where(sel_codes < 0, POINT_SIZE_EMPTY, POINT_SIZE_OCCUPIED).astype(float)
        cloud["point_size"] = sizes

        self.plotter.add_mesh(
            cloud,
            name="pores",
            scalars="rgb",
            rgb=True,
            render_points_as_spheres=True,
            point_size=10,
            opacity=0.95 if self._show_empty else 1.0,
        )

    def export_png(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.plotter.screenshot(str(path))
