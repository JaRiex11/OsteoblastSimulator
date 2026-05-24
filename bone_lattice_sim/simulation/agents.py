"""
Клеточные агенты: типы, параметры миграции и пролиферации.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

# Каноническое имя -> синонимы (для поля «Состав»)
CELL_TYPE_ALIASES: dict[str, list[str]] = {
    "osteoblast": ["osteoblast", "ob", "osteo", "osteoblasts", "остеобласт", "остеобласты"],
    "msc": ["msc", "mesenchymal", "мск", "msc_cell"],
    "fibroblast": [
        "fibroblast", "fibroblasts", "fibro", "fib", "fiboblast", "fibrblast",
        "фибробласт", "фибробласты",
    ],
}


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

_ALIAS_LOOKUP: dict[str, CellType] = {}
for _canonical, _aliases in CELL_TYPE_ALIASES.items():
    ct = CellType(_canonical)
    for alias in _aliases:
        _ALIAS_LOOKUP[alias.strip().lower()] = ct


def cell_type_help_text() -> str:
    lines = ["Допустимые имена типов клеток (латиница или русский, без учёта регистра):"]
    for canonical, aliases in CELL_TYPE_ALIASES.items():
        shown = ", ".join(aliases[:4])
        if len(aliases) > 4:
            shown += ", ..."
        lines.append(f"  • {canonical}: {shown}")
    return "\n".join(lines)


def parse_cell_type(name: str) -> CellType:
    key = name.strip().lower().replace("-", "_")
    if key in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[key]
    allowed = ", ".join(CELL_TYPE_ALIASES.keys())
    raise ValueError(
        f"Неизвестный тип клетки: {name!r}. "
        f"Используйте одно из: {allowed}. "
        f"Пример для fibroblast: fibroblast:1 или fibro:2"
    )
