"""Тесты спавна с грани решётки."""

from __future__ import annotations

import numpy as np

from bone_lattice_sim.experiment import build_initial_from_settings
from bone_lattice_sim.lattice.engine import (
    build_lattice,
    face_center_pore_index,
    face_pore_indices,
)
from bone_lattice_sim.simulation.agents import CellType
from bone_lattice_sim.simulation.simulation import build_initial_cells


def test_face_pores_on_min_z():
    lattice = build_lattice(6, "regular_6", seed=1)
    face = face_pore_indices(lattice)
    z_min = float(np.min(lattice.coords[:, 2]))
    for i in face:
        assert abs(lattice.coords[i, 2] - z_min) < 1e-4
    assert len(face) == 36  # 6x6 on one face


def test_face_center_on_face():
    lattice = build_lattice(6, "regular_6", seed=1)
    pore = face_center_pore_index(lattice)
    assert pore in face_pore_indices(lattice)


def test_build_initial_face_single():
    lattice = build_lattice(6, "regular_6", seed=1)
    cells = build_initial_cells(lattice, "face", cell_type=CellType.FIBROBLAST, seed=1)
    assert len(cells) == 1
    pore, ct = cells[0]
    assert ct == CellType.FIBROBLAST
    assert pore in face_pore_indices(lattice)


def test_build_initial_from_settings_face_multi():
    lattice = build_lattice(6, "regular_6", seed=1)
    settings = {
        "seed": 1,
        "initial_mode": "face",
        "cell_mix": "osteoblast:2,fibroblast:1",
        "n_seeds": 5,
    }
    cells = build_initial_from_settings(lattice, settings)
    assert len(cells) == 3
    face = set(face_pore_indices(lattice))
    assert all(p in face for p, _ in cells)
