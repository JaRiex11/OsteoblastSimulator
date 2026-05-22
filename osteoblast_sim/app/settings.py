"""
Сохранение последних параметров GUI между запусками.

Файл gui_settings.json лежит рядом с .exe (или run.py).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from osteoblast_sim.paths import project_root

SETTINGS_FILE = "gui_settings.json"

# Значения по умолчанию
DEFAULT_SETTINGS: dict[str, Any] = {
    "graph_type": "grid_2d",
    "size": 10,
    "nodes": "",
    "degree": 4,
    "p_migrate": 0.6,
    "p_prolif": 0.25,
    "time_steps": 150,
    "initial_cells": "center",
    "seed": "",
    "color_mode": "occupancy",
    "animate": False,
}

VALID_GRAPH_TYPES = {"grid_2d", "random", "small_world"}
VALID_COLOR_MODES = {"occupancy", "colonization", "local_density"}


def settings_path() -> Path:
    return project_root() / SETTINGS_FILE


def load_gui_settings() -> dict[str, Any]:
    """Загрузить сохранённые параметры или вернуть значения по умолчанию."""
    path = settings_path()
    if not path.is_file():
        return dict(DEFAULT_SETTINGS)

    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)

    if not isinstance(data, dict):
        return dict(DEFAULT_SETTINGS)

    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return _sanitize(merged)


def save_gui_settings(data: dict[str, Any]) -> None:
    """Записать параметры в gui_settings.json."""
    path = settings_path()
    payload = _sanitize({**DEFAULT_SETTINGS, **data})
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # не блокируем работу GUI при ошибке записи


def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    """Проверка и приведение типов перед применением в GUI."""
    out = dict(DEFAULT_SETTINGS)

    gt = str(data.get("graph_type", out["graph_type"])).strip()
    out["graph_type"] = gt if gt in VALID_GRAPH_TYPES else DEFAULT_SETTINGS["graph_type"]

    try:
        out["size"] = max(1, int(data.get("size", out["size"])))
    except (TypeError, ValueError):
        out["size"] = DEFAULT_SETTINGS["size"]

    out["nodes"] = str(data.get("nodes", out["nodes"]) or "").strip()

    try:
        out["degree"] = max(1, int(data.get("degree", out["degree"])))
    except (TypeError, ValueError):
        out["degree"] = DEFAULT_SETTINGS["degree"]

    for key in ("p_migrate", "p_prolif"):
        try:
            val = float(data.get(key, out[key]))
            out[key] = min(1.0, max(0.0, val))
        except (TypeError, ValueError):
            out[key] = DEFAULT_SETTINGS[key]

    try:
        out["time_steps"] = max(1, int(data.get("time_steps", out["time_steps"])))
    except (TypeError, ValueError):
        out["time_steps"] = DEFAULT_SETTINGS["time_steps"]

    out["initial_cells"] = str(data.get("initial_cells", out["initial_cells"]) or "center").strip()

    out["seed"] = str(data.get("seed", out["seed"]) or "").strip()

    cm = str(data.get("color_mode", out["color_mode"])).strip()
    out["color_mode"] = cm if cm in VALID_COLOR_MODES else DEFAULT_SETTINGS["color_mode"]

    out["animate"] = bool(data.get("animate", out["animate"]))

    return out


def settings_to_fields_dict(saved: dict[str, Any]) -> dict[str, Any]:
    """Словарь для инициализации tk.Variable."""
    s = _sanitize(saved)
    return s


def fields_to_settings_dict(fields: dict) -> dict[str, Any]:
    """Собрать текущие значения из полей GUI для сохранения."""
    return {
        "graph_type": fields["graph_type"].get(),
        "size": fields["size"].get(),
        "nodes": fields["nodes"].get().strip(),
        "degree": fields["degree"].get(),
        "p_migrate": fields["p_migrate"].get(),
        "p_prolif": fields["p_prolif"].get(),
        "time_steps": fields["time_steps"].get(),
        "initial_cells": fields["initial_cells"].get(),
        "seed": fields["seed"].get().strip(),
        "color_mode": fields["color_mode"].get(),
        "animate": fields["animate"].get(),
    }
