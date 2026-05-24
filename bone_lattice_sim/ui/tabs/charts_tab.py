"""Графики pyqtgraph в реальном времени."""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from bone_lattice_sim.simulation.stats import SimulationResult, StepStats


class ChartsTab(QWidget):
    """Доля занятых пор и число клеток по типам."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.plot_occ = pg.PlotWidget(title="Занятость пор (доля)")
        self.plot_occ.setLabel("left", "Occupancy")
        self.plot_occ.setLabel("bottom", "Step")
        self.plot_occ.showGrid(x=True, y=True, alpha=0.3)
        self.plot_occ.setYRange(0, 1.05)
        self.curve_occ = self.plot_occ.plot(pen=pg.mkPen("#2ecc71", width=2))

        self.plot_cells = pg.PlotWidget(title="Число клеток по типам")
        self.plot_cells.setLabel("left", "Count")
        self.plot_cells.setLabel("bottom", "Step")
        self.plot_cells.showGrid(x=True, y=True, alpha=0.3)
        self.plot_cells.addLegend(offset=(10, 10))
        self.curve_ob = self.plot_cells.plot(
            pen=pg.mkPen("#27ae60", width=2), name="Osteoblast",
        )
        self.curve_msc = self.plot_cells.plot(
            pen=pg.mkPen("#3498db", width=2), name="MSC",
        )
        self.curve_fib = self.plot_cells.plot(
            pen=pg.mkPen("#e74c3c", width=2), name="Fibroblast",
        )

        layout.addWidget(self.plot_occ, stretch=1)
        layout.addWidget(self.plot_cells, stretch=1)

        self._steps: list[int] = []
        self._occ: list[float] = []
        self._ob: list[int] = []
        self._msc: list[int] = []
        self._fib: list[int] = []

    def reset(self) -> None:
        self._steps.clear()
        self._occ.clear()
        self._ob.clear()
        self._msc.clear()
        self._fib.clear()
        self.curve_occ.setData([], [])
        self.curve_ob.setData([], [])
        self.curve_msc.setData([], [])
        self.curve_fib.setData([], [])

    def append_step(self, stats: StepStats) -> None:
        self._steps.append(stats.step)
        self._occ.append(stats.occupancy)
        self._ob.append(stats.counts_by_type["osteoblast"])
        self._msc.append(stats.counts_by_type["msc"])
        self._fib.append(stats.counts_by_type["fibroblast"])
        x = self._steps
        self.curve_occ.setData(x, self._occ)
        self.curve_ob.setData(x, self._ob)
        self.curve_msc.setData(x, self._msc)
        self.curve_fib.setData(x, self._fib)

    def load_result(self, result: SimulationResult) -> None:
        self.reset()
        for stats in result.history:
            self.append_step(stats)
