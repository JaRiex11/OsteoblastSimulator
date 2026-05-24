"""Тесты разрешения конфликтов при синхронном шаге."""

from __future__ import annotations

from bone_lattice_sim.lattice.engine import LatticeGraph
from bone_lattice_sim.simulation.agents import CellType, CellTypeParams
from bone_lattice_sim.simulation.simulation import Simulation, SimulationConfig
import numpy as np


def _fork_lattice() -> LatticeGraph:
    """
    Три поры: 0 — 1 — 2; клетки в 0 и 2 могут обе хотеть мигрировать в 1.
    """
    neighbors = [[1], [0, 2], [1]]
    coords = np.zeros((3, 3))
    return LatticeGraph(n_pores=3, neighbors=neighbors, coords=coords, meta={"size": 3})


def test_conflict_allows_at_most_one_cell_in_target():
    lattice = _fork_lattice()
    config = SimulationConfig(
        time_steps=1,
        seed=123,
        type_params={
            CellType.OSTEOBLAST: CellTypeParams(p_migrate=1.0, p_prolif=0.0),
        },
    )
    sim = Simulation(
        lattice,
        [(0, CellType.OSTEOBLAST), (2, CellType.OSTEOBLAST)],
        config,
    )
    sim.step()
    occupied = [i for i, c in enumerate(sim.occupancy) if c is not None]
    assert len(occupied) == 2
    assert len(set(occupied)) == 2
    assert 1 in occupied


def test_lattice_engine_builds_connected_random():
    from bone_lattice_sim.lattice.engine import build_lattice
    import networkx as nx

    lattice = build_lattice(5, "random", throat_deletion_fraction=0.4, seed=7)
    g = nx.Graph()
    g.add_nodes_from(range(lattice.n_pores))
    for i, nbrs in enumerate(lattice.neighbors):
        for j in nbrs:
            if i < j:
                g.add_edge(i, j)
    assert nx.is_connected(g)
    assert lattice.n_pores == 125
