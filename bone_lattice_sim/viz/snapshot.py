"""Снимки состояния для 3D-визуализации."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bone_lattice_sim.lattice.engine import LatticeGraph
from bone_lattice_sim.simulation.agents import CellType
from bone_lattice_sim.simulation.simulation import Simulation

CELL_CODE: dict[CellType, int] = {
    CellType.OSTEOBLAST: 0,
    CellType.MSC: 1,
    CellType.FIBROBLAST: 2,
}

CODE_TO_NAME: dict[int, str] = {
    -1: "empty",
    0: "osteoblast",
    1: "msc",
    2: "fibroblast",
}


@dataclass(frozen=True)
class LatticeVisualContext:
    coords: np.ndarray
    edges: np.ndarray
    n_pores: int


@dataclass(frozen=True)
class VisualSnapshot:
    step: int
    pore_types: np.ndarray


def build_visual_context(lattice: LatticeGraph) -> LatticeVisualContext:
    edges: list[list[int]] = []
    for i, nbrs in enumerate(lattice.neighbors):
        for j in nbrs:
            if i < j:
                edges.append([i, j])
    edge_arr = np.array(edges, dtype=np.int64) if edges else np.empty((0, 2), dtype=np.int64)
    return LatticeVisualContext(
        coords=np.asarray(lattice.coords, dtype=float),
        edges=edge_arr,
        n_pores=lattice.n_pores,
    )


def snapshot_from_simulation(sim: Simulation, step: int) -> VisualSnapshot:
    codes = np.full(sim.lattice.n_pores, -1, dtype=np.int8)
    for pore, cell in enumerate(sim.occupancy):
        if cell is not None:
            codes[pore] = CELL_CODE[cell.cell_type]
    return VisualSnapshot(step=step, pore_types=codes)


def snapshot_from_initial(
    lattice: LatticeGraph,
    initial: list[tuple[int, CellType]],
) -> VisualSnapshot:
    """Начальное размещение клеток (шаг 0) для предпросмотра."""
    codes = np.full(lattice.n_pores, -1, dtype=np.int8)
    for pore, cell_type in initial:
        if 0 <= pore < lattice.n_pores:
            codes[pore] = CELL_CODE[cell_type]
    return VisualSnapshot(step=0, pore_types=codes)


def empty_snapshot(n_pores: int) -> VisualSnapshot:
    return VisualSnapshot(step=0, pore_types=np.full(n_pores, -1, dtype=np.int8))


def copy_snapshot(snapshot: VisualSnapshot) -> VisualSnapshot:
    """Копия для хранения кадров анимации."""
    return VisualSnapshot(
        step=snapshot.step,
        pore_types=snapshot.pore_types.copy(),
    )
