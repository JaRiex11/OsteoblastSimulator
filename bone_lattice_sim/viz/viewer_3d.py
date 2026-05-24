"""
3D-визуализация поровой сети (PyVista + pyvistaqt).

Клетки — сферы (glyph) в мировых координатах; throats — линии.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from bone_lattice_sim.viz.snapshot import LatticeVisualContext, VisualSnapshot

# Имена типов для легенды
TYPE_LABELS = {
    -1: "Пустая пора",
    0: "Osteoblast",
    1: "MSC",
    2: "Fibroblast",
}

COLORS = {
    -1: "#b0b0b8",
    0: "#2ecc71",
    1: "#3498db",
    2: "#e74c3c",
}


def _estimate_spacing(coords: np.ndarray) -> float:
    """Среднее расстояние между соседними центрами пор."""
    if len(coords) < 2:
        return 1.0
    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(coords)
        dists, _ = tree.query(coords, k=2)
        return float(np.median(dists[:, 1]))
    except Exception:
        span = float(np.max(np.ptp(coords, axis=0)))
        n = max(2, int(round(len(coords) ** (1.0 / 3.0))))
        return span / (n - 1) if n > 1 else 1.0


def _sphere_mesh(points: np.ndarray, radius: float) -> pv.PolyData | None:
    if len(points) == 0:
        return None
    cloud = pv.PolyData(points)
    geom = pv.Sphere(radius=radius, theta_resolution=14, phi_resolution=14)
    return cloud.glyph(geom=geom, scale=False)


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
        self._r_occ = 0.35
        self._r_empty = 0.12

    def set_display_options(self, *, show_throats: bool, show_empty: bool) -> None:
        self._show_throats = show_throats
        self._show_empty = show_empty
        if self._context is not None and self._last_snapshot is not None:
            self.show_lattice(self._context, self._last_snapshot)

    def clear(self) -> None:
        self.plotter.clear()
        self._context = None
        self._last_snapshot = None

    def show_lattice(self, context: LatticeVisualContext, snapshot: VisualSnapshot) -> None:
        self._context = context
        self._last_snapshot = snapshot
        spacing = _estimate_spacing(context.coords)
        self._r_occ = spacing * 0.42
        self._r_empty = spacing * 0.14

        self.plotter.clear()
        self._draw_throats(context)
        self._draw_pores(context, snapshot)
        self.plotter.reset_camera()
        self.plotter.render()

    def update_snapshot(self, snapshot: VisualSnapshot) -> None:
        if self._context is None:
            return
        self._last_snapshot = snapshot
        self._remove_pore_actors()
        self._draw_pores(self._context, snapshot)
        self.plotter.render()

    def _remove_pore_actors(self) -> None:
        for name in ("pores_empty", "pores_ob", "pores_msc", "pores_fib"):
            try:
                self.plotter.remove_actor(name, reset_camera=False, render=False)
            except (KeyError, ValueError, TypeError):
                pass

    def _draw_throats(self, context: LatticeVisualContext) -> None:
        if not self._show_throats:
            return
        mesh = _throat_lines_mesh(context.coords, context.edges)
        self.plotter.add_mesh(
            mesh,
            name="throats",
            color="#666680",
            line_width=2,
            opacity=0.45,
            render_lines_as_tubes=True,
        )

    def _draw_pores(self, context: LatticeVisualContext, snapshot: VisualSnapshot) -> None:
        codes = snapshot.pore_types
        groups = [
            (-1, "pores_empty", self._r_empty, self._show_empty),
            (0, "pores_ob", self._r_occ, True),
            (1, "pores_msc", self._r_occ, True),
            (2, "pores_fib", self._r_occ, True),
        ]
        for code, name, radius, enabled in groups:
            if not enabled:
                continue
            idx = np.where(codes == code)[0]
            if len(idx) == 0:
                continue
            pts = context.coords[idx]
            mesh = _sphere_mesh(pts, radius)
            if mesh is None:
                continue
            opacity = 0.35 if code < 0 else 0.95
            self.plotter.add_mesh(
                mesh,
                name=name,
                color=COLORS[code],
                opacity=opacity,
                smooth_shading=True,
            )

    def occupied_count(self, snapshot: VisualSnapshot) -> int:
        return int(np.sum(snapshot.pore_types >= 0))

    def export_png(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.plotter.screenshot(str(path))
