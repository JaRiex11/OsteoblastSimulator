"""
Пересчёт P_migrate и P_prolif из физических констант (режим Biological Physics).

Шаг симуляции dt = d / v_max, где d — расстояние между порами, v_max — максимальная
скорость миграции среди типов клеток в модели.
"""

from __future__ import annotations

from dataclasses import dataclass

from bone_lattice_sim.simulation.agents import CellType, CellTypeParams

DEFAULT_PORE_SPACING_UM = 100.0


@dataclass(frozen=True)
class CellPhysics:
    """Скорость миграции и время деления для типа клетки."""

    migration_speed_um_h: float
    division_time_h: float


DEFAULT_CELL_PHYSICS: dict[CellType, CellPhysics] = {
    CellType.FIBROBLAST: CellPhysics(migration_speed_um_h=40.0, division_time_h=24.0),
    CellType.MSC: CellPhysics(migration_speed_um_h=20.0, division_time_h=30.0),
    CellType.OSTEOBLAST: CellPhysics(migration_speed_um_h=10.0, division_time_h=40.0),
}


@dataclass(frozen=True)
class BiophysicsCalibration:
    """Результат калибровки: dt и вероятности на один дискретный шаг."""

    pore_spacing_um: float
    dt_hours: float
    v_max_um_h: float
    type_params: dict[CellType, CellTypeParams]


def _clamp_prob(value: float) -> float:
    return min(1.0, max(0.0, value))


def compute_biophysics_calibration(
    *,
    pore_spacing_um: float = DEFAULT_PORE_SPACING_UM,
    physics: dict[CellType, CellPhysics] | None = None,
    cell_types: tuple[CellType, ...] | None = None,
) -> BiophysicsCalibration:
    """
    Вычислить dt и вероятности миграции/пролиферации на один шаг симуляции.

    P_migrate = (v_cell * dt) / d
    P_prolif = dt / T_div
    """
    if pore_spacing_um <= 0:
        raise ValueError("pore_spacing_um должно быть > 0")

    phys = physics or DEFAULT_CELL_PHYSICS
    types = cell_types or tuple(CellType)
    v_max = max(phys[t].migration_speed_um_h for t in types)
    if v_max <= 0:
        raise ValueError("v_max должно быть > 0")

    dt_hours = pore_spacing_um / v_max
    type_params: dict[CellType, CellTypeParams] = {}

    for cell_type in CellType:
        p = phys[cell_type]
        p_migrate = _clamp_prob((p.migration_speed_um_h * dt_hours) / pore_spacing_um)
        p_prolif = _clamp_prob(dt_hours / p.division_time_h)
        type_params[cell_type] = CellTypeParams(p_migrate=p_migrate, p_prolif=p_prolif)

    return BiophysicsCalibration(
        pore_spacing_um=pore_spacing_um,
        dt_hours=dt_hours,
        v_max_um_h=v_max,
        type_params=type_params,
    )
