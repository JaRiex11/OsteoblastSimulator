"""Вкладка параметров симуляции."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from bone_lattice_sim.io.settings import DEFAULT_SETTINGS, sanitize


class ConfigTab(QWidget):
    """Поля конфигурации решётки и клеток."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._fields: dict[str, Any] = {}
        self._build()

    def _spin(self, key: str, lo: int, hi: int, val: int) -> QSpinBox:
        w = QSpinBox()
        w.setRange(lo, hi)
        w.setValue(val)
        self._fields[key] = w
        return w

    def _double(self, key: str, val: float) -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(0.0, 1.0)
        w.setSingleStep(0.05)
        w.setDecimals(2)
        w.setValue(val)
        self._fields[key] = w
        return w

    def _build(self) -> None:
        root = QVBoxLayout(self)
        s = DEFAULT_SETTINGS

        lattice_box = QGroupBox("Решётка (OpenPNM Cubic)")
        lattice_form = QFormLayout(lattice_box)
        self._fields["size"] = self._spin("size", 2, 30, s["size"])
        lattice_form.addRow("Размер N (N^3 пор):", self._fields["size"])

        preset = QComboBox()
        preset.addItems(["regular_6", "random", "full_26"])
        preset.setCurrentText(s["preset"])
        self._fields["preset"] = preset
        lattice_form.addRow("Топология:", preset)

        self._fields["deletion"] = QDoubleSpinBox()
        self._fields["deletion"].setRange(0.0, 0.99)
        self._fields["deletion"].setSingleStep(0.05)
        self._fields["deletion"].setDecimals(2)
        self._fields["deletion"].setValue(s["deletion"])
        lattice_form.addRow("Доля удаления throats (random):", self._fields["deletion"])

        cells_box = QGroupBox("Клетки и симуляция")
        cells_form = QFormLayout(cells_box)

        initial = QComboBox()
        initial.addItems(["center", "random"])
        initial.setCurrentText(s["initial_mode"])
        self._fields["initial_mode"] = initial
        cells_form.addRow("Начальное размещение:", initial)

        self._fields["n_seeds"] = self._spin("n_seeds", 1, 500, s["n_seeds"])
        cells_form.addRow("Число пор (random):", self._fields["n_seeds"])

        mix = QLineEdit(s["cell_mix"])
        mix.setPlaceholderText("osteoblast:1  или  osteoblast:3,msc:2")
        self._fields["cell_mix"] = mix
        cells_form.addRow("Состав (тип:число):", mix)

        self._fields["time_steps"] = self._spin("time_steps", 1, 5000, s["time_steps"])
        cells_form.addRow("Шагов симуляции:", self._fields["time_steps"])

        self._fields["seed"] = self._spin("seed", 0, 2_000_000_000, s["seed"])
        cells_form.addRow("Seed:", self._fields["seed"])

        self._fields["update_every"] = self._spin("update_every", 1, 100, s["update_every"])
        cells_form.addRow("Обновление графика каждые K шагов:", self._fields["update_every"])

        prob_box = QGroupBox("Вероятности по типам клеток")
        prob_form = QFormLayout(prob_box)
        for label, prefix in (
            ("Остеобласт", "osteoblast"),
            ("МСК", "msc"),
            ("Фибробласт", "fibroblast"),
        ):
            row = QHBoxLayout()
            pm = self._double(f"{prefix}_p_migrate", s[f"{prefix}_p_migrate"])
            pp = self._double(f"{prefix}_p_prolif", s[f"{prefix}_p_prolif"])
            row.addWidget(QLabel("P_mig"))
            row.addWidget(pm)
            row.addWidget(QLabel("P_prol"))
            row.addWidget(pp)
            prob_form.addRow(label + ":", row)

        root.addWidget(lattice_box)
        root.addWidget(cells_box)
        root.addWidget(prob_box)
        root.addStretch()

    def get_settings(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for key, widget in self._fields.items():
            if isinstance(widget, QComboBox):
                data[key] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                data[key] = widget.text().strip()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                if isinstance(widget, QDoubleSpinBox) and key == "deletion":
                    data[key] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    data[key] = widget.value()
                else:
                    data[key] = widget.value()
        return sanitize(data)

    def set_settings(self, settings: dict[str, Any]) -> None:
        s = sanitize(settings)
        for key, widget in self._fields.items():
            if key not in s:
                continue
            val = s[key]
            if isinstance(widget, QComboBox):
                widget.setCurrentText(str(val))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(val))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(val))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(val))
