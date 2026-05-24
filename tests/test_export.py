"""Тесты экспорта CSV/JSON/VTK."""

from __future__ import annotations

import json
from pathlib import Path

from bone_lattice_sim.experiment import create_simulation
from bone_lattice_sim.io.export import export_full_run, export_timeseries_csv
from bone_lattice_sim.io.run_bundle import build_run_bundle
from bone_lattice_sim.io.settings import sanitize


def _quick_run(initial_mode: str = "face"):
    settings = sanitize({
        "size": 5,
        "preset": "regular_6",
        "time_steps": 5,
        "seed": 1,
        "initial_mode": initial_mode,
        "cell_mix": "osteoblast:1",
    })
    sim, lattice, initial = create_simulation(None, settings)
    result = sim.run()
    return build_run_bundle(sim, lattice, settings, initial, result)


def test_export_timeseries_csv(tmp_path: Path):
    run = _quick_run("center")
    path = export_timeseries_csv(tmp_path / "ts.csv", run.result)
    text = path.read_text(encoding="utf-8")
    assert "occupancy_fraction" in text
    assert text.count("\n") >= 3


def test_export_full_run_face_spawn(tmp_path: Path):
    run = _quick_run("face")
    assert len(run.initial) == 1
    paths = export_full_run(run, tmp_path, prefix="test_face")
    assert paths["run.json"].is_file()
    assert paths["lattice.vtk"].is_file()
    data = json.loads(paths["run.json"].read_text(encoding="utf-8"))
    assert data["settings"]["initial_mode"] == "face"
    assert data["initial_cells"][0]["type"] == "osteoblast"
