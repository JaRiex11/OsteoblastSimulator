"""
Сбор и агрегация статистики симуляции.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bone_lattice_sim.simulation.agents import CellType


@dataclass
class StepStats:
    step: int
    occupancy: float
    cell_count: int
    counts_by_type: dict[str, int]
    migrate_events: int = 0
    prolif_events: int = 0
    total_time_hours: float | None = None


@dataclass
class SimulationResult:
    n_pores: int
    history: list[StepStats] = field(default_factory=list)
    preset: str = ""
    avg_lattice_degree: float = 0.0
    dt_hours: float | None = None

    @property
    def occupancy_history(self) -> list[float]:
        return [s.occupancy for s in self.history]

    @property
    def final_occupancy(self) -> float:
        return self.history[-1].occupancy if self.history else 0.0

    @property
    def final_cell_count(self) -> int:
        return self.history[-1].cell_count if self.history else 0

    def time_to_threshold(self, threshold: float) -> int | None:
        return time_to_threshold(self.occupancy_history, threshold)


def time_to_threshold(occupancy_history: list[float], threshold: float) -> int | None:
    """Первый шаг, когда occupancy >= threshold (T50 при 0.5, T90 при 0.9)."""
    for step, value in enumerate(occupancy_history):
        if value >= threshold:
            return step
    return None


def count_cells_by_type(cells: list) -> dict[str, int]:
    counts = {t.value: 0 for t in CellType}
    for cell in cells:
        counts[cell.cell_type.value] += 1
    return counts
