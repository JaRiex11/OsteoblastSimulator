"""Независимость интервалов графиков, 3D и анимации."""

from __future__ import annotations

from bone_lattice_sim.ui.progress_intervals import (
    should_record_animation_frame,
    should_update_charts,
    should_update_visual,
)


def test_chart_and_animation_decoupled_at_step_3():
    """Шаг 3: анимация каждый 1, графики каждые 5 — кадр есть, график нет."""
    assert not should_update_charts(3, 5, 100)
    assert should_record_animation_frame(3, 1, 100)


def test_animation_and_chart_independent_at_step_5():
    """Шаг 5: графики каждые 5, анимация каждые 2 — график да, кадр нет."""
    assert should_update_charts(5, 5, 100)
    assert not should_record_animation_frame(5, 2, 100)


def test_visual_independent_of_charts():
    """Шаг 7: 3D каждые 7, графики каждые 10."""
    assert not should_update_charts(7, 10, 100)
    assert should_update_visual(7, 7, 100)
