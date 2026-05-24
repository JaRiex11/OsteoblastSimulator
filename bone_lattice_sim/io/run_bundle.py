"""Результат одного прогона симуляции для экспорта и отчётов."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bone_lattice_sim.lattice.engine import LatticeGraph
from bone_lattice_sim.simulation.agents import CellType
from bone_lattice_sim.simulation.simulation import Simulation
from bone_lattice_sim.simulation.stats import SimulationResult
from bone_lattice_sim.viz.snapshot import VisualSnapshot


@dataclass
class SimulationRun:
    """Полный контекст прогона: настройки, решётка, история, финальные клетки."""

    result: SimulationResult
    lattice: LatticeGraph
    settings: dict[str, Any]
    initial: list[tuple[int, CellType]]
    final_cells: list[dict[str, Any]] = field(default_factory=list)
    animation_frames: list[VisualSnapshot] = field(default_factory=list)

    @property
    def cancelled_early(self) -> bool:
        expected = int(self.settings.get("time_steps", 0)) + 1
        return len(self.result.history) < expected


def build_run_bundle(
    sim: Simulation,
    lattice: LatticeGraph,
    settings: dict[str, Any],
    initial: list[tuple[int, CellType]],
    result: SimulationResult,
    animation_frames: list[VisualSnapshot] | None = None,
) -> SimulationRun:
    final_cells = [
        {
            "cell_id": cell.cell_id,
            "pore": cell.pore,
            "type": cell.cell_type.value,
        }
        for cell in sim.cells
    ]
    return SimulationRun(
        result=result,
        lattice=lattice,
        settings=dict(settings),
        initial=list(initial),
        final_cells=final_cells,
        animation_frames=list(animation_frames or []),
    )
