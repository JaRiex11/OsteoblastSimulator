"""Фоновый прогон симуляции в QThread."""

from __future__ import annotations

import threading
from typing import Any

from PySide6.QtCore import QThread, Signal

from bone_lattice_sim.experiment import create_simulation, lattice_summary, result_summary
from bone_lattice_sim.io.run_bundle import build_run_bundle
from bone_lattice_sim.io.settings import sanitize, suggest_visual_update_every
from bone_lattice_sim.simulation.stats import StepStats
from bone_lattice_sim.viz.snapshot import (
    build_visual_context,
    copy_snapshot,
    snapshot_from_simulation,
)


class SimulationWorker(QThread):
    """Строит решётку и гоняет симуляцию; UI получает сигналы прогресса."""

    step_updated = Signal(object)           # StepStats
    lattice_info = Signal(str)
    visual_ready = Signal(object, object)   # LatticeVisualContext, VisualSnapshot
    visual_updated = Signal(object)         # VisualSnapshot
    finished_ok = Signal(object)            # SimulationRun
    finished_summary = Signal(str)
    error = Signal(str)

    def __init__(self, settings: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.settings = sanitize(settings)
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def _cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            sim, lattice, initial = create_simulation(None, self.settings)
            self.lattice_info.emit(lattice_summary(lattice, initial))

            context = build_visual_context(lattice)
            snap0 = snapshot_from_simulation(sim, 0)
            self.visual_ready.emit(context, snap0)

            chart_every = int(self.settings.get("update_every", 5))
            visual_every = int(
                self.settings.get(
                    "visual_update_every",
                    suggest_visual_update_every(int(self.settings["size"])),
                )
            )
            visual_every = max(1, visual_every)

            record_anim = bool(self.settings.get("record_animation", True))
            anim_every = int(self.settings.get("animation_frame_every", 1))
            anim_every = max(1, anim_every)
            time_steps = int(self.settings["time_steps"])
            animation_frames: list = []

            if record_anim:
                animation_frames.append(copy_snapshot(snap0))

            def on_step(stats: StepStats) -> None:
                self.step_updated.emit(stats)
                snap = snapshot_from_simulation(sim, stats.step)

                if record_anim and (
                    stats.step % anim_every == 0 or stats.step >= time_steps
                ):
                    animation_frames.append(copy_snapshot(snap))

                if stats.step % visual_every == 0 or stats.step >= time_steps:
                    self.visual_updated.emit(snap)

            result = sim.run(
                on_step=on_step,
                cancel_check=self._cancelled,
                update_every=chart_every,
            )

            if record_anim and animation_frames:
                last = animation_frames[-1]
                if last.step != result.history[-1].step:
                    animation_frames.append(
                        copy_snapshot(snapshot_from_simulation(sim, result.history[-1].step))
                    )

            bundle = build_run_bundle(
                sim, lattice, self.settings, initial, result, animation_frames,
            )
            self.finished_ok.emit(bundle)
            self.finished_summary.emit(result_summary(result))
        except Exception as exc:
            self.error.emit(str(exc))
