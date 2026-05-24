"""
Клеточные агенты: типы, параметры миграции и пролиферации.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class CellType(str, Enum):
    OSTEOBLAST = "osteoblast"
    MSC = "msc"
    FIBROBLAST = "fibroblast"


class ActionType(str, Enum):
    NONE = "none"
    MIGRATE = "migrate"
    PROLIF = "prolif"


@dataclass(frozen=True)
class CellTypeParams:
    p_migrate: float
    p_prolif: float


DEFAULT_TYPE_PARAMS: dict[CellType, CellTypeParams] = {
    CellType.OSTEOBLAST: CellTypeParams(p_migrate=0.5, p_prolif=0.25),
    CellType.MSC: CellTypeParams(p_migrate=0.35, p_prolif=0.15),
    CellType.FIBROBLAST: CellTypeParams(p_migrate=0.65, p_prolif=0.10),
}


def default_params_for(cell_type: CellType) -> CellTypeParams:
    return DEFAULT_TYPE_PARAMS[cell_type]


@dataclass
class Cell:
    """Активная клетка в одной поре."""

    cell_id: int
    cell_type: CellType
    pore: int

    def params(self, overrides: dict[CellType, CellTypeParams] | None = None) -> CellTypeParams:
        if overrides and self.cell_type in overrides:
            return overrides[self.cell_type]
        return default_params_for(self.cell_type)


CellTypeName = Literal["osteoblast", "msc", "fibroblast"]


def parse_cell_type(name: str) -> CellType:
    key = name.strip().lower()
    mapping = {
        "osteoblast": CellType.OSTEOBLAST,
        "msc": CellType.MSC,
        "fibroblast": CellType.FIBROBLAST,
    }
    if key not in mapping:
        raise ValueError(f"Неизвестный тип клетки: {name!r}")
    return mapping[key]
