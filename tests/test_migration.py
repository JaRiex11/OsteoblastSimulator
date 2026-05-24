"""Тесты миграции клеток по графу пор."""

from __future__ import annotations

import random

from bone_lattice_sim.lattice.engine import LatticeGraph
from bone_lattice_sim.simulation.agents import CellType, CellTypeParams
from bone_lattice_sim.simulation.simulation import Simulation, SimulationConfig
import numpy as np


def _tiny_line_lattice(n: int = 5) -> LatticeGraph:
    neighbors = [[] for _ in range(n)]
    for i in range(n):
        if i > 0:
            neighbors[i].append(i - 1)
        if i < n - 1:
            neighbors[i].append(i + 1)
    coords = np.column_stack([np.arange(n, dtype=float), np.zeros(n), np.zeros(n)])
    return LatticeGraph(n_pores=n, neighbors=neighbors, coords=coords, meta={"size": n})


def test_migration_moves_to_neighbor():
    lattice = _tiny_line_lattice(5)
    config = SimulationConfig(
        time_steps=1,
        seed=0,
        type_params={
            CellType.OSTEOBLAST: CellTypeParams(p_migrate=1.0, p_prolif=0.0),
        },
    )
    sim = Simulation(lattice, [(0, CellType.OSTEOBLAST)], config)
    assert sim.cells[0].pore == 0
    sim.step()
    assert sim.cells[0].pore == 1


def test_no_migration_without_free_neighbors():
    lattice = _tiny_line_lattice(1)
    config = SimulationConfig(
        time_steps=1,
        seed=0,
        type_params={
            CellType.OSTEOBLAST: CellTypeParams(p_migrate=1.0, p_prolif=0.0),
        },
    )
    sim = Simulation(lattice, [(0, CellType.OSTEOBLAST)], config)
    sim.step()
    assert sim.cells[0].pore == 0


def test_proliferation_creates_daughter():
    lattice = _tiny_line_lattice(5)
    config = SimulationConfig(
        time_steps=1,
        seed=0,
        type_params={
            CellType.OSTEOBLAST: CellTypeParams(p_migrate=0.0, p_prolif=1.0),
        },
    )
    sim = Simulation(lattice, [(2, CellType.OSTEOBLAST)], config)
    assert len(sim.cells) == 1
    sim.step()
    assert len(sim.cells) == 2
    pores = sorted(c.pore for c in sim.cells)
    assert pores == [1, 2] or pores == [2, 3]
