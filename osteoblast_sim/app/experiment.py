"""
Связка «параметры эксперимента → граф → симуляция → результат».

Используется и CLI, и GUI: оба передают argparse.Namespace с одними полями,
чтобы логика опыта не дублировалась.
"""

from __future__ import annotations

import argparse

from osteoblast_sim.graph.builder import (
    GRID_LAYOUT_TYPES,
    build_graph,
    graph_summary,
    normalize_graph_type,
)
from osteoblast_sim.simulation.engine import (
    OsteoblastSimulation,
    SimulationConfig,
    parse_initial_cells,
)


def build_experiment_graph(args: argparse.Namespace):
    """
    Построить граф по полям args (graph_type, size, nodes, degree, …).

    Подставляет разумные значения по умолчанию, если пользователь
    не указал size/nodes (см. нормализацию в build_graph).
    """
    size, nodes = args.size, args.nodes
    kind = normalize_graph_type(args.graph_type)

    # Для сеточных типов без параметров — 10×10
    if kind in GRID_LAYOUT_TYPES and size is None and nodes is None:
        size = 10
    # Для random/small_world без nodes — 100 пор
    if kind not in GRID_LAYOUT_TYPES and nodes is None:
        nodes = (size * size if size else None) or 100

    return build_graph(
        args.graph_type,
        size=size,
        nodes=nodes,
        degree=args.degree,
        edge_probability=args.edge_probability,
        rewiring_probability=args.rewiring_probability,
        diagonals=getattr(args, "diagonals", False),
        seed=args.seed,
    )


def run_experiment(args: argparse.Namespace):
    """
    Полный цикл одного прогона.

    Возвращает (sim, result): sim — для финальной визуализации (occupied, colonization_step),
    result — истории и метрики.

    record_history включается при анимации или раскраске colonization —
    иначе снимки по шагам не нужны и экономят память.
    """
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
