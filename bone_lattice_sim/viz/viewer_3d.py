"""
3D-визуализация поровой сети (PyVista + pyvistaqt).

Клетки — отдельные непрозрачные сферы (корректная глубина) с wireframe-контуром.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from bone_lattice_sim.viz.snapshot import LatticeVisualContext, VisualSnapshot

COLORS = {
    -1: "#b0b0b8",
    0: "#2ecc71",
    1: "#3498db",
    2: "#e74c3c",
}

RIM_COLOR = "#14141e"
RIM_SCALE = 1.04
SPHERE_RES = 14
OUTLINE_RES = 10


def _estimate_spacing(coords: np.ndarray) -> float:
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


def _sphere_at(
    center: np.ndarray,
    radius: float,
    *,
    theta_resolution: int = SPHERE_RES,
    phi_resolution: int | None = None,
) -> pv.PolyData:
    phi_resolution = phi_resolution if phi_resolution is not None else theta_resolution
    return pv.Sphere(
        radius=radius,
        center=center,
        theta_resolution=theta_resolution,
        phi_resolution=phi_resolution,
    )


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
        self._last_snapshot: VisualSnapshot | None = None
        self._show_throats = True
        self._show_empty = False
        self._base_spacing = 1.0
        self._cell_radius_factor = 0.24
        self._dynamic_actors: list[str] = []
        self._reset_camera_next = True

    @property
    def cell_radius_factor(self) -> float:
        return self._cell_radius_factor

    def set_cell_radius_factor(self, factor: float) -> None:
        self._cell_radius_factor = min(0.48, max(0.06, factor))

    def occupied_radius(self) -> float:
        return self._base_spacing * self._cell_radius_factor

    def empty_radius(self) -> float:
        return self._base_spacing * self._cell_radius_factor * 0.45

    def set_display_options(self, *, show_throats: bool, show_empty: bool) -> None:
        self._show_throats = show_throats
        self._show_empty = show_empty
        self.refresh(reset_camera=False)

    def clear(self) -> None:
        self.plotter.clear()
        self._context = None
        self._last_snapshot = None
        self._dynamic_actors.clear()
        self._reset_camera_next = True

    def show_lattice(
        self,
        context: LatticeVisualContext,
        snapshot: VisualSnapshot,
        *,
        reset_camera: bool = True,
    ) -> None:
        self._context = context
        self._last_snapshot = snapshot
        self._base_spacing = _estimate_spacing(context.coords)
        self._reset_camera_next = reset_camera
        self.refresh(reset_camera=reset_camera)

    def refresh(self, *, reset_camera: bool | None = None) -> None:
        if self._context is None or self._last_snapshot is None:
            return
        if reset_camera is None:
            reset_camera = self._reset_camera_next
        self.plotter.clear()
        self._dynamic_actors.clear()
        self._draw_throats(self._context)
        self._draw_pores(self._context, self._last_snapshot)
        if reset_camera:
            self.plotter.reset_camera()
            self._reset_camera_next = False
        self.plotter.render()

    def update_snapshot(self, snapshot: VisualSnapshot) -> None:
        if self._context is None:
            return
        self._last_snapshot = snapshot
        self.refresh(reset_camera=False)

    def _track_actor(self, name: str) -> None:
        self._dynamic_actors.append(name)

    def _draw_throats(self, context: LatticeVisualContext) -> None:
        if not self._show_throats:
            return
        mesh = _throat_lines_mesh(context.coords, context.edges)
        self.plotter.add_mesh(
            mesh,
            name="throats",
            color="#666680",
            line_width=1.5,
            opacity=0.35,
            render_lines_as_tubes=True,
        )
        self._track_actor("throats")

    def _add_cell_sphere(
        self,
        center: np.ndarray,
        radius: float,
        color: str,
        name: str,
        *,
        with_rim: bool,
    ) -> None:
        core = _sphere_at(center, radius)
        self.plotter.add_mesh(
            core,
            name=f"{name}_core",
            color=color,
            opacity=1.0,
            smooth_shading=True,
            lighting=True,
            specular=0.35,
            specular_power=18,
            ambient=0.22,
            diffuse=0.78,
        )
        self._track_actor(f"{name}_core")

        if with_rim:
            outline = _sphere_at(
                center,
                radius * RIM_SCALE,
                theta_resolution=OUTLINE_RES,
                phi_resolution=OUTLINE_RES,
            )
            self.plotter.add_mesh(
                outline,
                name=f"{name}_rim",
                style="wireframe",
                color=RIM_COLOR,
                line_width=1.6,
                opacity=1.0,
                lighting=False,
            )
            self._track_actor(f"{name}_rim")

    def _draw_cells_individual(
        self,
        pts: np.ndarray,
        radius: float,
        color: str,
        prefix: str,
        *,
        with_rim: bool,
    ) -> None:
        for i, pt in enumerate(pts):
            self._add_cell_sphere(pt, radius, color, f"{prefix}_{i}", with_rim=with_rim)

    def _draw_pores(self, context: LatticeVisualContext, snapshot: VisualSnapshot) -> None:
        codes = snapshot.pore_types
        r_occ = self.occupied_radius()
        r_empty = self.empty_radius()

        groups = [
            (-1, "empty", r_empty, self._show_empty, False),
            (0, "ob", r_occ, True, True),
            (1, "msc", r_occ, True, True),
            (2, "fib", r_occ, True, True),
        ]
        for code, prefix, radius, enabled, with_rim in groups:
            if not enabled:
                continue
            idx = np.where(codes == code)[0]
            if len(idx) == 0:
                continue
            pts = context.coords[idx]
            self._draw_cells_individual(pts, radius, COLORS[code], prefix, with_rim=with_rim)

    def occupied_count(self, snapshot: VisualSnapshot) -> int:
        return int(np.sum(snapshot.pore_types >= 0))

    def export_png(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.plotter.screenshot(str(path))
