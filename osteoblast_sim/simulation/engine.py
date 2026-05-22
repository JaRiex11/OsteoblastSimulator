"""
Движок вероятностной симуляции остеобластов (lattice-based model).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterable

import networkx as nx
import numpy as np


@dataclass
class SimulationConfig:
    p_migrate: float = 0.7
    p_prolif: float = 0.3
    time_steps: int = 200
    seed: int | None = None

    def validate(self) -> None:
        for name, value in (("p_migrate", self.p_migrate), ("p_prolif", self.p_prolif)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} должно быть в [0, 1], получено {value}")
        if self.time_steps < 1:
            raise ValueError(f"time_steps должно быть >= 1, получено {self.time_steps}")


@dataclass
class EventCounters:
    migrate_attempts: int = 0
    migrate_success: int = 0
    prolif_attempts: int = 0
    prolif_success: int = 0

    def total_events(self) -> int:
        return self.migrate_success + self.prolif_success


@dataclass
class SimulationResult:
    occupancy_history: list[float] = field(default_factory=list)
    cell_count_history: list[int] = field(default_factory=list)
    occupied_sets: list[set[int]] = field(default_factory=list)
    colonization_snapshots: list[dict[int, int]] = field(default_factory=list)
    events_per_step: list[tuple[int, int]] = field(default_factory=list)
    n_vertices: int = 0
    events: EventCounters = field(default_factory=EventCounters)

    @property
    def final_occupancy(self) -> float:
        return self.occupancy_history[-1] if self.occupancy_history else 0.0

    @property
    def final_cell_count(self) -> int:
        return self.cell_count_history[-1] if self.cell_count_history else 0

    def time_to_threshold(self, threshold: float) -> int | None:
        for step, fraction in enumerate(self.occupancy_history):
            if fraction >= threshold:
                return step
        return None


class OsteoblastSimulation:
    UNCOLONIZED = -1

    def __init__(
        self,
        graph: nx.Graph,
        initial_vertices: Iterable[int],
        config: SimulationConfig | None = None,
    ) -> None:
        if graph.number_of_nodes() == 0:
            raise ValueError("Граф не должен быть пустым")

        self.graph = graph
        self.n_vertices = graph.number_of_nodes()
        self.config = config or SimulationConfig()
        self.config.validate()

        self.rng = random.Random(self.config.seed)
        self.cells: list[int] = []
        self.occupied: set[int] = set()
        self.colonization_step: dict[int, int] = {
            int(v): self.UNCOLONIZED for v in graph.nodes()
        }
        self.events = EventCounters()
        self._step_migrate_ok = 0
        self._step_prolif_ok = 0
        self._init_cells(initial_vertices)

    def _init_cells(self, initial_vertices: Iterable[int]) -> None:
        nodes = set(self.graph.nodes())
        for v in initial_vertices:
            vi = int(v)
            if vi not in nodes:
                raise ValueError(
                    f"Начальная вершина {vi} отсутствует в графе (0..{self.n_vertices - 1})"
                )
            self.cells.append(vi)
            self._colonize(vi, step=0)
        if not self.cells:
            raise ValueError("Нужна хотя бы одна начальная клетка")
        self._sync_occupied()

    def _colonize(self, vertex: int, step: int) -> None:
        if self.colonization_step[vertex] == self.UNCOLONIZED:
            self.colonization_step[vertex] = step

    def _sync_occupied(self) -> None:
        self.occupied = set(self.cells)

    def _neighbors(self, vertex: int) -> list[int]:
        return list(self.graph.neighbors(vertex))

    def _try_release_vertex(
        self, vertex: int, cell_index: int, all_indices: list[int],
        processed: set[int], new_cells: list[int],
    ) -> None:
        others = sum(
            1 for j in all_indices
            if j not in processed and j != cell_index and self.cells[j] == vertex
        )
        staying = sum(1 for c in new_cells if c == vertex)
        if others + staying == 0:
            self.occupied.discard(vertex)

    def _attempt_migration(
        self, vertex: int, cell_index: int, all_indices: list[int],
        processed: set[int], new_cells: list[int], current_step: int,
    ) -> int:
        if self.rng.random() >= self.config.p_migrate:
            return vertex
        self.events.migrate_attempts += 1
        neighbors = self._neighbors(vertex)
        if not neighbors:
            return vertex
        target = self.rng.choice(neighbors)
        if target in self.occupied:
            return vertex
        self.events.migrate_success += 1
        self._step_migrate_ok += 1
        self._try_release_vertex(vertex, cell_index, all_indices, processed, new_cells)
        self.occupied.add(target)
        self._colonize(target, current_step)
        return target

    def _attempt_proliferation(self, vertex: int, current_step: int) -> int | None:
        if self.rng.random() >= self.config.p_prolif:
            return None
        self.events.prolif_attempts += 1
        neighbors = self._neighbors(vertex)
        if not neighbors:
            return None
        target = self.rng.choice(neighbors)
        if target in self.occupied:
            return None
        self.events.prolif_success += 1
        self._step_prolif_ok += 1
        self.occupied.add(target)
        self._colonize(target, current_step)
        return target

    def step(self, step_index: int) -> float:
        self._step_migrate_ok = 0
        self._step_prolif_ok = 0
        new_cells: list[int] = []
        indices = list(range(len(self.cells)))
        self.rng.shuffle(indices)
        processed: set[int] = set()

        for idx in indices:
            v = self.cells[idx]
            v = self._attempt_migration(v, idx, indices, processed, new_cells, step_index)
            new_cells.append(v)
            daughter = self._attempt_proliferation(v, step_index)
            if daughter is not None:
                new_cells.append(daughter)
            processed.add(idx)

        self.cells = new_cells
        self._sync_occupied()
        return len(self.occupied) / self.n_vertices

    def run(self, record_history: bool = False) -> SimulationResult:
        result = SimulationResult(n_vertices=self.n_vertices)
        result.events = self.events

        def _snapshot() -> None:
            result.occupancy_history.append(len(self.occupied) / self.n_vertices)
            result.cell_count_history.append(len(self.cells))
            if record_history:
                result.occupied_sets.append(set(self.occupied))
                result.colonization_snapshots.append(dict(self.colonization_step))
            result.events_per_step.append((self._step_migrate_ok, self._step_prolif_ok))

        _snapshot()
        for t in range(1, self.config.time_steps + 1):
            self.step(t)
            _snapshot()
        return result

    def local_density_map(self) -> dict[int, float]:
        density: dict[int, float] = {}
        for node in self.graph.nodes():
            nbrs = list(self.graph.neighbors(node))
            if not nbrs:
                density[node] = 0.0
            else:
                density[node] = sum(1 for n in nbrs if n in self.occupied) / len(nbrs)
        return density


def parse_initial_cells(
    spec: str, n_vertices: int, n_seeds: int = 1, seed: int | None = None,
) -> list[int]:
    spec = spec.strip().lower()
    rng = random.Random(seed)
    if spec == "center":
        return [n_vertices // 2]
    if spec == "random":
        if n_seeds < 1 or n_seeds > n_vertices:
            raise ValueError("n_seeds должно быть от 1 до числа вершин")
        return rng.sample(range(n_vertices), n_seeds)
    try:
        vertices = [int(x.strip()) for x in spec.split(",") if x.strip()]
    except ValueError as exc:
        raise ValueError("initial-cells: center | random | 0,5,10") from exc
    if not vertices:
        raise ValueError("Укажите хотя бы одну начальную вершину")
    return vertices


def export_results_csv(path: str, result: SimulationResult) -> None:
    n = len(result.occupancy_history)
    migrate_col = [0] * n
    prolif_col = [0] * n
    for i, (m, p) in enumerate(result.events_per_step):
        if i < n:
            migrate_col[i] = m
            prolif_col[i] = p
    data = np.column_stack([
        np.arange(n), result.occupancy_history,
        result.cell_count_history or [0] * n, migrate_col, prolif_col,
    ])
    header = "step,occupancy_fraction,cell_count,migrate_events,prolif_events"
    np.savetxt(path, data, delimiter=",", header=header, comments="",
               fmt=["%d", "%.6f", "%d", "%d", "%d"])
