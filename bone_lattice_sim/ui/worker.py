"""Фоновый прогон симуляции в QThread."""

from __future__ import annotations

import threading
from typing import Any

from PySide6.QtCore import QThread, Signal

from bone_lattice_sim.experiment import create_simulation, lattice_summary, result_summary
from bone_lattice_sim.io.settings import sanitize
from bone_lattice_sim.simulation.stats import SimulationResult, StepStats


class SimulationWorker(QThread):
    """Строит решётку и гоняет симуляцию; UI получает сигналы прогресса."""

    step_updated = Signal(object)       # StepStats
    lattice_info = Signal(str)
    finished_ok = Signal(object)        # SimulationResult
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

            update_every = int(self.settings.get("update_every", 5))

            def on_step(stats: StepStats) -> None:
                self.step_updated.emit(stats)

            result = sim.run(
                on_step=on_step,
                cancel_check=self._cancelled,
                update_every=update_every,
            )
            self.finished_ok.emit(result)
            self.finished_summary.emit(result_summary(result))
        except Exception as exc:
            self.error.emit(str(exc))
