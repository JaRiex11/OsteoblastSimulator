# UML: диаграмма классов (весь проект)

> **Для курсовой по логике симуляции клеток** используйте набор из **[uml/simulation/](uml/simulation/README.md)** — 12 диаграмм (use case, class, sequence, activity, state, component, object, communication) без GUI и сборки exe.

Основной продукт — **`bone_lattice_sim`** (3D, OpenPNM, PySide6).  
Legacy — **`osteoblast_sim`** (2D, NetworkX, Tkinter).

## Диаграмма реализации (для защиты)

UML-нотация (`+`/`-`, поля и методы). **Только предметная область** (решётка, клетки, симуляция, биофизика) — без UI, экспорта, 3D, CLI:

| Артефакт | Описание |
|----------|----------|
| [actual_classes.puml](actual_classes.puml) | Исходник PlantUML |
| [diagram_actual_classes.png](diagram_actual_classes.png) | PNG для слайдов |
| [diagram_actual_classes.svg](diagram_actual_classes.svg) | SVG для печати |
| [planning_classes.puml](planning_classes.puml) | Планирование (упрощённая) |

Пересборка: `python scripts/render_all_diagrams.py` (или `render_actual_diagram.py`).

**Параметризованные типы:** в `.puml` — `List~Cell~` (сырые `<` ломают PlantUML). Скрипт рендера заменяет `~` на `List<Cell>` в SVG и собирает PNG через `npx @resvg/resvg-js-cli`. Нужен Node.js. Команда: `python scripts/render_all_diagrams.py`.

## Как получить картинку (обзорная / legacy)

| Формат | Файл | Как рендерить |
|--------|------|----------------|
| PlantUML | [uml_classes.puml](uml_classes.puml) | обзор + legacy `osteoblast_sim` |
| Mermaid | ниже | GitHub, [mermaid.live](https://mermaid.live) |

Для отчёта: `\includegraphics{diagram_actual_classes.png}` из `docs/`.

---

## bone_lattice_sim (Mermaid)

```mermaid
classDiagram
    direction TB

    class LatticeGraph {
        +int n_pores
        +list neighbors
        +ndarray coords
        +dict meta
        +validate()
    }

    class LatticeEngine {
        <<utility>>
        +build_lattice() LatticeGraph
        +average_degree()
        +reachable_fraction()
    }

    class CellType {
        <<enumeration>>
        OSTEOBLAST
        MSC
        FIBROBLAST
    }

    class ActionType {
        <<enumeration>>
        MIGRATE
        PROLIF
    }

    class Cell {
        +int cell_id
        +CellType cell_type
        +int pore
    }

    class CellTypeParams {
        +float p_migrate
        +float p_prolif
    }

    class Intent {
        +int cell_id
        +ActionType action
        +int target_pore
    }

    class SimulationConfig {
        +int time_steps
        +dict type_params
        +float dt_hours
    }

    class Simulation {
        -LatticeGraph lattice
        -list~Cell~ cells
        -list occupancy
        +step()
        +run() SimulationResult
    }

    class SimulationResult {
        +list~StepStats~ history
        +time_to_threshold()
    }

    class StepStats {
        +int step
        +float occupancy
        +dict counts_by_type
    }

    class BiophysicsCalibration {
        +float dt_hours
        +dict type_params
    }

    class SimulationRun {
        +SimulationResult result
        +LatticeGraph lattice
        +dict settings
        +list animation_frames
    }

    class LatticeVisualContext {
        +ndarray coords
        +ndarray edges
    }

    class VisualSnapshot {
        +int step
        +ndarray pore_types
    }

    class LatticeViewer3D {
        +set_lattice()
        +update_snapshot()
    }

    class MainWindow {
        +on_run()
        +on_stop()
    }

    class SimulationWorker {
        <<QThread>>
        +run()
        +cancel()
    }

    class Experiment {
        <<utility>>
        +create_lattice()
        +create_simulation()
    }

    LatticeEngine ..> LatticeGraph : creates
    Simulation *-- LatticeGraph
    Simulation *-- Cell
    Simulation o-- SimulationConfig
    Simulation ..> Intent
    Simulation ..> SimulationResult
    SimulationResult *-- StepStats
    Cell --> CellType
    Intent --> ActionType
    SimulationConfig --> CellTypeParams
    BiophysicsCalibration --> CellTypeParams
    Experiment ..> LatticeGraph
    Experiment ..> Simulation
    SimulationRun *-- SimulationResult
    SimulationRun *-- LatticeGraph
    MainWindow *-- SimulationWorker
    MainWindow o-- SimulationRun
    SimulationWorker ..> Simulation
    SimulationWorker ..> SimulationRun
    LatticeViewer3D ..> LatticeVisualContext
    LatticeViewer3D ..> VisualSnapshot
```

---

## Поток данных (кратко)

```mermaid
flowchart LR
    subgraph UI
        MW[MainWindow]
        CT[ConfigTab]
        W[SimulationWorker]
    end
    subgraph Core
        EX[experiment]
        LG[LatticeGraph]
        SIM[Simulation]
        RES[SimulationResult]
    end
    subgraph Viz
        V3D[LatticeViewer3D]
        SNAP[VisualSnapshot]
    end
    CT --> MW
    MW --> W
    W --> EX
    EX --> LG
    EX --> SIM
    SIM --> RES
    W --> SNAP
    SNAP --> V3D
    RES --> Export[CSV / JSON / PNG]
```

---

## osteoblast_sim (legacy)

```mermaid
classDiagram
    class GraphBuilder {
        <<utility>>
        +build_graph()
        +create_grid_2d_random()
    }
    class OsteoblastSimulation {
        -Graph graph
        -list cells
        +step()
        +run()
    }
    class SimulationConfig {
        +p_migrate
        +p_prolif
    }
    GraphBuilder ..> OsteoblastSimulation : NetworkX Graph
    OsteoblastSimulation --> SimulationConfig
```
