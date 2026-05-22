"""
Построение графов пористой (решётчатой) структуры имплантата.
"""

from __future__ import annotations

import math
from typing import Literal

import networkx as nx

GraphType = Literal["grid_2d", "random", "small_world"]

GRAPH_TYPES: dict[str, GraphType] = {
    "grid_2d": "grid_2d",
    "random": "random",
    "small_world": "small_world",
}


def normalize_graph_type(graph_type: str) -> GraphType:
    key = graph_type.lower().strip()
    if key not in GRAPH_TYPES:
        raise ValueError(
            f"Неизвестный тип графа: {graph_type!r}. Допустимо: {', '.join(GRAPH_TYPES)}"
        )
    return GRAPH_TYPES[key]


def _validate_positive_int(name: str, value: int) -> None:
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} должно быть целым числом >= 1, получено: {value!r}")


def _validate_probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} должно быть в [0, 1], получено: {value}")


def create_grid_2d(size: int | None = None, nodes: int | None = None) -> nx.Graph:
    if size is None and nodes is None:
        size = 10
    if size is None and nodes is not None:
        _validate_positive_int("nodes", nodes)
        size = max(2, int(math.ceil(math.sqrt(nodes))))
    if size is not None:
        _validate_positive_int("size", size)

    graph = nx.grid_graph(dim=(size, size))
    graph = nx.convert_node_labels_to_integers(graph)
    if nodes is not None and graph.number_of_nodes() > nodes:
        graph.remove_nodes_from(list(graph.nodes())[nodes:])

    graph.graph["grid_rows"] = size
    graph.graph["grid_cols"] = size
    graph.graph["layout"] = "grid_2d"
    return graph


def create_random_lattice(
    nodes: int,
    degree: int = 4,
    edge_probability: float | None = None,
    seed: int | None = None,
) -> nx.Graph:
    _validate_positive_int("nodes", nodes)
    if edge_probability is None:
        _validate_positive_int("degree", degree)
        edge_probability = min(1.0, degree / (nodes - 1)) if nodes > 1 else 0.0
    else:
        _validate_probability("edge_probability", edge_probability)

    graph = nx.erdos_renyi_graph(nodes, edge_probability, seed=seed)
    if not nx.is_connected(graph) and nodes > 1:
        comps = list(nx.connected_components(graph))
        for i in range(len(comps) - 1):
            graph.add_edge(next(iter(comps[i])), next(iter(comps[i + 1])))
    graph.graph["layout"] = "spring"
    return graph


def create_small_world_lattice(
    nodes: int,
    degree: int = 4,
    rewiring_probability: float = 0.1,
    seed: int | None = None,
) -> nx.Graph:
    _validate_positive_int("nodes", nodes)
    _validate_positive_int("degree", degree)
    _validate_probability("rewiring_probability", rewiring_probability)
    k = degree if degree % 2 == 0 else degree + 1
    k = min(max(k, 2), nodes - 1) if nodes > 2 else 1
    graph = nx.watts_strogatz_graph(nodes, k, rewiring_probability, seed=seed)
    graph.graph["layout"] = "spring"
    return graph


def build_graph(
    graph_type: str,
    *,
    size: int | None = None,
    nodes: int | None = None,
    degree: int = 4,
    edge_probability: float | None = None,
    rewiring_probability: float = 0.1,
    seed: int | None = None,
) -> nx.Graph:
    kind = normalize_graph_type(graph_type)
    if kind == "grid_2d":
        return create_grid_2d(size=size, nodes=nodes)
    if kind == "random":
        n = nodes or (size * size if size else 100)
        return create_random_lattice(n, degree=degree, edge_probability=edge_probability, seed=seed)
    n = nodes or (size * size if size else 100)
    return create_small_world_lattice(
        n, degree=degree, rewiring_probability=rewiring_probability, seed=seed
    )


def graph_summary(graph: nx.Graph) -> str:
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    avg_degree = (2 * m / n) if n else 0.0
    connected = nx.is_connected(graph) if n > 0 else True
    layout = graph.graph.get("layout", "spring")
    extra = ""
    if "grid_rows" in graph.graph:
        extra = f", сетка {graph.graph['grid_rows']}x{graph.graph['grid_cols']}"
    return (
        f"Вершин: {n}, рёбер: {m}, средняя степень: {avg_degree:.2f}, "
        f"связный: {connected}, раскладка: {layout}{extra}"
    )


def average_degree(graph: nx.Graph) -> float:
    n = graph.number_of_nodes()
    return (2 * graph.number_of_edges() / n) if n else 0.0
