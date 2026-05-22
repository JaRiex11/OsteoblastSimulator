"""
Визуализация результатов lattice-модели.

Три режима раскраски вершин (пор):
  occupancy      — занято / свободно (основной для курсовой);
  colonization   — когда пора впервые была занята (градиент по времени);
  local_density  — доля занятых соседей (скученность).

Используются NetworkX для графа и Matplotlib для рисунков и анимации.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from osteoblast_sim.simulation.engine import SimulationResult

ColorMode = Literal["occupancy", "colonization", "local_density"]

# Фирменные цвета интерфейса (как в исходном дизайне)
COLOR_OCCUPIED = "#2ecc71"
COLOR_FREE = "#bdc3c7"
COLOR_EDGE = "#7f8c8d"


def _cmap(name: str):
    """Палитра Matplotlib с запасным вариантом для старых версий."""
    try:
        return plt.colormaps[name]
    except (AttributeError, KeyError):
        return cm.get_cmap(name)


def layout_for_graph(graph: nx.Graph) -> dict:
    """
    Координаты узлов на плоскости для отрисовки.

    grid_2d: узлы в сетке (node // cols, node % cols) — читаемая схема решётки.
    Иначе: spring_layout — «пружинная» раскладка для random/small_world.
    """
    n = graph.number_of_nodes()
    if n <= 0:
        return {}
    rows = graph.graph.get("grid_rows")
    cols = graph.graph.get("grid_cols")
    # grid_2d и grid_2d_random рисуются в координатах квадратной решётки
    if rows and cols and graph.graph.get("layout") == "grid_2d":
        return {
            node: (float(int(node) % cols), -float(int(node) // cols))
            for node in graph.nodes()
        }
    return nx.spring_layout(graph, seed=42, k=1.0 / np.sqrt(max(n, 1)))


def node_colors(
    graph: nx.Graph, occupied: set[int], mode: ColorMode = "occupancy",
    colonization_step: dict[int, int] | None = None,
    local_density: dict[int, float] | None = None, max_step: int = 1,
) -> list:
    """
    Список цветов для nx.draw_networkx_nodes — по одному на вершину.

    colonization: нормируем шаг колонизации на max_step → оттенок YlGn.
    local_density: значение 0..1 → тепловая карта OrRd.
    """
    nodes = list(graph.nodes())
    if mode == "occupancy":
        return [COLOR_OCCUPIED if n in occupied else COLOR_FREE for n in nodes]
    if mode == "colonization" and colonization_step is not None:
        cmap = _cmap("YlGn")
        return [
            COLOR_FREE if colonization_step.get(n, -1) < 0
            else cmap(min(1.0, colonization_step[n] / max(max_step, 1)))
            for n in nodes
        ]
    if mode == "local_density" and local_density is not None:
        cmap = _cmap("OrRd")
        return [cmap(local_density.get(n, 0.0)) for n in nodes]
    return [COLOR_OCCUPIED if n in occupied else COLOR_FREE for n in nodes]


def draw_graph(
    graph: nx.Graph, occupied: set[int], *, title: str = "",
    ax: plt.Axes | None = None, color_mode: ColorMode = "occupancy",
    colonization_step: dict[int, int] | None = None,
    local_density: dict[int, float] | None = None,
    max_step: int = 1, pos: dict | None = None,
) -> plt.Axes:
    """Отрисовка одного кадра: рёбра серые, узлы по выбранному режиму."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))
    pos = pos or layout_for_graph(graph)
    colors = node_colors(graph, occupied, color_mode, colonization_step, local_density, max_step)
    nx.draw_networkx_edges(graph, pos, ax=ax, edge_color=COLOR_EDGE, alpha=0.45, width=0.8)
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, node_color=colors, node_size=120,
        edgecolors="#2c3e50", linewidths=0.5,
    )
    labels = {"occupancy": "Занятость", "colonization": "Колонизация", "local_density": "Плотность"}
    ax.set_title(f"{title}\n({labels.get(color_mode, '')})" if title else labels.get(color_mode, ""))
    ax.axis("off")
    return ax


def plot_occupancy_curve(result: SimulationResult, ax: plt.Axes | None = None) -> plt.Axes:
    """
    S-кривая заполнения: доля занятых пор от номера шага.

    Горизонтали 50% и 90% + вертикали в моменты T50/T90 — для отчёта
    по скорости остеоинтеграции.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5))
    steps = np.arange(len(result.occupancy_history))
    ax.plot(steps, result.occupancy_history, color="#2980b9", linewidth=2, label="Занятость")
    for thr, color, label in ((0.5, "#f39c12", "50%"), (0.9, "#e74c3c", "90%")):
        ax.axhline(thr, color=color, linestyle="--", linewidth=1, alpha=0.8)
        t = result.time_to_threshold(thr)
        if t is not None:
            ax.axvline(t, color=color, linestyle=":", linewidth=1, alpha=0.6)
            ax.plot(t, thr, "o", color=color, markersize=8)
            ax.annotate(f"{label}: шаг {t}", xy=(t, thr), xytext=(8, 8),
                        textcoords="offset points", fontsize=9, color=color)
    ax.set_xlabel("Шаг (время)")
    ax.set_ylabel("Доля занятых пор")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    ax.set_title("Динамика заполнения пористой структуры")
    ax.legend(loc="lower right")
    return ax


def format_statistics(result: SimulationResult) -> str:
    """Текстовый блок метрик для лога GUI и консоли."""
    ev = result.events
    t50 = result.time_to_threshold(0.5)
    t90 = result.time_to_threshold(0.9)
    return "\n".join([
        "=== Отчёт эксперимента ===",
        f"Пор: {result.n_vertices}",
        f"Шагов: {len(result.occupancy_history) - 1}",
        f"Занятость (финал): {result.final_occupancy:.2%}",
        f"Занятость (макс.): {max(result.occupancy_history):.2%}",
        f"Клеток: {result.final_cell_count}",
        f"T50: {t50 if t50 is not None else 'нет'}",
        f"T90: {t90 if t90 is not None else 'нет'}",
        f"Миграции: {ev.migrate_success} / {ev.migrate_attempts}",
        f"Пролиферации: {ev.prolif_success} / {ev.prolif_attempts}",
    ])


def show_dashboard(graph, sim, result: SimulationResult, color_mode: ColorMode = "occupancy") -> None:
    """
    Итоговое окно из трёх панелей: схема графа, S-кривая, текстовый отчёт.

    Зачем: всё для научной работы на одном экране после прогона.
    """
    fig = plt.figure(figsize=(15, 5.5))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.2, 0.7])
    draw_graph(
        graph, sim.occupied,
        title=f"Финал: {len(sim.occupied)}/{graph.number_of_nodes()} пор",
        ax=fig.add_subplot(gs[0, 0]), color_mode=color_mode,
        colonization_step=sim.colonization_step,
        local_density=sim.local_density_map(),
        max_step=max(1, len(result.occupancy_history) - 1),
    )
    plot_occupancy_curve(result, ax=fig.add_subplot(gs[0, 1]))
    ax_t = fig.add_subplot(gs[0, 2])
    ax_t.axis("off")
    ax_t.text(0.05, 0.95, format_statistics(result), transform=ax_t.transAxes,
              fontsize=10, va="top", family="monospace",
              bbox=dict(boxstyle="round", facecolor="#ecf0f1", alpha=0.9))
    plt.tight_layout()
    plt.show()


def animate_simulation(
    graph, result: SimulationResult, *, interval_ms: int = 200,
    color_mode: ColorMode = "occupancy", show: bool = True,
):
    """
    Пошаговая анимация: FuncAnimation перерисовывает граф на каждом кадре.

    Требует, чтобы при run() был record_history=True (есть occupied_sets).
    pos фиксируется один раз — узлы не «прыгают» между кадрами.
    """
    from matplotlib.animation import FuncAnimation
    if not result.occupied_sets:
        raise ValueError("Нужен record_history=True")
    pos = layout_for_graph(graph)
    max_step = max(1, len(result.occupancy_history) - 1)
    fig, ax = plt.subplots(figsize=(8, 6))

    def _update(frame: int):
        ax.clear()
        colon = result.colonization_snapshots[frame] if result.colonization_snapshots else None
        draw_graph(
            graph, result.occupied_sets[frame], ax=ax, color_mode=color_mode,
            colonization_step=colon, max_step=max_step, pos=pos,
        )
        m, p = result.events_per_step[frame]
        ax.set_title(
            f"Шаг {frame} | {result.occupancy_history[frame]:.1%} | "
            f"клеток {result.cell_count_history[frame]} | M:{m} P:{p}"
        )

    anim = FuncAnimation(fig, _update, frames=len(result.occupied_sets), interval=interval_ms, repeat=False)
    if show:
        plt.show()
    return anim  # ссылка нужна, иначе GC удалит анимацию до показа


def save_figure(path: str | Path, dpi: int = 150) -> None:
    """Сохранить текущую фигуру Matplotlib в PNG."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=dpi, bbox_inches="tight")


def save_graph_png(graph, sim, path: str | Path, color_mode: ColorMode = "occupancy", dpi: int = 150) -> None:
    """Отдельный PNG только со схемой графа (для вставки в записку)."""
    fig, ax = plt.subplots(figsize=(8, 6))
    draw_graph(
        graph, sim.occupied, ax=ax, color_mode=color_mode,
        colonization_step=sim.colonization_step,
        local_density=sim.local_density_map(),
        max_step=max(1, max(sim.colonization_step.values()) if sim.colonization_step else 1),
    )
    save_figure(path, dpi=dpi)
    plt.close(fig)
