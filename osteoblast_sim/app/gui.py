"""
Графический интерфейс (tkinter) — основной режим для .exe.

Поля связаны с tk.Variable; при запуске подставляются значения из gui_settings.json.
Сохранение: перед прогоном, при закрытии окна.

Внутри используется тот же run_experiment(), что и CLI — одна логика модели.
"""

from __future__ import annotations

import argparse
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

from osteoblast_sim.app.experiment import run_experiment
from osteoblast_sim.app.settings import (
    fields_to_settings_dict,
    load_gui_settings,
    save_gui_settings,
    settings_to_fields_dict,
)
from osteoblast_sim.paths import ensure_output_dir
from osteoblast_sim.simulation.engine import export_results_csv
from osteoblast_sim.visualization.charts import (
    animate_simulation,
    format_statistics,
    plot_occupancy_curve,
    save_figure,
    save_graph_png,
    show_dashboard,
)


def _make_fields(root: tk.Tk, saved: dict) -> dict:
    """
    Создать переменные полей формы.

    master=root нужен, чтобы переменные жили столько же, сколько окно.
    """
    s = settings_to_fields_dict(saved)
    return {
        "graph_type": tk.StringVar(master=root, value=s["graph_type"]),
        "size": tk.IntVar(master=root, value=s["size"]),
        "nodes": tk.StringVar(master=root, value=s["nodes"]),
        "degree": tk.IntVar(master=root, value=s["degree"]),
        "p_migrate": tk.DoubleVar(master=root, value=s["p_migrate"]),
        "p_prolif": tk.DoubleVar(master=root, value=s["p_prolif"]),
        "time_steps": tk.IntVar(master=root, value=s["time_steps"]),
        "initial_cells": tk.StringVar(master=root, value=s["initial_cells"]),
        "seed": tk.StringVar(master=root, value=s["seed"]),
        "color_mode": tk.StringVar(master=root, value=s["color_mode"]),
        "animate": tk.BooleanVar(master=root, value=s["animate"]),
        "diagonals": tk.BooleanVar(master=root, value=s["diagonals"]),
    }


def launch_gui() -> None:
    root = tk.Tk()
    root.title("Остеобласты в пористом имплантате")
    root.minsize(420, 520)

    # Восстановить прошлые параметры пользователя
    saved = load_gui_settings()
    fields = _make_fields(root, saved)

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill="both", expand=True)

    def row(r: int, label: str, widget) -> None:
        ttk.Label(frame, text=label).grid(row=r, column=0, sticky="w", pady=2)
        widget.grid(row=r, column=1, sticky="ew", pady=2)

    row(0, "Тип решётки", ttk.Combobox(
        frame, textvariable=fields["graph_type"],
        values=["grid_2d", "grid_2d_random", "random", "small_world"],
        state="readonly",
        width=20,
    ))
    row(1, "Размер сетки", ttk.Entry(frame, textvariable=fields["size"], width=22))
    row(2, "Число узлов (пусто=авто)", ttk.Entry(frame, textvariable=fields["nodes"], width=22))
    row(3, "Связность (степень)", ttk.Entry(frame, textvariable=fields["degree"], width=22))
    row(4, "P_migrate", ttk.Entry(frame, textvariable=fields["p_migrate"], width=22))
    row(5, "P_prolif", ttk.Entry(frame, textvariable=fields["p_prolif"], width=22))
    row(6, "Шагов времени", ttk.Entry(frame, textvariable=fields["time_steps"], width=22))
    row(7, "Начало (center/random)", ttk.Entry(frame, textvariable=fields["initial_cells"], width=22))
    row(8, "Раскраска", ttk.Combobox(
        frame, textvariable=fields["color_mode"],
        values=["occupancy", "colonization", "local_density"], state="readonly", width=20,
    ))
    row(9, "Seed", ttk.Entry(frame, textvariable=fields["seed"], width=22))
    ttk.Checkbutton(frame, text="Анимация", variable=fields["animate"]).grid(row=10, column=1, sticky="w")
    ttk.Checkbutton(
        frame,
        text="Диагонали (grid_2d_random)",
        variable=fields["diagonals"],
    ).grid(row=11, column=1, sticky="w")

    # Лог отчёта под формой (только чтение)
    log = scrolledtext.ScrolledText(frame, height=8, width=50, state="disabled", font=("Consolas", 9))
    log.grid(row=12, column=0, columnspan=2, pady=8, sticky="nsew")
    frame.rowconfigure(12, weight=1)

    def log_msg(text: str) -> None:
        log.configure(state="normal")
        log.insert("end", text + "\n")
        log.see("end")
        log.configure(state="disabled")

    def persist_settings() -> None:
        save_gui_settings(fields_to_settings_dict(fields))

    def _args() -> argparse.Namespace:
        """
        Собрать Namespace как у CLI — чтобы run_experiment() не знал,
        откуда пришли параметры (GUI или терминал).
        """
        nodes_raw = fields["nodes"].get().strip()
        seed_raw = fields["seed"].get().strip()
        return argparse.Namespace(
            graph_type=fields["graph_type"].get(),
            size=fields["size"].get(),
            nodes=int(nodes_raw) if nodes_raw else None,
            degree=fields["degree"].get(),
            edge_probability=None,
            rewiring_probability=0.1,  # для small_world; в GUI не вынесено
            diagonals=fields["diagonals"].get(),
            p_migrate=fields["p_migrate"].get(),
            p_prolif=fields["p_prolif"].get(),
            time_steps=fields["time_steps"].get(),
            initial_cells=fields["initial_cells"].get(),
            n_seeds=1,
            seed=int(seed_raw) if seed_raw else None,
            color_mode=fields["color_mode"].get(),
            animate=fields["animate"].get(),
            no_show=False,
            save_csv=None,
            save_plot=None,
            save_graph=None,
            gui=False,
        )

    def on_run() -> None:
        try:
            persist_settings()
            ns = _args()
            sim, result = run_experiment(ns)
            log_msg(format_statistics(result))
            if ns.animate and result.occupied_sets:
                animate_simulation(sim.graph, result, color_mode=ns.color_mode)
            else:
                show_dashboard(sim.graph, sim, result, color_mode=ns.color_mode)
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Параметры", str(exc))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", f"{type(exc).__name__}: {exc}")

    def on_save() -> None:
        """Прогон + автосохранение CSV и двух PNG с меткой времени в output/."""
        try:
            persist_settings()
            ns = _args()
            sim, result = run_experiment(ns)
            out = ensure_output_dir()
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_p = out / f"run_{stamp}.csv"
            plot_p = out / f"curve_{stamp}.png"
            graph_p = out / f"lattice_{stamp}.png"
            export_results_csv(str(csv_p), result)
            plot_occupancy_curve(result)
            save_figure(plot_p)
            import matplotlib.pyplot as plt
            plt.close("all")
            save_graph_png(sim.graph, sim, graph_p, color_mode=ns.color_mode)
            log_msg(format_statistics(result))
            log_msg(f"Сохранено в {out}:")
            log_msg(f"  {csv_p.name}")
            log_msg(f"  {plot_p.name}")
            log_msg(f"  {graph_p.name}")
            messagebox.showinfo("Готово", f"Файлы сохранены в:\n{out}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))

    def _open_output() -> None:
        import os
        import subprocess
        folder = str(ensure_output_dir())
        if os.name == "nt":
            os.startfile(folder)  # noqa: S606
        else:
            subprocess.run(["xdg-open", folder], check=False)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=13, column=0, columnspan=2, pady=6)
    ttk.Button(btn_frame, text="Запустить", command=on_run).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="Запустить и сохранить в output/", command=on_save).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="Открыть папку output", command=_open_output).pack(side="left", padx=4)

    def on_close() -> None:
        persist_settings()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
