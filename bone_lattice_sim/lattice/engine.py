"""
Генерация 3D поровых сетей через OpenPNM и адаптер LatticeGraph.

OpenPNM используется только для построения топологии (pores/throats) и координат.
Симуляция работает с LatticeGraph — списком соседей без зависимости от OpenPNM.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

import networkx as nx
import numpy as np

LatticePreset = Literal["regular_6", "random", "full_26"]


@dataclass(frozen=True)
class LatticeGraph:
    """
    Поровая сеть для симуляции клеток.

    neighbors[i] — индексы пор, связанных с порой i каналами (throats).
    coords — координаты центров пор (n_pores, 3), для будущей 3D-визуализации.
    """

    n_pores: int
    neighbors: list[list[int]]
    coords: np.ndarray
    meta: dict = field(default_factory=dict)

    def validate(self) -> None:
        if self.coords.shape != (self.n_pores, 3):
            raise ValueError(
                f"coords должны иметь форму ({self.n_pores}, 3), "
                f"получено {self.coords.shape}"
            )
        if len(self.neighbors) != self.n_pores:
            raise ValueError("len(neighbors) должно совпадать с n_pores")


def _edges_from_openpnm(pn) -> list[tuple[int, int]]:
    """Уникальные неориентированные рёбра из OpenPNM conns."""
    seen: set[tuple[int, int]] = set()
    edges: list[tuple[int, int]] = []
    for a, b in pn.conns:
        u, v = int(a), int(b)
        key = (u, v) if u < v else (v, u)
        if key not in seen:
            seen.add(key)
            edges.append(key)
    return edges


def _adjacency_from_edges(n_pores: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    neighbors: list[list[int]] = [[] for _ in range(n_pores)]
    for u, v in edges:
        neighbors[u].append(v)
        neighbors[v].append(u)
    for i in range(n_pores):
        neighbors[i].sort()
    return neighbors


def _ensure_connected(
    edges: list[tuple[int, int]],
    template_edges: list[tuple[int, int]],
    rng: random.Random,
) -> list[tuple[int, int]]:
    """
    Восстановить связность MST по полному шаблону (как bond percolation в 2D-модели).

    Если после удаления throats граф распался — добавляем рёбра из остовного дерева.
    """
    n_pores = max(max(u, v) for u, v in template_edges) + 1 if template_edges else 0
    if n_pores <= 1:
        return edges

    graph = nx.Graph()
    graph.add_nodes_from(range(n_pores))
    graph.add_edges_from(edges)

    if nx.is_connected(graph):
        return edges

    template = nx.Graph()
    template.add_nodes_from(range(n_pores))
    template.add_edges_from(template_edges)
    for u, v in template.edges():
        template[u][v]["w"] = rng.random()

    mst = nx.minimum_spanning_tree(template, weight="w")
    edge_set = set(edges)
    for u, v in mst.edges():
        key = (u, v) if u < v else (v, u)
        edge_set.add(key)
    return sorted(edge_set)


def _random_throat_deletion(
    template_edges: list[tuple[int, int]],
    deletion_fraction: float,
    rng: random.Random,
) -> list[tuple[int, int]]:
    """Случайно удалить долю throats, затем восстановить связность."""
    if not template_edges:
        return []
    if deletion_fraction <= 0.0:
        return list(template_edges)
    if deletion_fraction >= 1.0:
        raise ValueError("deletion_fraction должна быть в [0, 1)")

    shuffled = template_edges[:]
    rng.shuffle(shuffled)
    keep_count = max(1, int(round(len(shuffled) * (1.0 - deletion_fraction))))
    kept = shuffled[:keep_count]
    return _ensure_connected(kept, template_edges, rng)


def _connectivity_for_preset(preset: LatticePreset) -> int:
    if preset == "full_26":
        return 26
    return 6


def build_lattice(
    size: int,
    preset: LatticePreset = "regular_6",
    *,
    throat_deletion_fraction: float = 0.3,
    seed: int | None = None,
) -> LatticeGraph:
    """
    Создать 3D кубическую поровую сеть N×N×N.

    preset:
      regular_6 — ортогональные связи (connectivity 6);
      random    — regular_6 + случайное удаление доли throats + MST;
      full_26   — все соседи в окне 3×3×3 (connectivity 26).
    """
    if size < 2:
        raise ValueError("size должно быть >= 2")
    if preset == "random" and not 0.0 <= throat_deletion_fraction < 1.0:
        raise ValueError("throat_deletion_fraction должна быть в [0, 1)")

    import openpnm as op

    connectivity = _connectivity_for_preset(preset)
    pn = op.network.Cubic(shape=[size, size, size], connectivity=connectivity)
    template_edges = _edges_from_openpnm(pn)
    rng = random.Random(seed)

    if preset == "random":
        edges = _random_throat_deletion(
            template_edges, throat_deletion_fraction, rng,
        )
    else:
        edges = template_edges

    n_pores = int(pn.Np)
    neighbors = _adjacency_from_edges(n_pores, edges)
    coords = np.array(pn.coords, dtype=float)

    graph = LatticeGraph(
        n_pores=n_pores,
        neighbors=neighbors,
        coords=coords,
        meta={
            "preset": preset,
            "size": size,
            "connectivity_base": connectivity,
            "n_throats": len(edges),
            "throat_deletion_fraction": throat_deletion_fraction if preset == "random" else 0.0,
            "avg_degree": average_degree_from_neighbors(neighbors),
            "seed": seed,
        },
    )
    graph.validate()
    return graph


def average_degree_from_neighbors(neighbors: list[list[int]]) -> float:
    n = len(neighbors)
    if n == 0:
        return 0.0
    return sum(len(nbrs) for nbrs in neighbors) / n


def average_degree(lattice: LatticeGraph) -> float:
    return float(lattice.meta.get("avg_degree", average_degree_from_neighbors(lattice.neighbors)))


def reachable_fraction(lattice: LatticeGraph, source_pores: list[int]) -> float:
    """
    Доля пор, достижимых от source по графу throats (BFS).

    Полезно для оценки «мёртвых зон» топологии до симуляции.
    """
    if lattice.n_pores == 0:
        return 0.0
    visited: set[int] = set()
    queue = [p for p in source_pores if 0 <= p < lattice.n_pores]
    for pore in queue:
        visited.add(pore)
    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        for nbr in lattice.neighbors[current]:
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)
    return len(visited) / lattice.n_pores


def face_pore_indices(lattice: LatticeGraph, *, axis: int = 2, side: str = "min") -> list[int]:
    """
    Индексы пор на одной грани куба (по умолчанию min-Z — «нижняя» грань, контакт с тканью).

    axis: 0=x, 1=y, 2=z; side: min | max
    """
    coords = lattice.coords
    values = coords[:, axis]
    target = float(np.min(values) if side == "min" else np.max(values))
    tol = max(1e-5, float(np.ptp(values)) * 1e-4)
    return [i for i in range(lattice.n_pores) if abs(coords[i, axis] - target) <= tol]


def face_center_pore_index(lattice: LatticeGraph, *, axis: int = 2, side: str = "min") -> int:
    """Центральная пора на грани (ближайшая к центру грани в двух других осях)."""
    face = face_pore_indices(lattice, axis=axis, side=side)
    if not face:
        return 0
    coords = lattice.coords[face]
    other = [a for a in range(3) if a != axis]
    cx = float(np.mean(coords[:, other[0]]))
    cy = float(np.mean(coords[:, other[1]]))
    dists = (coords[:, other[0]] - cx) ** 2 + (coords[:, other[1]] - cy) ** 2
    return face[int(np.argmin(dists))]


def random_face_pore_indices(
    lattice: LatticeGraph,
    count: int,
    rng: random.Random,
    *,
    axis: int = 2,
    side: str = "min",
) -> list[int]:
    face = face_pore_indices(lattice, axis=axis, side=side)
    if count < 1:
        raise ValueError("count должно быть >= 1")
    if count > len(face):
        raise ValueError(
            f"На грани {len(face)} пор, нельзя разместить {count} клеток. "
            "Уменьшите число в «Составе» или выберите random/center."
        )
    return rng.sample(face, count)


def center_pore_index(size: int) -> int:
    """Индекс центральной поры в кубической сетке OpenPNM (row-major по shape)."""
    i = size // 2
    return i * size * size + i * size + i


def random_pore_indices(
    n_pores: int, count: int, rng: random.Random,
) -> list[int]:
    if count < 1 or count > n_pores:
        raise ValueError("count должно быть от 1 до n_pores")
    return rng.sample(range(n_pores), count)
