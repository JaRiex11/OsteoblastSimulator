"""Тест выбора действия клетки (миграция / пролиферация)."""

from __future__ import annotations

import random

from bone_lattice_sim.experiment import create_simulation
from bone_lattice_sim.simulation.agents import CellType, CellTypeParams
from bone_lattice_sim.simulation.simulation import Simulation, SimulationConfig
from bone_lattice_sim.lattice.engine import build_lattice


def test_biophysics_fibroblast_can_proliferate():
    """При P_mig=1 и нормировке деление фибробластов возможно."""
    settings = {
        "size": 8,
        "preset": "regular_6",
        "deletion": 0.3,
        "time_steps": 80,
        "seed": 7,
        "initial_mode": "center",
        "cell_mix": "fibroblast:5",
        "biological_physics_mode": True,
        "pore_spacing_um": 100.0,
    }
    sim, _, _ = create_simulation(None, settings)
    p = sim.config.params_for(CellType.FIBROBLAST)
    assert p.p_migrate == 1.0
    assert p.p_prolif > 0.0
    result = sim.run()
    assert result.final_cell_count > 5
    assert sum(s.prolif_events for s in result.history[1:]) > 0


def test_pick_action_type_distribution():
    lattice = build_lattice(4, "regular_6", seed=0)
    config = SimulationConfig(
        time_steps=1,
        seed=0,
        type_params={
            CellType.FIBROBLAST: CellTypeParams(p_migrate=1.0, p_prolif=1.0),
        },
    )
    sim = Simulation(lattice, [(20, CellType.FIBROBLAST)], config)
    rng = random.Random(0)
    counts = {"migrate": 0, "prolif": 0, "stay": 0}
    for _ in range(3000):
        action = sim._pick_action_type(1.0, 1.0)
        if action is None:
            counts["stay"] += 1
        elif action.value == "migrate":
            counts["migrate"] += 1
        else:
            counts["prolif"] += 1
    assert counts["prolif"] > 400
    assert counts["migrate"] > 400
