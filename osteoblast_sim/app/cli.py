"""Командная строка для пакетных экспериментов."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from osteoblast_sim.app.experiment import run_experiment
from osteoblast_sim.paths import ensure_output_dir
from osteoblast_sim.simulation.engine import export_results_csv
from osteoblast_sim.visualization.charts import (
    ColorMode,
    animate_simulation,
    format_statistics,
    plot_occupancy_curve,
    save_figure,
    save_graph_png,
    show_dashboard,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Симулятор остеобластов в пористом имплантате",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    g = parser.add_argument_group("Граф")
    g.add_argument("--graph-type", default="grid_2d", choices=["grid_2d", "random", "small_world"])
    g.add_argument("--size", type=int, default=None, help="Сторона 2D-сетки")
    g.add_argument("--nodes", type=int, default=None, help="Число пор")
    g.add_argument("--degree", type=int, default=4, help="Средняя степень связности")
    g.add_argument("--edge-probability", type=float, default=None)
    g.add_argument("--rewiring-probability", type=float, default=0.1)

    b = parser.add_argument_group("Биология")
    b.add_argument("--p-migrate", type=float, default=0.7, dest="p_migrate")
    b.add_argument("--p-prolif", type=float, default=0.3, dest="p_prolif")

    s = parser.add_argument_group("Симуляция")
    s.add_argument("--time-steps", type=int, default=200)
    s.add_argument("--initial-cells", default="center", dest="initial_cells")
    s.add_argument("--n-seeds", type=int, default=1)
    s.add_argument("--seed", type=int, default=None)

    v = parser.add_argument_group("Вывод")
    v.add_argument("--color-mode", choices=["occupancy", "colonization", "local_density"], default="occupancy")
    v.add_argument("--animate", action="store_true")
    v.add_argument("--no-show", action="store_true")
    v.add_argument("--save-csv", type=str, default=None)
    v.add_argument("--save-plot", type=str, default=None)
    v.add_argument("--save-graph", type=str, default=None)
    v.add_argument("--gui", action="store_true", help="Графический интерфейс")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.gui:
        from osteoblast_sim.app.gui import launch_gui
        launch_gui()
        return 0

    try:
        sim, result = run_experiment(args)
    except (ValueError, ImportError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print(format_statistics(result))
    out = ensure_output_dir()

    csv_path = args.save_csv
    if csv_path:
        p = Path(csv_path)
        if not p.is_absolute():
            p = out / p.name
        export_results_csv(str(p), result)
        print(f"CSV: {p.resolve()}")

    import matplotlib.pyplot as plt

    if args.save_plot:
        p = Path(args.save_plot)
        if not p.is_absolute():
            p = out / p.name
        plot_occupancy_curve(result)
        save_figure(p)
        print(f"График: {p.resolve()}")
        if args.no_show:
            plt.close("all")

    if args.save_graph:
        p = Path(args.save_graph)
        if not p.is_absolute():
            p = out / p.name
        save_graph_png(sim.graph, sim, p, color_mode=args.color_mode)
        print(f"Схема: {p.resolve()}")

    if not args.no_show:
        mode: ColorMode = args.color_mode
        if args.animate and result.occupied_sets:
            animate_simulation(sim.graph, result, color_mode=mode)
        else:
            show_dashboard(sim.graph, sim, result, color_mode=mode)
    return 0
