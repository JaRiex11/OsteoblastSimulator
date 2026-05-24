"""
CLI: генерация решётки, симуляция, опциональный экспорт.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bone lattice simulator — 3D pore network colonization",
    )
    parser.add_argument("--size", type=int, default=10, help="Сторона кубической сетки N (N^3 пор)")
    parser.add_argument(
        "--preset",
        choices=["regular_6", "random", "full_26"],
        default="regular_6",
        help="Тип топологии решётки",
    )
    parser.add_argument(
        "--deletion",
        type=float,
        default=0.3,
        help="Доля удаляемых throats для preset=random",
    )
    parser.add_argument("--steps", type=int, default=100, help="Число шагов симуляции")
    parser.add_argument("--seed", type=int, default=42, help="Зерно ГСЧ")
    parser.add_argument(
        "--cell-type",
        choices=["osteoblast", "msc", "fibroblast"],
        default="osteoblast",
    )
    parser.add_argument(
        "--initial",
        choices=["center", "face", "random"],
        default="center",
        help="center | face (грань min-Z) | random",
    )
    parser.add_argument("--n-seeds", type=int, default=1, help="Число начальных клеток для initial=random")
    parser.add_argument(
        "--export-dir",
        type=str,
        default=None,
        help="Папка для CSV/JSON/VTK/PNG (подпапка run_* создаётся автоматически)",
    )
    parser.add_argument(
        "--biophysics",
        action="store_true",
        help="Режим Biological Physics: P_mig/P_prol из физических констант",
    )
    return parser


def _settings_from_args(args: argparse.Namespace) -> dict:
    from bone_lattice_sim.io.settings import sanitize

    return sanitize({
        "size": args.size,
        "preset": args.preset,
        "deletion": args.deletion,
        "time_steps": args.steps,
        "seed": args.seed,
        "initial_mode": args.initial,
        "n_seeds": args.n_seeds,
        "cell_mix": f"{args.cell_type}:1",
        "biological_physics_mode": args.biophysics,
        "osteoblast_p_migrate": 0.5,
        "osteoblast_p_prolif": 0.25,
        "msc_p_migrate": 0.35,
        "msc_p_prolif": 0.15,
        "fibroblast_p_migrate": 0.65,
        "fibroblast_p_prolif": 0.10,
    })


def main(argv: list[str] | None = None) -> int:
    from bone_lattice_sim.experiment import (
        create_simulation,
        lattice_summary,
        result_summary,
        simulation_config_from_settings,
    )
    from bone_lattice_sim.io.export import export_full_run
    from bone_lattice_sim.io.run_bundle import build_run_bundle
    from bone_lattice_sim.lattice.engine import average_degree, reachable_fraction

    args = build_parser().parse_args(argv)

    if args.size < 2 or args.size > 30:
        print("Ошибка: --size должно быть от 2 до 30", file=sys.stderr)
        return 1

    settings = _settings_from_args(args)
    config = simulation_config_from_settings(settings)
    if config.dt_hours is not None:
        print(f"Biophysics: dt = {config.dt_hours:.3f} h/step")
    sim, lattice, initial = create_simulation(None, settings)
    result = sim.run()
    bundle = build_run_bundle(sim, lattice, settings, initial, result)

    t50 = result.time_to_threshold(0.5)
    t90 = result.time_to_threshold(0.9)
    reach = reachable_fraction(lattice, [p for p, _ in initial])

    print("=== Bone Lattice Simulator ===")
    print(lattice_summary(lattice, initial))
    print(f"Steps: {args.steps}, seed: {args.seed}, initial={args.initial}")
    print(result_summary(result))
    print(f"T50: {t50 if t50 is not None else 'n/a'}, T90: {t90 if t90 is not None else 'n/a'}")

    if args.export_dir:
        out = Path(args.export_dir)
        paths = export_full_run(bundle, out)
        print(f"Экспорт в {paths['timeseries.csv'].parent}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
