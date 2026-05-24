"""Вкладка параметров симуляции."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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
        initial.addItems(["center", "face", "random"])
        initial.setCurrentText(s["initial_mode"])
        initial.setToolTip(
            "center — кластер клеток из «Состава» в порых, ближайших к центру объёма; "
            "face — спавн с грани min-Z (контакт с тканью); "
            "random — по всему объёму.",
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
        self._fields["update_every"].setToolTip("Обновлять графики каждые K шагов (лёгкая операция).")
        cells_form.addRow(
            self._label("Графики каждые K шагов:", ""),
            self._fields["update_every"],
        )

        self._fields["visual_update_every"] = self._spin(
            "visual_update_every", 0, 200, s["visual_update_every"],
        )
        self._fields["visual_update_every"].setToolTip(
            "Обновление 3D Viewer. 0 = авто (зависит от размера сетки). "
            "Больше K — меньше нагрузка, меньше подвисаний.",
        )
        cells_form.addRow(
            self._label("3D каждые K шагов (0=авто):", ""),
            self._fields["visual_update_every"],
        )

        chk_anim = QCheckBox("Записать кадры для анимации")
        chk_anim.setChecked(bool(s["record_animation"]))
        chk_anim.setToolTip(
            "После симуляции можно проиграть заполнение решётки на вкладке 3D Viewer.",
        )
        self._fields["record_animation"] = chk_anim
        cells_form.addRow("", chk_anim)

        self._fields["animation_frame_every"] = self._spin(
            "animation_frame_every", 1, 50, s["animation_frame_every"],
        )
        self._fields["animation_frame_every"].setToolTip(
            "Сохранять каждый N-й шаг в анимацию (1 = все шаги).",
        )
        cells_form.addRow(
            self._label("Кадр анимации каждые N шагов:", ""),
            self._fields["animation_frame_every"],
        )

        bio_box = QGroupBox("Физический режим (Biological Physics)")
        bio_form = QFormLayout(bio_box)
        chk_bio = QCheckBox("Пересчитать P_mig / P_prol из скоростей и T_div")
        chk_bio.setChecked(bool(s["biological_physics_mode"]))
        chk_bio.setToolTip(
            "dt = d / v_max; P_migrate = v·dt/d; P_prolif = dt/T_div. "
            "d=100 мкм; фибро 40 мкм/ч, МСК 20, остео 10.",
        )
        self._fields["biological_physics_mode"] = chk_bio
        bio_form.addRow(chk_bio)

        self._fields["pore_spacing_um"] = QDoubleSpinBox()
        self._fields["pore_spacing_um"].setRange(1.0, 1000.0)
        self._fields["pore_spacing_um"].setDecimals(1)
        self._fields["pore_spacing_um"].setSuffix(" мкм")
        self._fields["pore_spacing_um"].setValue(float(s["pore_spacing_um"]))
        self._fields["pore_spacing_um"].setToolTip(
            "Среднее расстояние между центрами соседних пор (d).",
        )
        bio_form.addRow(
            self._label("Расстояние между порами d:", self._fields["pore_spacing_um"].toolTip()),
            self._fields["pore_spacing_um"],
        )
        self._lbl_bio_dt = QLabel("")
        self._lbl_bio_dt.setWordWrap(True)
        bio_form.addRow("Шаг dt:", self._lbl_bio_dt)
        chk_bio.toggled.connect(self._update_biophysics_ui)
        self._fields["pore_spacing_um"].valueChanged.connect(self._update_biophysics_ui)

        prob_box = QGroupBox("Вероятности по типам клеток")
        prob_form = QFormLayout(prob_box)
        prob_form.addRow(
            QLabel("P_mig — попытка миграции; P_prol — деление (если миграция не выбрана)."),
        )
        self._prob_spinboxes: list[QDoubleSpinBox] = []
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
            self._prob_spinboxes.extend((pm, pp))

        root.addWidget(lattice_box)
        root.addWidget(cells_box)
        root.addWidget(bio_box)
        root.addWidget(prob_box)
        self._update_biophysics_ui()
        root.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def get_settings(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for key, widget in self._fields.items():
            if isinstance(widget, QCheckBox):
                data[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
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
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(val))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(val))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(val))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(val))
        self._update_biophysics_ui()

    def _update_biophysics_ui(self) -> None:
        from bone_lattice_sim.simulation.agents import CellType
        from bone_lattice_sim.simulation.biophysics import compute_biophysics_calibration

        enabled = self._fields["biological_physics_mode"].isChecked()
        self._fields["pore_spacing_um"].setEnabled(enabled)
        for spin in self._prob_spinboxes:
            spin.setEnabled(not enabled)
        if enabled:
            cal = compute_biophysics_calibration(
                pore_spacing_um=self._fields["pore_spacing_um"].value(),
            )
            mapping = {
                "osteoblast": CellType.OSTEOBLAST,
                "msc": CellType.MSC,
                "fibroblast": CellType.FIBROBLAST,
            }
            for prefix, ct in mapping.items():
                p = cal.type_params[ct]
                self._fields[f"{prefix}_p_migrate"].setValue(p.p_migrate)
                self._fields[f"{prefix}_p_prolif"].setValue(p.p_prolif)
            self._lbl_bio_dt.setText(
                f"dt = {cal.dt_hours:.2f} ч/шаг (v_max = {cal.v_max_um_h:.0f} мкм/ч, d = {cal.pore_spacing_um:.0f} мкм)",
            )
        else:
            self._lbl_bio_dt.setText("— (абстрактные вероятности)")

    def validate_input(self) -> str | None:
        """Проверка полей; None если всё ок, иначе текст ошибки."""
        from bone_lattice_sim.simulation.simulation import parse_initial_cell_mix

        try:
            parse_initial_cell_mix(self._fields["cell_mix"].text())
        except ValueError as exc:
            return str(exc)
        return None
