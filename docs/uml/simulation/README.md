# UML: логика симуляции клеток

Диаграммы описывают только **agent-based модель колонизации пор** (`bone_lattice_sim/simulation/`, `experiment.py` — сборка параметров).  
**Не включены:** PyVista, GUI, PyInstaller, экспорт VTK/STL.

## Список диаграмм

| № | Тип UML | Файл | Что показывает |
|---|---------|------|----------------|
| 0 | **Контекст** (C4-lite) | [00_context.puml](00_context.puml) | Входы/выходы ABM без UI |
| 1 | **Варианты использования** | [01_use_case.puml](01_use_case.puml) | Кто и что делает с моделью (исследователь, система) |
| 2 | **Классов** | [02_class.puml](02_class.puml) | Сущности: клетки, намерения, конфиг, движок, статистика |
| 3 | **Компонентов** | [03_component.puml](03_component.puml) | Модули `agents`, `simulation`, `stats`, `biophysics` |
| 4 | **Пакетов** | [04_package.puml](04_package.puml) | Зависимости пакетов (упрощённо) |
| 5 | **Последовательности** — один шаг | [05_sequence_step.puml](05_sequence_step.puml) | Синхронный шаг: Intent → конфликты → migrate → prolif |
| 6 | **Последовательности** — прогон | [06_sequence_run.puml](06_sequence_run.puml) | `run()`: снимок t=0, цикл шагов, отмена |
| 7 | **Деятельности** — один шаг | [07_activity_step.puml](07_activity_step.puml) | Алгоритм `step()` |
| 8 | **Деятельности** — решение клетки | [08_activity_decide.puml](08_activity_decide.puml) | `_decide_action` / `_pick_action_type` |
| 9 | **Состояний** — намерение (Intent) | [09_state_intent.puml](09_state_intent.puml) | Жизненный цикл намерения за шаг |
| 10 | **Состояний** — пора | [10_state_pore.puml](10_state_pore.puml) | Пустая / занята (volume exclusion) |
| 11 | **Объектов** (пример) | [11_object_example.puml](11_object_example.puml) | Снимок системы на шаге t=5 (учебный пример) |
| 12 | **Коммуникации** | [12_communication_step.puml](12_communication_step.puml) | Объекты и сообщения при одном шаге |

> **Диаграмма развёртывания** для desktop-логики не нужна (нет серверов).  
> **Временная диаграмма** (timing) не используется — дискретные шаги уже на activity/sequence.

## Как получить PNG/SVG

1. Откройте нужный `.puml` на [plantuml.com/plantuml](https://www.plantuml.com/plantuml/uml/).
2. Или VS Code: расширение **PlantUML** → Preview → Export.
3. Для отчёта: `java -jar plantuml.jar docs/uml/simulation/*.puml -o ../../../отчет/images`

## Рекомендация для пояснительной записки

В основной текст обычно вставляют **4–5 рисунков**:

1. Варианты использования  
2. Классов  
3. Деятельности (шаг симуляции)  
4. Последовательности (шаг симуляции)  
5. Состояний (пора или Intent)

Остальные — в приложение.
