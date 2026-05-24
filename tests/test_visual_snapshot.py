"""Тесты снимков для 3D-визуализации."""

from __future__ import annotations

from bone_lattice_sim.lattice.engine import build_lattice
from bone_lattice_sim.simulation.agents import CellType
from bone_lattice_sim.simulation.simulation import Simulation, SimulationConfig
from bone_lattice_sim.viz.snapshot import (
    build_visual_context,
    empty_snapshot,
    snapshot_from_simulation,
)


def test_build_visual_context_edges():
    lattice = build_lattice(4, "regular_6", seed=1)
    ctx = build_visual_context(lattice)
    assert ctx.coords.shape == (64, 3)
    assert ctx.edges.shape[1] == 2
    assert len(ctx.edges) > 0


def test_snapshot_from_simulation():
    lattice = build_lattice(4, "regular_6", seed=1)
    sim = Simulation(lattice, [(0, CellType.OSTEOBLAST)], SimulationConfig(time_steps=1, seed=1))
    snap = snapshot_from_simulation(sim, 0)
    assert snap.pore_types[0] == 0
    assert (snap.pore_types[1:] == -1).all()


def test_empty_snapshot():
    snap = empty_snapshot(10)
    assert len(snap.pore_types) == 10
    assert (snap.pore_types == -1).all()
