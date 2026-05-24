"""Тесты режима Biological Physics."""

from __future__ import annotations

import pytest

from bone_lattice_sim.experiment import simulation_config_from_settings
from bone_lattice_sim.lattice.engine import build_lattice
from bone_lattice_sim.simulation.agents import CellType
from bone_lattice_sim.simulation.biophysics import compute_biophysics_calibration
from bone_lattice_sim.simulation.simulation import Simulation


def test_biophysics_default_probabilities():
    cal = compute_biophysics_calibration(pore_spacing_um=100.0)
    assert cal.dt_hours == pytest.approx(2.5)
    assert cal.type_params[CellType.FIBROBLAST].p_migrate == pytest.approx(1.0)
    assert cal.type_params[CellType.MSC].p_migrate == pytest.approx(0.5)
    assert cal.type_params[CellType.OSTEOBLAST].p_migrate == pytest.approx(0.25)
    assert cal.type_params[CellType.FIBROBLAST].p_prolif == pytest.approx(2.5 / 24.0)
    assert cal.type_params[CellType.MSC].p_prolif == pytest.approx(2.5 / 30.0)
    assert cal.type_params[CellType.OSTEOBLAST].p_prolif == pytest.approx(2.5 / 40.0)


def test_total_time_hours_in_result():
    lattice = build_lattice(4, "regular_6", seed=1)
    settings = {
        "time_steps": 10,
        "seed": 1,
        "biological_physics_mode": True,
        "pore_spacing_um": 100.0,
        "initial_mode": "center",
        "cell_mix": "osteoblast:1",
        "n_seeds": 1,
    }
    from bone_lattice_sim.experiment import build_initial_from_settings

    config = simulation_config_from_settings(settings)
    initial = build_initial_from_settings(lattice, settings)
    sim = Simulation(lattice, initial, config)
    result = sim.run()
    assert result.dt_hours == pytest.approx(2.5)
    assert result.history[-1].total_time_hours == pytest.approx(10 * 2.5)
