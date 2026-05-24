"""Вкладка параметров симуляции."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from bone_lattice_sim.io.settings import DEFAULT_SETTINGS, sanitize
from bone_lattice_sim.ui.help_text import CONFIG_HELP


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

    def _label(self, text: str, tip: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setToolTip(tip)
        return lbl

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        root = QVBoxLayout(inner)

        help_lbl = QLabel(CONFIG_HELP)
        help_lbl.setWordWrap(True)
        help_lbl.setTextFormat(Qt.TextFormat.RichText)
        help_lbl.setObjectName("configHelp")
        root.addWidget(help_lbl)

        s = DEFAULT_SETTINGS

        lattice_box = QGroupBox("Решётка (OpenPNM Cubic)")
        lattice_form = QFormLayout(lattice_box)
        self._fields["size"] = self._spin("size", 2, 30, s["size"])
        self._fields["size"].setToolTip("Сторона куба N: будет N×N×N пор (например 10 → 1000 пор).")
        lattice_form.addRow(
            self._label("Размер N (N^3 пор):", "2…30. Число пор = N³."),
            self._fields["size"],
        )

        preset = QComboBox()
        preset.addItems(["regular_6", "random", "full_26"])
        preset.setCurrentText(s["preset"])
        preset.setToolTip(
            "regular_6 — ортогональ; random — случайное удаление каналов; full_26 — все соседи 3×3×3.",
        )
        self._fields["preset"] = preset
        lattice_form.addRow(self._label("Топология:", preset.toolTip()), preset)

        self._fields["deletion"] = QDoubleSpinBox()
        self._fields["deletion"].setRange(0.0, 0.99)
        self._fields["deletion"].setSingleStep(0.05)
        self._fields["deletion"].setDecimals(2)
        self._fields["deletion"].setValue(s["deletion"])
        self._fields["deletion"].setToolTip("Только для random: доля удаляемых throats (0…0.99).")
        lattice_form.addRow(
            self._label("Доля удаления throats:", self._fields["deletion"].toolTip()),
            self._fields["deletion"],
        )

        cells_box = QGroupBox("Клетки и симуляция")
        cells_form = QFormLayout(cells_box)

        initial = QComboBox()
        initial.addItems(["center", "random"])
        initial.setCurrentText(s["initial_mode"])
        initial.setToolTip(
            "center — одна клетка (первый тип из «Состава») в центре; "
            "random — все клетки из «Состава» в случайных порах.",
        )
        self._fields["initial_mode"] = initial
        cells_form.addRow(self._label("Начальное размещение:", initial.toolTip()), initial)

        self._fields["n_seeds"] = self._spin("n_seeds", 1, 500, s["n_seeds"])
        self._fields["n_seeds"].setToolTip(
            "Для random: минимальное число пор, если в «Составе» клеток меньше.",
        )
        cells_form.addRow(
            self._label("Число пор (random):", self._fields["n_seeds"].toolTip()),
            self._fields["n_seeds"],
        )

        mix = QLineEdit(s["cell_mix"])
        mix.setPlaceholderText("osteoblast:1  |  fibroblast:3,msc:2")
        mix.setToolTip(
            "Формат: тип:число через запятую или ;\n"
            "Типы: osteoblast (ob), msc, fibroblast (fibro, fib)\n"
            "Примеры: osteoblast:1 | fibroblast:5 | osteoblast:2,msc:1",
        )
        self._fields["cell_mix"] = mix
        cells_form.addRow(
            self._label("Состав (тип:число):", mix.toolTip()),
            mix,
        )

        self._fields["time_steps"] = self._spin("time_steps", 1, 5000, s["time_steps"])
        self._fields["time_steps"].setToolTip("Дискретных шагов симуляции.")
        cells_form.addRow(self._label("Шагов симуляции:", ""), self._fields["time_steps"])

        self._fields["seed"] = self._spin("seed", 0, 2_000_000_000, s["seed"])
        self._fields["seed"].setToolTip("Зерно ГСЧ — одинаковый seed даёт тот же результат.")
        cells_form.addRow(self._label("Seed:", ""), self._fields["seed"])

        self._fields["update_every"] = self._spin("update_every", 1, 100, s["update_every"])
        self._fields["update_every"].setToolTip("Обновлять графики и 3D каждые K шагов.")
        cells_form.addRow(
            self._label("Обновление UI каждые K шагов:", ""),
            self._fields["update_every"],
        )

        prob_box = QGroupBox("Вероятности по типам клеток")
        prob_form = QFormLayout(prob_box)
        prob_form.addRow(
            QLabel("P_mig — попытка миграции; P_prol — деление (если миграция не выбрана)."),
        )
        for label, prefix in (
            ("Остеобласт (osteoblast)", "osteoblast"),
            ("МСК (msc)", "msc"),
            ("Фибробласт (fibroblast)", "fibroblast"),
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

        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def get_settings(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for key, widget in self._fields.items():
            if isinstance(widget, QComboBox):
                data[key] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                data[key] = widget.text().strip()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
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

    def validate_input(self) -> str | None:
        """Проверка полей; None если всё ок, иначе текст ошибки."""
        from bone_lattice_sim.simulation.simulation import parse_initial_cell_mix

        try:
            parse_initial_cell_mix(self._fields["cell_mix"].text())
        except ValueError as exc:
            return str(exc)
        return None
