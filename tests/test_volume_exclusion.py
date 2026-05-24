"""Тесты volume exclusion — одна клетка на пору."""

from __future__ import annotations

from bone_lattice_sim.lattice.engine import LatticeGraph
from bone_lattice_sim.simulation.agents import CellType, CellTypeParams
from bone_lattice_sim.simulation.simulation import Simulation, SimulationConfig
import numpy as np


def _tiny_line_lattice(n: int = 5) -> LatticeGraph:
    """Цепочка n пор — простой граф для детерминированных тестов."""
    neighbors = [[] for _ in range(n)]
    for i in range(n):
        if i > 0:
            neighbors[i].append(i - 1)
        if i < n - 1:
            neighbors[i].append(i + 1)
    coords = np.column_stack([np.arange(n, dtype=float), np.zeros(n), np.zeros(n)])
    return LatticeGraph(n_pores=n, neighbors=neighbors, coords=coords, meta={"size": n})


def test_no_duplicate_occupancy_after_many_steps():
    lattice = _tiny_line_lattice(8)
    config = SimulationConfig(
        time_steps=50,
        seed=1,
        type_params={
            CellType.OSTEOBLAST: CellTypeParams(p_migrate=0.9, p_prolif=0.9),
        },
    )
    sim = Simulation(lattice, [(0, CellType.OSTEOBLAST)], config)
    sim.run()

    occupied = [i for i, c in enumerate(sim.occupancy) if c is not None]
    assert len(occupied) == len(set(occupied))
    assert len(sim.cells) == len(occupied)


def test_init_rejects_double_booking():
    lattice = _tiny_line_lattice(3)
    try:
        Simulation(lattice, [(0, CellType.OSTEOBLAST), (0, CellType.MSC)])
        assert False, "expected ValueError"
    except ValueError:
        pass
