"""Сохранение параметров GUI bone_lattice_sim в JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bone_lattice_sim.paths import project_root

SETTINGS_FILE = "bone_gui_settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "size": 10,
    "preset": "regular_6",
    "deletion": 0.3,
    "time_steps": 150,
    "seed": 42,
    "initial_mode": "center",
    "n_seeds": 5,
    "cell_mix": "osteoblast:1",
    "update_every": 5,
    "visual_update_every": 0,
    "record_animation": True,
    "animation_frame_every": 1,
    "osteoblast_p_migrate": 0.5,
    "osteoblast_p_prolif": 0.25,
    "msc_p_migrate": 0.35,
    "msc_p_prolif": 0.15,
    "fibroblast_p_migrate": 0.65,
    "fibroblast_p_prolif": 0.10,
    "cell_radius_pct": 24,
}

VALID_PRESETS = {"regular_6", "random", "full_26"}
VALID_INITIAL = {"center", "face", "random"}


def suggest_visual_update_every(size: int) -> int:
    """Рекомендуемый интервал обновления 3D (меньше нагрузка на UI)."""
    n_pores = size ** 3
    if n_pores > 8000:
        return 25
    if n_pores > 2000:
        return 15
    if n_pores > 500:
        return 10
    return 5


def settings_path() -> Path:
    return project_root() / SETTINGS_FILE


def load_settings() -> dict[str, Any]:
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
    return sanitize(merged)


def save_settings(data: dict[str, Any]) -> None:
    path = settings_path()
    payload = sanitize({**DEFAULT_SETTINGS, **data})
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def sanitize(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(DEFAULT_SETTINGS)

    try:
        out["size"] = min(30, max(2, int(data.get("size", out["size"]))))
    except (TypeError, ValueError):
        pass

    preset = str(data.get("preset", out["preset"])).strip()
    out["preset"] = preset if preset in VALID_PRESETS else DEFAULT_SETTINGS["preset"]

    try:
        out["deletion"] = min(0.99, max(0.0, float(data.get("deletion", out["deletion"]))))
    except (TypeError, ValueError):
        pass

    try:
        out["time_steps"] = max(1, int(data.get("time_steps", out["time_steps"])))
    except (TypeError, ValueError):
        pass

    try:
        out["seed"] = int(data.get("seed", out["seed"]))
    except (TypeError, ValueError):
        out["seed"] = DEFAULT_SETTINGS["seed"]

    mode = str(data.get("initial_mode", out["initial_mode"])).strip()
    out["initial_mode"] = mode if mode in VALID_INITIAL else DEFAULT_SETTINGS["initial_mode"]

    try:
        out["n_seeds"] = max(1, int(data.get("n_seeds", out["n_seeds"])))
    except (TypeError, ValueError):
        pass

    out["cell_mix"] = str(data.get("cell_mix", out["cell_mix"]) or "osteoblast:1").strip()

    try:
        out["update_every"] = max(1, int(data.get("update_every", out["update_every"])))
    except (TypeError, ValueError):
        pass

    try:
        raw_v = int(data.get("visual_update_every", out["visual_update_every"]))
        out["visual_update_every"] = max(0, raw_v)
    except (TypeError, ValueError):
        pass
    if out["visual_update_every"] == 0:
        out["visual_update_every"] = suggest_visual_update_every(out["size"])

    out["record_animation"] = bool(data.get("record_animation", out["record_animation"]))

    try:
        out["animation_frame_every"] = max(
            1, int(data.get("animation_frame_every", out["animation_frame_every"])),
        )
    except (TypeError, ValueError):
        pass

    try:
        out["cell_radius_pct"] = min(42, max(6, int(data.get("cell_radius_pct", out["cell_radius_pct"]))))
    except (TypeError, ValueError):
        pass

    for prefix in ("osteoblast", "msc", "fibroblast"):
        for suffix in ("p_migrate", "p_prolif"):
            key = f"{prefix}_{suffix}"
            try:
                val = float(data.get(key, out[key]))
                out[key] = min(1.0, max(0.0, val))
            except (TypeError, ValueError):
                pass

    return out
