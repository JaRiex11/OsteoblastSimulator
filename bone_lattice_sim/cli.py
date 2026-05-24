"""
CLI для Спринта 1: генерация решётки и прогон симуляции без GUI.
"""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bone lattice simulator — 3D pore network colonization (Sprint 1 CLI)",
    )
    parser.add_argument("--size", type=int, default=10, help="Сторона кубической сетки N (N×N×N пор)")
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
        help="center | face (грань min-Z, контакт с тканью) | random",
    )
    parser.add_argument("--n-seeds", type=int, default=1, help="Число начальных клеток для initial=random")
    return parser


def main(argv: list[str] | None = None) -> int:
    from bone_lattice_sim.lattice.engine import build_lattice, average_degree, reachable_fraction
    from bone_lattice_sim.simulation.agents import parse_cell_type
    from bone_lattice_sim.simulation.simulation import (
        Simulation,
        SimulationConfig,
        build_initial_cells,
    )

    args = build_parser().parse_args(argv)

    if args.size < 2 or args.size > 30:
        print("Ошибка: --size должно быть от 2 до 30", file=sys.stderr)
        return 1

    lattice = build_lattice(
        args.size,
        args.preset,
        throat_deletion_fraction=args.deletion,
        seed=args.seed,
    )
    cell_type = parse_cell_type(args.cell_type)
    initial = build_initial_cells(
        lattice,
        args.initial,
        cell_type=cell_type,
        n_seeds=args.n_seeds,
        seed=args.seed,
    )

    sim = Simulation(
        lattice,
        initial,
        SimulationConfig(time_steps=args.steps, seed=args.seed),
    )
    result = sim.run()

    t50 = result.time_to_threshold(0.5)
    t90 = result.time_to_threshold(0.9)
    reach = reachable_fraction(lattice, [p for p, _ in initial])

    print("=== Bone Lattice Simulator (Sprint 1) ===")
    print(f"Preset: {args.preset}, size={args.size}^3, pores={lattice.n_pores}")
    print(f"Avg degree: {average_degree(lattice):.2f}, throats={lattice.meta.get('n_throats')}")
    print(f"Reachable from seed: {reach * 100:.1f}%")
    print(f"Initial cells: {len(initial)} ({args.cell_type}, {args.initial})")
    print(f"Steps: {args.steps}, seed: {args.seed}")
    print(f"Final occupancy: {result.final_occupancy * 100:.2f}%")
    print(f"Final cell count: {result.final_cell_count}")
    print(f"T50: {t50 if t50 is not None else 'n/a'}, T90: {t90 if t90 is not None else 'n/a'}")
    last = result.history[-1]
    print(
        f"Cell types: osteoblast={last.counts_by_type['osteoblast']}, "
        f"msc={last.counts_by_type['msc']}, "
        f"fibroblast={last.counts_by_type['fibroblast']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
