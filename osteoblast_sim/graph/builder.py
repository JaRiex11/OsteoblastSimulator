"""
Построение графов пористой (решётчатой) структуры имплантата.

Модель: вершина = пора, ребро = канал между соседними порами.
Тип графа задаёт геометрию/топологию решётки для сравнения в курсовой:
  - grid_2d           — регулярная lattice (все соседние связи);
  - grid_2d_random    — те же узлы на плоскости, bond percolation по пулу
                        ортогональных и (опц.) планарных диагоналей 2×2;
  - random            — нерегулярная пористость (не планарная раскладка);
  - small_world       — локальная связность + редкие «дальние» каналы.
"""

from __future__ import annotations

import math
import random
from typing import Literal

import networkx as nx

# Допустимые типы для подсказок типизации и проверки ввода
GraphType = Literal["grid_2d", "grid_2d_random", "random", "small_world"]

GRAPH_TYPES: dict[str, GraphType] = {
    "grid_2d": "grid_2d",
    "grid_2d_random": "grid_2d_random",
    "random_grid": "grid_2d_random",
    "planar_random_grid": "grid_2d_random",
    "random": "random",
    "small_world": "small_world",
}

# Типы с координатной сеткой (для раскладки и параметров size/nodes)
GRID_LAYOUT_TYPES = frozenset({"grid_2d", "grid_2d_random"})


def normalize_graph_type(graph_type: str) -> GraphType:
    """Привести строку из GUI/CLI к одному из канонических имён."""
    key = graph_type.lower().strip()
    if key not in GRAPH_TYPES:
        raise ValueError(
            f"Неизвестный тип графа: {graph_type!r}. Допустимо: {', '.join(GRAPH_TYPES)}"
        )
    return GRAPH_TYPES[key]


def _validate_positive_int(name: str, value: int) -> None:
    """Защита от нулевого или отрицательного числа пор/размера сетки."""
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} должно быть целым числом >= 1, получено: {value!r}")


def _validate_probability(name: str, value: float) -> None:
    """Вероятности в модели всегда из отрезка [0, 1]."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} должно быть в [0, 1], получено: {value}")


def create_grid_2d(size: int | None = None, nodes: int | None = None) -> nx.Graph:
    """
    Регулярная 2D-решётка (ортогональная проекция кубической решётки).

    Зачем: baseline для lattice-based модели (Khayyeri et al.) — каждая внутренняя
    пора имеет до 4 соседей по сторонам.

    Как: NetworkX grid_graph, метки узлов — целые 0..N-1 для простой визуализации.
    В graph.graph сохраняем grid_rows/cols — визуализатор рисует узлы в сетке.
    """
    if size is None and nodes is None:
        size = 10
    # Если задано только число узлов — подбираем сторону квадрата
    if size is None and nodes is not None:
        _validate_positive_int("nodes", nodes)
        size = max(2, int(math.ceil(math.sqrt(nodes))))
    if size is not None:
        _validate_positive_int("size", size)

    graph = nx.grid_graph(dim=(size, size))
    graph = nx.convert_node_labels_to_integers(graph)

    # Обрезка, если нужно ровно nodes пор, а не полный квадрат
    if nodes is not None and graph.number_of_nodes() > nodes:
        graph.remove_nodes_from(list(graph.nodes())[nodes:])

    graph.graph["grid_rows"] = size
    graph.graph["grid_cols"] = size
    graph.graph["layout"] = "grid_2d"
    return graph


def _node_at(row: int, col: int, cols: int) -> int:
    """Индекс вершины при построчной нумерации сетки."""
    return row * cols + col


def _enumerate_planar_grid_candidates(
    rows: int,
    cols: int,
    nodes: set[int],
    *,
    diagonals: bool,
    rng: random.Random,
) -> tuple[list[tuple[int, int]], int, int]:
    """
    Собрать единый список возможных рёбер для grid_2d_random.

    Ортогональные рёбра — все стороны между соседними порами.
    Диагональные (опционально) — по одной на каждый квадрат 2×2 пор:
    либо «\\», либо «/», случайно и независимо. Так диагонали не пересекаются
    и участвуют в bond percolation наравне с ортогональными.

    Returns:
        (рёбра, число ортогональных кандидатов, число диагональных кандидатов)
    """
    orth: list[tuple[int, int]] = []
    diag: list[tuple[int, int]] = []

    for r in range(rows):
        for c in range(cols):
            u = _node_at(r, c, cols)
            if u not in nodes:
                continue
            if c + 1 < cols:
                v = _node_at(r, c + 1, cols)
                if v in nodes:
                    orth.append((u, v) if u < v else (v, u))
            if r + 1 < rows:
                v = _node_at(r + 1, c, cols)
                if v in nodes:
                    orth.append((u, v) if u < v else (v, u))

    if diagonals:
        for r in range(rows - 1):
            for c in range(cols - 1):
                ul = _node_at(r, c, cols)
                ur = _node_at(r, c + 1, cols)
                ll = _node_at(r + 1, c, cols)
                lr = _node_at(r + 1, c + 1, cols)
                if not {ul, ur, ll, lr}.issubset(nodes):
                    continue
                # Ровно одна диагональ на плашку 2×2 — планарное вложение на сетке
                if rng.random() < 0.5:
                    edge = (ul, lr)
                else:
                    edge = (ur, ll)
                diag.append(edge if edge[0] < edge[1] else (edge[1], edge[0]))

    return orth + diag, len(orth), len(diag)


def _bond_probability_from_degree(
    degree: int,
    n_nodes: int,
    n_candidates: int,
) -> float:
    """
    Вероятность сохранить ребро из общего пула кандидатов.

    Целевая средняя степень ⟨k⟩ ≈ degree:
      2 · p · n_candidates / n_nodes ≈ degree  →  p = degree · n_nodes / (2 · n_candidates)

    Так параметр «связность» одинаково влияет и на ортогональные, и на диагональные рёбра.
    """
    _validate_positive_int("degree", degree)
    if n_nodes <= 0 or n_candidates <= 0:
        return 0.0
    p = (degree * n_nodes) / (2 * n_candidates)
    return min(1.0, max(0.0, p))


def _ensure_connected_on_grid_template(
    graph: nx.Graph, template: nx.Graph, rng: random.Random
) -> None:
    """
    Гарантировать связность, добавляя рёбра только из шаблона полной сетки.

    Зачем: при низкой p граф мог распасться; новые рёбра — те же grid-соседства,
    вложение в плоскость (планарность на квадратной решётке) сохраняется.

    Как: остовное дерево полной сетки (MST) — все его рёбра добавляем, если их
    случайно удалили.
    """
    if graph.number_of_nodes() <= 1 or nx.is_connected(graph):
        return

    # Случайные веса → разные MST при разных seed, но только grid-рёбра
    weighted = template.copy()
    for u, v in weighted.edges():
        weighted[u][v]["w"] = rng.random()

    mst = nx.minimum_spanning_tree(weighted, weight="w")
    for u, v in mst.edges():
        graph.add_edge(u, v)


def create_grid_2d_random(
    size: int | None = None,
    nodes: int | None = None,
    degree: int = 4,
    bond_probability: float | None = None,
    diagonals: bool = False,
    seed: int | None = None,
) -> nx.Graph:
    """
    Планарная случайная решётка: узлы как у grid_2d, связи — bond percolation.

    1. Формируется общий пул кандидатов: ортогональные рёбра + (опционально)
       по одной непересекающейся диагонали на каждый квадрат 2×2.
    2. Каждый кандидат сохраняется с одной и той же вероятностью p.
    3. p из параметра degree: ⟨k⟩ ≈ degree для всего пула сразу.
    4. Связность восстанавливается рёбрами из полного шаблона (MST).
    """
    lattice = create_grid_2d(size=size, nodes=nodes)
    rows = int(lattice.graph["grid_rows"])
    cols = int(lattice.graph["grid_cols"])
    node_set = set(lattice.nodes())

    rng = random.Random(seed)
    candidates, n_orth, n_diag = _enumerate_planar_grid_candidates(
        rows, cols, node_set, diagonals=diagonals, rng=rng,
    )

    if not candidates:
        graph = lattice.copy()
        graph.clear_edges()
        graph.graph["topology"] = "grid_2d_random"
        graph.graph["diagonals"] = diagonals
        return graph

    if bond_probability is None:
        bond_probability = _bond_probability_from_degree(
            degree, len(node_set), len(candidates),
        )
    else:
        _validate_probability("bond_probability", bond_probability)

    # Полный шаблон — все кандидаты (для MST и метаданных)
    template = nx.Graph()
    template.add_nodes_from(node_set)
    template.add_edges_from(candidates)

    # Случайное подмножество: ортогональные и диагональные — одна вероятность p
    graph = nx.Graph()
    graph.add_nodes_from(node_set)
    for u, v in candidates:
        if rng.random() < bond_probability:
            graph.add_edge(u, v)

    _ensure_connected_on_grid_template(graph, template, rng)

    graph.graph["grid_rows"] = rows
    graph.graph["grid_cols"] = cols
    graph.graph["layout"] = "grid_2d"
    graph.graph["topology"] = "grid_2d_random"
    graph.graph["bond_probability"] = bond_probability
    graph.graph["diagonals"] = diagonals
    graph.graph["candidates_orthogonal"] = n_orth
    graph.graph["candidates_diagonal"] = n_diag
    return graph


def create_random_lattice(
    nodes: int,
    degree: int = 4,
    edge_probability: float | None = None,
    seed: int | None = None,
) -> nx.Graph:
    """
    Случайный граф Эрдёша–Реньи — нерегулярная связность пор.

    Зачем: модель «случайной» пористости; параметр degree задаёт среднюю
    связность ⟨k⟩, важную для остеоинтеграции (Kechagias et al.).

    Как: G(n,p) с p ≈ k/(n-1). Если граф распался на компоненты — соединяем
    их ребром, иначе клетки не смогут распространиться по всей структуре.
    """
    _validate_positive_int("nodes", nodes)
    if edge_probability is None:
        _validate_positive_int("degree", degree)
        edge_probability = min(1.0, degree / (nodes - 1)) if nodes > 1 else 0.0
    else:
        _validate_probability("edge_probability", edge_probability)

    graph = nx.erdos_renyi_graph(nodes, edge_probability, seed=seed)

    # Склеивание компонент связности в одну (минимально для симуляции)
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
    """
    Граф «маленького мира» (Watts–Strogatz).

    Зачем: промежуточный сценарий — почти как сетка локально, но с короткими
    путями между дальними участками (редкие длинные каналы в решётке).

    Как: кольцо с k соседями, затем с вероятностью rewiring_probability
    ребро переназначается на случайный дальний узел. k делаем чётным — требование модели.
    """
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
    diagonals: bool = False,
    seed: int | None = None,
) -> nx.Graph:
    """
    Фабрика: по строке типа и параметрам CLI/GUI вернуть готовый граф.

    Логика числа узлов:
      - grid_2d / grid_2d_random: приоритет size, nodes — опциональная обрезка;
      - random/small_world: nodes или size², иначе 100 по умолчанию.

    edge_probability для grid_2d_random — вероятность сохранить соседнее ребро сетки.
    """
    kind = normalize_graph_type(graph_type)
    if kind == "grid_2d":
        return create_grid_2d(size=size, nodes=nodes)
    if kind == "grid_2d_random":
        return create_grid_2d_random(
            size=size,
            nodes=nodes,
            degree=degree,
            bond_probability=edge_probability,
            diagonals=diagonals,
            seed=seed,
        )
    if kind == "random":
        n = nodes or (size * size if size else 100)
        return create_random_lattice(n, degree=degree, edge_probability=edge_probability, seed=seed)
    n = nodes or (size * size if size else 100)
    return create_small_world_lattice(
        n, degree=degree, rewiring_probability=rewiring_probability, seed=seed
    )


def graph_summary(graph: nx.Graph) -> str:
    """
    Краткая строка для консоли/лога: размер, связность, тип раскладки.

    Средняя степень 2m/n — метрика ⟨k⟩ для отчёта по эксперименту.
    """
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    avg_degree = (2 * m / n) if n else 0.0
    connected = nx.is_connected(graph) if n > 0 else True
    layout = graph.graph.get("layout", "spring")
    extra = ""
    if "grid_rows" in graph.graph:
        extra = f", сетка {graph.graph['grid_rows']}x{graph.graph['grid_cols']}"
    if graph.graph.get("topology") == "grid_2d_random":
        p = graph.graph.get("bond_probability", "?")
        n_orth = graph.graph.get("candidates_orthogonal", 0)
        n_diag = graph.graph.get("candidates_diagonal", 0)
        if graph.graph.get("diagonals"):
            extra += f", bond percolation (p={p}, канд. {n_orth}+{n_diag} диг.)"
        else:
            extra += f", bond percolation (p={p}, канд. {n_orth})"
    return (
        f"Вершин: {n}, рёбер: {m}, средняя степень: {avg_degree:.2f}, "
        f"связный: {connected}, раскладка: {layout}{extra}"
    )


def average_degree(graph: nx.Graph) -> float:
    """Средняя степень вершин ⟨k⟩ — показатель связности решётки."""
    n = graph.number_of_nodes()
    return (2 * graph.number_of_edges() / n) if n else 0.0
