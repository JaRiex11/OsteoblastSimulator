"""
Экспорт результатов симуляции: CSV, JSON, VTK, графики PNG.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from bone_lattice_sim.experiment import result_summary
from bone_lattice_sim.io.run_bundle import SimulationRun
from bone_lattice_sim.lattice.engine import LatticeGraph
from bone_lattice_sim.paths import ensure_output_dir
from bone_lattice_sim.simulation.stats import SimulationResult
from bone_lattice_sim.viz.snapshot import build_visual_context


def _timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def export_timeseries_csv(path: str | Path, result: SimulationResult) -> Path:
    """CSV: шаг, занятость, число клеток, типы, события миграции/пролиферации."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "step",
            "occupancy_fraction",
            "cell_count",
            "osteoblast",
            "msc",
            "fibroblast",
            "migrate_events",
            "prolif_events",
        ])
        for s in result.history:
            writer.writerow([
                s.step,
                f"{s.occupancy:.6f}",
                s.cell_count,
                s.counts_by_type.get("osteoblast", 0),
                s.counts_by_type.get("msc", 0),
                s.counts_by_type.get("fibroblast", 0),
                s.migrate_events,
                s.prolif_events,
            ])
    return path


def export_run_json(path: str | Path, run: SimulationRun) -> Path:
    """JSON: параметры, метаданные решётки, начальные и финальные клетки, T50/T90."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    result = run.result
    payload: dict[str, Any] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "settings": run.settings,
        "lattice": {
            "n_pores": run.lattice.n_pores,
            "meta": run.lattice.meta,
        },
        "initial_cells": [
            {"pore": p, "type": t.value} for p, t in run.initial
        ],
        "final_cells": run.final_cells,
        "summary": {
            "text": result_summary(result),
            "final_occupancy": result.final_occupancy,
            "final_cell_count": result.final_cell_count,
            "t50": result.time_to_threshold(0.5),
            "t90": result.time_to_threshold(0.9),
            "cancelled_early": run.cancelled_early,
        },
        "occupancy_history": result.occupancy_history,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def export_lattice_csv(path: str | Path, lattice: LatticeGraph) -> Path:
    """CSV списка пор (координаты) и throats (пары индексов)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["section", "pore_id", "x", "y", "z", "n1", "n2"])
        for i, (x, y, z) in enumerate(lattice.coords):
            writer.writerow(["pore", i, x, y, z, "", ""])
        ctx = build_visual_context(lattice)
        for u, v in ctx.edges:
            writer.writerow(["throat", "", "", "", "", u, v])
    return path


def export_lattice_vtk(path: str | Path, lattice: LatticeGraph) -> Path:
    """VTK: линии throats + точки пор (ParaView / PyVista)."""
    import pyvista as pv

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ctx = build_visual_context(lattice)
    coords = ctx.coords

    if ctx.edges.size > 0:
        cells = np.hstack([
            np.full((len(ctx.edges), 1), 2, dtype=np.int64),
            ctx.edges,
        ]).ravel()
        mesh = pv.PolyData(coords, lines=cells)
    else:
        mesh = pv.PolyData(coords)

    mesh["pore_id"] = np.arange(lattice.n_pores)
    mesh.save(str(path))
    return path


def export_charts_png(path: str | Path, result: SimulationResult) -> Path:
    """PNG: занятость и клетки по типам (matplotlib, без GUI)."""
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    steps = [s.step for s in result.history]
    occ = [s.occupancy for s in result.history]
    ob = [s.counts_by_type.get("osteoblast", 0) for s in result.history]
    msc = [s.counts_by_type.get("msc", 0) for s in result.history]
    fib = [s.counts_by_type.get("fibroblast", 0) for s in result.history]

    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    axes[0].plot(steps, occ, color="#2ecc71", linewidth=2)
    axes[0].set_ylabel("Occupancy")
    axes[0].set_ylim(0, 1.05)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title("Pore occupancy")

    axes[1].plot(steps, ob, label="Osteoblast", color="#27ae60")
    axes[1].plot(steps, msc, label="MSC", color="#3498db")
    axes[1].plot(steps, fib, label="Fibroblast", color="#e74c3c")
    axes[1].set_xlabel("Step")
    axes[1].set_ylabel("Cell count")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def export_full_run(
    run: SimulationRun,
    output_dir: str | Path | None = None,
    *,
    prefix: str | None = None,
) -> dict[str, Path]:
    """
    Сохранить полный набор артефактов в output/<prefix>/.

    Returns:
        словарь {имя_файла: путь}
    """
    base = Path(output_dir) if output_dir else ensure_output_dir()
    tag = prefix or f"run_{_timestamp()}"
    folder = base / tag
    folder.mkdir(parents=True, exist_ok=True)

    paths = {
        "timeseries.csv": export_timeseries_csv(folder / "timeseries.csv", run.result),
        "run.json": export_run_json(folder / "run.json", run),
        "lattice_pores_throats.csv": export_lattice_csv(folder / "lattice.csv", run.lattice),
        "lattice.vtk": export_lattice_vtk(folder / "lattice.vtk", run.lattice),
        "charts.png": export_charts_png(folder / "charts.png", run.result),
    }
    return paths
