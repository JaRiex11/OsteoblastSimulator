"""
Синхронный agent-based движок: одно действие на клетку за шаг, разрешение конфликтов.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Iterable

from bone_lattice_sim.lattice.engine import (
    LatticeGraph,
    center_cluster_pore_indices,
    face_center_pore_index,
    random_pore_indices,
)
from bone_lattice_sim.simulation.agents import (
    ActionType,
    Cell,
    CellType,
    CellTypeParams,
    default_params_for,
    parse_cell_type,
)
from bone_lattice_sim.simulation.stats import SimulationResult, StepStats, count_cells_by_type


@dataclass
class SimulationConfig:
    time_steps: int = 200
    seed: int | None = None
    type_params: dict[CellType, CellTypeParams] = field(default_factory=dict)

    def params_for(self, cell_type: CellType) -> CellTypeParams:
        return self.type_params.get(cell_type, default_params_for(cell_type))

    def validate(self) -> None:
        if self.time_steps < 1:
            raise ValueError("time_steps должно быть >= 1")
        for cell_type, params in (
            (t, self.params_for(t)) for t in CellType
        ):
            for name, value in (
                ("p_migrate", params.p_migrate),
                ("p_prolif", params.p_prolif),
            ):
                if not 0.0 <= value <= 1.0:
                    raise ValueError(
                        f"{cell_type.value}.{name} должно быть в [0, 1], получено {value}"
                    )


@dataclass(frozen=True)
class Intent:
    cell_id: int
    action: ActionType
    target_pore: int


class Simulation:
    """
    Колонизация 3D-поровой сети несколькими типами клеток.

    Шаг симуляции (синхронный):
      1. Для каждой клетки (случайный порядок) — decide_action → Intent или NONE.
      2. Конфликты по target_pore: случайный победитель.
      3. Применение: сначала MIGRATE, затем PROLIF (с повторной проверкой занятости).
    """

    def __init__(
        self,
        lattice: LatticeGraph,
        initial_cells: Iterable[tuple[int, CellType]],
        config: SimulationConfig | None = None,
    ) -> None:
        if lattice.n_pores == 0:
            raise ValueError("Решётка не должна быть пустой")

        self.lattice = lattice
        self.config = config or SimulationConfig()
        self.config.validate()
        self.rng = random.Random(self.config.seed)

        self.cells: list[Cell] = []
        self.occupancy: list[Cell | None] = [None] * lattice.n_pores
        self._next_cell_id = 0
        self._init_cells(initial_cells)

    def _init_cells(self, initial_cells: Iterable[tuple[int, CellType]]) -> None:
        for pore, cell_type in initial_cells:
            if not 0 <= pore < self.lattice.n_pores:
                raise ValueError(
                    f"Начальная пора {pore} вне диапазона 0..{self.lattice.n_pores - 1}"
                )
            if self.occupancy[pore] is not None:
                raise ValueError(f"Пора {pore} уже занята при инициализации")
            cell = Cell(cell_id=self._next_cell_id, cell_type=cell_type, pore=pore)
            self._next_cell_id += 1
            self.cells.append(cell)
            self.occupancy[pore] = cell

        if not self.cells:
            raise ValueError("Нужна хотя бы одна начальная клетка")

    def _free_neighbors(self, pore: int) -> list[int]:
        return [n for n in self.lattice.neighbors[pore] if self.occupancy[n] is None]

    def _decide_action(self, cell: Cell) -> Intent | None:
        params = self.config.params_for(cell.cell_type)
        free = self._free_neighbors(cell.pore)
        if not free:
            return None

        if self.rng.random() < params.p_migrate:
            target = self.rng.choice(free)
            return Intent(cell.cell_id, ActionType.MIGRATE, target)

        if self.rng.random() < params.p_prolif:
            target = self.rng.choice(free)
            return Intent(cell.cell_id, ActionType.PROLIF, target)

        return None

    def _resolve_conflicts(self, intents: list[Intent]) -> list[Intent]:
        """Один intent на target_pore — случайный победитель."""
        by_target: dict[int, list[Intent]] = {}
        for intent in intents:
            by_target.setdefault(intent.target_pore, []).append(intent)

        resolved: list[Intent] = []
        for group in by_target.values():
            resolved.append(self.rng.choice(group))
        return resolved

    def _apply_migrations(self, intents: list[Intent]) -> int:
        migrate_map = {
            i.cell_id: i for i in intents if i.action == ActionType.MIGRATE
        }
        if not migrate_map:
            return 0

        id_to_cell = {c.cell_id: c for c in self.cells}
        applied = 0
        for cell_id, intent in migrate_map.items():
            cell = id_to_cell.get(cell_id)
            if cell is None:
                continue
            if self.occupancy[intent.target_pore] is not None:
                continue
            if self.occupancy[cell.pore] is not cell:
                continue

            self.occupancy[cell.pore] = None
            cell.pore = intent.target_pore
            self.occupancy[intent.target_pore] = cell
            applied += 1
        return applied

    def _apply_proliferations(self, intents: list[Intent]) -> int:
        prolif_map = {
            i.cell_id: i for i in intents if i.action == ActionType.PROLIF
        }
        if not prolif_map:
            return 0

        id_to_cell = {c.cell_id: c for c in self.cells}
        applied = 0
        for cell_id, intent in prolif_map.items():
            parent = id_to_cell.get(cell_id)
            if parent is None:
                continue
            if self.occupancy[intent.target_pore] is not None:
                continue

            child = Cell(
                cell_id=self._next_cell_id,
                cell_type=parent.cell_type,
                pore=intent.target_pore,
            )
            self._next_cell_id += 1
            self.cells.append(child)
            self.occupancy[intent.target_pore] = child
            applied += 1
        return applied

    def _snapshot(self, step_index: int, migrate_n: int = 0, prolif_n: int = 0) -> StepStats:
        occupied = sum(1 for slot in self.occupancy if slot is not None)
        return StepStats(
            step=step_index,
            occupancy=occupied / self.lattice.n_pores,
            cell_count=len(self.cells),
            counts_by_type=count_cells_by_type(self.cells),
            migrate_events=migrate_n,
            prolif_events=prolif_n,
        )

    def step(self) -> tuple[int, int]:
        """Один шаг симуляции. Возвращает (migrate_events, prolif_events)."""
        intents: list[Intent] = []
        order = self.cells[:]
        self.rng.shuffle(order)

        for cell in order:
            intent = self._decide_action(cell)
            if intent is not None:
                intents.append(intent)

        resolved = self._resolve_conflicts(intents)
        migrate_n = self._apply_migrations(resolved)
        prolif_n = self._apply_proliferations(resolved)
        return migrate_n, prolif_n

    def run(
        self,
        *,
        on_step: Callable[[StepStats], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        update_every: int = 1,
    ) -> SimulationResult:
        """
        Полный прогон. on_step вызывается для GUI (каждые update_every шагов).
        cancel_check возвращает True — остановка досрочно.
        """
        result = SimulationResult(
            n_pores=self.lattice.n_pores,
            preset=str(self.lattice.meta.get("preset", "")),
            avg_lattice_degree=float(self.lattice.meta.get("avg_degree", 0.0)),
        )
        snap0 = self._snapshot(0)
        result.history.append(snap0)
        if on_step is not None:
            on_step(snap0)

        for t in range(1, self.config.time_steps + 1):
            if cancel_check and cancel_check():
                break
            migrate_n, prolif_n = self.step()
            snap = self._snapshot(t, migrate_n, prolif_n)
            result.history.append(snap)
            if on_step is not None and (t % max(1, update_every) == 0 or t == self.config.time_steps):
                on_step(snap)
        return result

    @property
    def occupied_pore_count(self) -> int:
        return sum(1 for slot in self.occupancy if slot is not None)


def build_initial_cells(
    lattice: LatticeGraph,
    seed_mode: str,
    *,
    cell_type: CellType = CellType.OSTEOBLAST,
    n_seeds: int = 1,
    seed: int | None = None,
) -> list[tuple[int, CellType]]:
    """
    Размещение начальных клеток.

    seed_mode: center | face | random
    """
    rng = random.Random(seed)
    mode = seed_mode.strip().lower()

    if mode == "center":
        pores = center_cluster_pore_indices(lattice, max(1, n_seeds))
        return [(p, cell_type) for p in pores]

    if mode == "face":
        pore = face_center_pore_index(lattice)
        return [(pore, cell_type)]

    if mode == "random":
        pores = random_pore_indices(lattice.n_pores, n_seeds, rng)
        return [(p, cell_type) for p in pores]

    raise ValueError("seed_mode: center | face | random")


def parse_initial_cell_mix(spec: str) -> list[tuple[CellType, int]]:
    """
    Разбор строки вида 'osteoblast:5,msc:3' или 'fibroblast:1;msc:2'.

    Разделители: запятая или точка с запятой. Без «:число» считается :1.
    """
    if not spec.strip():
        return [(CellType.OSTEOBLAST, 1)]
    normalized = spec.replace(";", ",")
    result: list[tuple[CellType, int]] = []
    for part in normalized.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, count_str = part.split(":", 1)
            count = int(count_str.strip())
        else:
            name, count = part, 1
        if count < 1:
            raise ValueError(f"Число клеток должно быть >= 1, получено: {count}")
        result.append((parse_cell_type(name), count))
    if not result:
        raise ValueError("Состав клеток пуст. Пример: osteoblast:1 или fibroblast:3,msc:2")
    return result
