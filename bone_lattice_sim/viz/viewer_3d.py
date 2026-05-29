"""
3D-визуализация поровой сети (PyVista + pyvistaqt).

Оптимизация: throats рисуются один раз; клетки — glyph-пакетами (не N отдельных actors).
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

CELL_ACTOR_NAMES = ("cells_empty", "cells_ob", "cells_msc", "cells_fib")

# Тип: ((pos), (focal), (view_up))
CameraPosition = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]


def _estimate_spacing(coords: np.ndarray) -> float:
    if len(coords) < 2:
        return 1.0
    diffs = coords[:, None, :] - coords[None, :, :]
    dists = np.linalg.norm(diffs, axis=2)
    np.fill_diagonal(dists, np.inf)
    nearest = np.min(dists, axis=1)
    positive = nearest[nearest > 1e-9]
    if len(positive) > 0:
        return float(np.median(positive))
    span = float(np.max(np.ptp(coords, axis=0)))
    n = max(2, int(round(len(coords) ** (1.0 / 3.0))))
    return span / (n - 1) if n > 1 else 1.0


def _throat_lines_mesh(coords: np.ndarray, edges: np.ndarray) -> pv.PolyData:
    if edges.size == 0:
        return pv.PolyData(coords)
    cells = np.hstack([np.full((len(edges), 1), 2, dtype=np.int64), edges]).ravel()
    return pv.PolyData(coords, lines=cells)


def _fixed_clipping_from_coords(coords: np.ndarray, spacing: float, radius_factor: float) -> tuple[float, float]:
    """Clipping по bbox всей решётки, не по текущих клетках (убирает «пульсацию» кадров)."""
    pad = spacing * (radius_factor + 1.0)
    mins = coords.min(axis=0) - pad
    maxs = coords.max(axis=0) + pad
    diagonal = float(np.linalg.norm(maxs - mins))
    near = max(diagonal * 0.02, 1e-3)
    far = max(diagonal * 4.0, near + 1.0)
    return near, far


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
        self._throats_built = False
        self._fast_mode = False
        self._camera_locked = False
        self._fixed_clipping: tuple[float, float] | None = None

    @property
    def has_lattice_context(self) -> bool:
        return self._context is not None

    @property
    def cell_radius_factor(self) -> float:
        return self._cell_radius_factor

    def set_cell_radius_factor(self, factor: float) -> None:
        self._cell_radius_factor = min(0.48, max(0.06, factor))

    def set_fast_mode(self, enabled: bool) -> None:
        """Меньше полигонов при живом обновлении во время симуляции."""
        self._fast_mode = enabled

    def occupied_radius(self) -> float:
        return self._base_spacing * self._cell_radius_factor

    def empty_radius(self) -> float:
        return self._base_spacing * self._cell_radius_factor * 0.45

    def _sphere_resolution(self) -> int:
        return 8 if self._fast_mode else 14

    def set_display_options(self, *, show_throats: bool, show_empty: bool) -> None:
        self._show_throats = show_throats
        self._show_empty = show_empty
        self._rebuild_throats_if_needed()
        if self._last_snapshot is not None:
            self._update_cells_only()

    def clear(self) -> None:
        self.plotter.clear()
        self._context = None
        self._last_snapshot = None
        self._throats_built = False
        self._camera_locked = False
        self._fixed_clipping = None
        self.plotter.camera_set = False

    def _stash_camera(self) -> CameraPosition:
        return self.plotter.camera_position

    def _restore_camera(self, position: CameraPosition) -> None:
        self.plotter.camera_position = position

    def _ensure_fixed_clipping(self) -> None:
        if self._context is None:
            return
        if self._fixed_clipping is None:
            self._fixed_clipping = _fixed_clipping_from_coords(
                self._context.coords,
                self._base_spacing,
                self._cell_radius_factor,
            )
        self.plotter.camera.clipping_range = self._fixed_clipping

    def _lock_camera_after_draw(self) -> None:
        self._ensure_fixed_clipping()
        self._camera_locked = True
        self.plotter.camera_set = True

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
        self._fixed_clipping = None
        self._camera_locked = False
        self.plotter.camera_set = False
        self.plotter.clear()
        self._throats_built = False
        self._rebuild_throats_if_needed()
        self._update_cells_only()
        if reset_camera:
            self.plotter.reset_camera()
        self._lock_camera_after_draw()
        self.plotter.render()

    def update_snapshot(self, snapshot: VisualSnapshot) -> None:
        """Быстрое обновление — только клетки, без пересборки throats."""
        if self._context is None:
            return
        self._last_snapshot = snapshot
        cam = self._stash_camera() if self._camera_locked else None
        self._update_cells_only()
        if self._camera_locked and cam is not None:
            self._restore_camera(cam)
        self._ensure_fixed_clipping()
        self.plotter.render()

    def refresh_cells(self) -> None:
        """Перерисовать клетки (например после смены размера сфер)."""
        if self._last_snapshot is not None:
            cam = self._stash_camera() if self._camera_locked else None
            self._fixed_clipping = None
            self._update_cells_only()
            if self._camera_locked and cam is not None:
                self._restore_camera(cam)
            self._ensure_fixed_clipping()
            self.plotter.render()

    def _remove_cell_actors(self) -> None:
        for name in CELL_ACTOR_NAMES:
            try:
                self.plotter.remove_actor(name, reset_camera=False, render=False)
            except (KeyError, ValueError):
                pass

    def _rebuild_throats_if_needed(self) -> None:
        if self._context is None:
            return
        if not self._show_throats:
            if self._throats_built:
                try:
                    self.plotter.remove_actor("throats", reset_camera=False, render=False)
                except (KeyError, ValueError):
                    pass
                self._throats_built = False
            return
        if self._throats_built:
            return
        mesh = _throat_lines_mesh(self._context.coords, self._context.edges)
        self.plotter.add_mesh(
            mesh,
            name="throats",
            color="#666680",
            line_width=1.2,
            opacity=0.3,
            render_lines_as_tubes=False,
            reset_camera=False,
        )
        self._throats_built = True

    def _add_glyph_cells(
        self,
        pts: np.ndarray,
        radius: float,
        color: str,
        name: str,
    ) -> None:
        if len(pts) == 0:
            return
        res = self._sphere_resolution()
        cloud = pv.PolyData(pts)
        geom = pv.Sphere(radius=radius, theta_resolution=res, phi_resolution=res)
        glyphs = cloud.glyph(geom=geom, scale=False, orient=False)
        self.plotter.add_mesh(
            glyphs,
            name=name,
            color=color,
            opacity=1.0,
            smooth_shading=not self._fast_mode,
            lighting=True,
            reset_camera=False,
        )

    def _update_cells_only(self) -> None:
        if self._context is None or self._last_snapshot is None:
            return
        self._remove_cell_actors()
        codes = self._last_snapshot.pore_types
        coords = self._context.coords
        r_occ = self.occupied_radius()
        r_empty = self.empty_radius()

        groups = [
            (-1, "cells_empty", r_empty, self._show_empty),
            (0, "cells_ob", r_occ, True),
            (1, "cells_msc", r_occ, True),
            (2, "cells_fib", r_occ, True),
        ]
        for code, name, radius, enabled in groups:
            if not enabled:
                continue
            idx = np.where(codes == code)[0]
            if len(idx) == 0:
                continue
            self._add_glyph_cells(coords[idx], radius, COLORS[code], name)

    def occupied_count(self, snapshot: VisualSnapshot) -> int:
        return int(np.sum(snapshot.pore_types >= 0))

    def export_png(self, path: str | Path) -> None:
        was_fast = self._fast_mode
        self._fast_mode = False
        if self._last_snapshot is not None:
            self._update_cells_only()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.plotter.screenshot(str(path))
        self._fast_mode = was_fast
