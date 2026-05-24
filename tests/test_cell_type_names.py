"""Тесты разбора имён типов клеток."""

from __future__ import annotations

import pytest

from bone_lattice_sim.simulation.agents import CellType, parse_cell_type
from bone_lattice_sim.simulation.simulation import parse_initial_cell_mix


@pytest.mark.parametrize("name", ["fibroblast", "Fibroblast", "fibro", "fib", "фибробласт"])
def test_fibroblast_aliases(name: str):
    assert parse_cell_type(name) == CellType.FIBROBLAST


def test_cell_mix_fibro():
    mix = parse_initial_cell_mix("fibro:3,msc:1")
    assert mix == [(CellType.FIBROBLAST, 3), (CellType.MSC, 1)]


def test_cell_mix_invalid_shows_hint():
    with pytest.raises(ValueError, match="fibroblast"):
        parse_cell_type("fibroblst")
