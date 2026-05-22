"""Сборка графа и запуск одного эксперимента."""

from __future__ import annotations

import argparse

from osteoblast_sim.graph.builder import build_graph, graph_summary, normalize_graph_type
from osteoblast_sim.simulation.engine import (
    OsteoblastSimulation,
    SimulationConfig,
    parse_initial_cells,
)


def build_experiment_graph(args: argparse.Namespace):
    size, nodes = args.size, args.nodes
    kind = normalize_graph_type(args.graph_type)
    if kind == "grid_2d" and size is None and nodes is None:
        size = 10
    if kind != "grid_2d" and nodes is None:
        nodes = (size * size if size else None) or 100
    return build_graph(
        args.graph_type,
        size=size,
        nodes=nodes,
        degree=args.degree,
        edge_probability=args.edge_probability,
        rewiring_probability=args.rewiring_probability,
        seed=args.seed,
    )


def run_experiment(args: argparse.Namespace):
    graph = build_experiment_graph(args)
    print(graph_summary(graph))

    initial = parse_initial_cells(
        args.initial_cells, graph.number_of_nodes(),
        n_seeds=args.n_seeds, seed=args.seed,
    )
    print(f"Начальные клетки: {initial}")

    config = SimulationConfig(
        p_migrate=args.p_migrate,
        p_prolif=args.p_prolif,
        time_steps=args.time_steps,
        seed=args.seed,
    )
    sim = OsteoblastSimulation(graph, initial_vertices=initial, config=config)
    record = args.animate or args.color_mode == "colonization"
    result = sim.run(record_history=record)
    return sim, result
