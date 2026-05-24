"""Тесты кластера начальных клеток в центре решётки."""

from __future__ import annotations

import numpy as np

from bone_lattice_sim.experiment import build_initial_from_settings
from bone_lattice_sim.lattice.engine import build_lattice, center_cluster_pore_indices
from bone_lattice_sim.simulation.agents import CellType


def test_center_cluster_count_and_uniqueness():
    lattice = build_lattice(10, "regular_6", seed=1)
    pores = center_cluster_pore_indices(lattice, 5)
    assert len(pores) == 5
    assert len(set(pores)) == 5


def test_center_cluster_near_geometric_center():
    lattice = build_lattice(10, "regular_6", seed=1)
    center = lattice.coords.mean(axis=0)
    pores = center_cluster_pore_indices(lattice, 5)
    dists = [float(np.linalg.norm(lattice.coords[p] - center)) for p in pores]
    all_dists = np.linalg.norm(lattice.coords - center, axis=1)
    fifth_nearest = float(np.sort(all_dists)[4])
    assert max(dists) <= fifth_nearest + 1e-9


def test_center_cluster_single_is_nearest_to_center():
    lattice = build_lattice(10, "regular_6", seed=1)
    center = lattice.coords.mean(axis=0)
    pores = center_cluster_pore_indices(lattice, 1)
    dists = np.linalg.norm(lattice.coords - center, axis=1)
    assert pores[0] == int(np.argmin(dists))


def test_build_initial_center_mix_five_osteoblasts():
    lattice = build_lattice(10, "regular_6", seed=42)
    settings = {
        "seed": 42,
        "initial_mode": "center",
        "cell_mix": "osteoblast:5",
        "n_seeds": 1,
    }
    initial = build_initial_from_settings(lattice, settings)
    assert len(initial) == 5
    assert all(ct == CellType.OSTEOBLAST for _, ct in initial)
    assert len({p for p, _ in initial}) == 5
