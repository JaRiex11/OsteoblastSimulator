"""
Сборка решётки и симуляции из параметров GUI/CLI.
"""

from __future__ import annotations

import random
from typing import Any

from bone_lattice_sim.lattice.engine import (
    LatticeGraph,
    average_degree,
    build_lattice,
    center_cluster_pore_indices,
    random_face_pore_indices,
    reachable_fraction,
)
from bone_lattice_sim.simulation.agents import CellType, CellTypeParams
from bone_lattice_sim.simulation.simulation import (
    Simulation,
    SimulationConfig,
    build_initial_cells,
    parse_initial_cell_mix,
)
from bone_lattice_sim.simulation.stats import SimulationResult


def type_params_from_settings(settings: dict[str, Any]) -> dict[CellType, CellTypeParams]:
    mapping = {
        CellType.OSTEOBLAST: "osteoblast",
        CellType.MSC: "msc",
        CellType.FIBROBLAST: "fibroblast",
    }
    params: dict[CellType, CellTypeParams] = {}
    for cell_type, prefix in mapping.items():
        params[cell_type] = CellTypeParams(
            p_migrate=float(settings[f"{prefix}_p_migrate"]),
            p_prolif=float(settings[f"{prefix}_p_prolif"]),
        )
    return params


def _cells_from_mix_on_pores(
    mix: list[tuple[CellType, int]],
    pores: list[int],
) -> list[tuple[int, CellType]]:
    cells: list[tuple[int, CellType]] = []
    idx = 0
    for cell_type, count in mix:
        for _ in range(count):
            if idx >= len(pores):
                break
            cells.append((pores[idx], cell_type))
            idx += 1
    return cells


def build_initial_from_settings(
    lattice: LatticeGraph,
    settings: dict[str, Any],
) -> list[tuple[int, CellType]]:
    """Размещение: center, face (грань min-Z), random."""
    seed = int(settings["seed"])
    mode = settings["initial_mode"]
    mix = parse_initial_cell_mix(settings["cell_mix"])
    total = sum(count for _, count in mix)
    rng = random.Random(seed)

    if mode == "center":
        if total <= 1:
            cell_type = mix[0][0]
            return build_initial_cells(
                lattice, "center", cell_type=cell_type, n_seeds=1, seed=seed,
            )
        pores = center_cluster_pore_indices(lattice, total)
        cells = _cells_from_mix_on_pores(mix, pores)
        if cells:
            return cells
        return build_initial_cells(lattice, "center", cell_type=mix[0][0], seed=seed)

    if mode == "face":
        if total <= 1:
            cell_type = mix[0][0]
            return build_initial_cells(lattice, "face", cell_type=cell_type, seed=seed)
        pores = random_face_pore_indices(lattice, total, rng)
        cells = _cells_from_mix_on_pores(mix, pores)
        if cells:
            return cells
        return build_initial_cells(lattice, "face", cell_type=mix[0][0], seed=seed)

    if mode == "random":
        n_seeds = max(total, int(settings.get("n_seeds", total)))
        from bone_lattice_sim.lattice.engine import random_pore_indices

        pores = random_pore_indices(lattice.n_pores, min(total, n_seeds), rng)
        cells = _cells_from_mix_on_pores(mix, pores)
        if cells:
            return cells
        return build_initial_cells(lattice, "center", seed=seed)

    raise ValueError(f"Неизвестный initial_mode: {mode!r}")


def create_lattice(settings: dict[str, Any]) -> LatticeGraph:
    return build_lattice(
        int(settings["size"]),
        settings["preset"],
        throat_deletion_fraction=float(settings["deletion"]),
        seed=int(settings["seed"]),
    )


def create_simulation(
    lattice: LatticeGraph | None,
    settings: dict[str, Any],
) -> tuple[Simulation, LatticeGraph, list[tuple[int, CellType]]]:
    if lattice is None:
        lattice = create_lattice(settings)
    initial = build_initial_from_settings(lattice, settings)
    config = SimulationConfig(
        time_steps=int(settings["time_steps"]),
        seed=int(settings["seed"]),
        type_params=type_params_from_settings(settings),
    )
    sim = Simulation(lattice, initial, config)
    return sim, lattice, initial


def lattice_summary(lattice: LatticeGraph, initial: list[tuple[int, CellType]]) -> str:
    reach = reachable_fraction(lattice, [p for p, _ in initial])
    return (
        f"Поры: {lattice.n_pores}, preset={lattice.meta.get('preset')}, "
        f"<k>={average_degree(lattice):.2f}, достижимо={reach * 100:.1f}%"
    )


def result_summary(result: SimulationResult) -> str:
    t50 = result.time_to_threshold(0.5)
    t90 = result.time_to_threshold(0.9)
    last = result.history[-1] if result.history else None
    types = ""
    if last:
        types = (
            f" | Ob={last.counts_by_type['osteoblast']}, "
            f"MSC={last.counts_by_type['msc']}, "
            f"Fib={last.counts_by_type['fibroblast']}"
        )
    return (
        f"Занятость: {result.final_occupancy * 100:.1f}%, "
        f"клеток: {result.final_cell_count}, "
        f"T50={t50 if t50 is not None else 'n/a'}, "
        f"T90={t90 if t90 is not None else 'n/a'}{types}"
    )
