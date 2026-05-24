"""Тест snapshot_from_initial для предпросмотра."""

from __future__ import annotations

from bone_lattice_sim.experiment import build_initial_from_settings
from bone_lattice_sim.lattice.engine import build_lattice
from bone_lattice_sim.simulation.agents import CellType
from bone_lattice_sim.viz.snapshot import CELL_CODE, snapshot_from_initial


def test_snapshot_from_initial_shows_cells():
    lattice = build_lattice(6, "regular_6", seed=1)
    settings = {"seed": 1, "initial_mode": "face", "cell_mix": "fibroblast:1", "n_seeds": 1}
    initial = build_initial_from_settings(lattice, settings)
    snap = snapshot_from_initial(lattice, initial)
    assert snap.pore_types.max() == CELL_CODE[CellType.FIBROBLAST]
    assert (snap.pore_types >= 0).sum() == 1
