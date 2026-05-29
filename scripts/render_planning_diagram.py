# -*- coding: utf-8 -*-
"""Рендер planning_classes.puml → PNG."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from plantuml_render import render_diagram  # noqa: E402

PUML = ROOT / "docs" / "planning_classes.puml"
OUT_PATHS = [
    ROOT / "docs" / "diagram_planning_classes.png",
    ROOT / "Видение проекта" / "diagram_planning_classes.png",
]


def main() -> None:
    render_diagram(PUML, OUT_PATHS[0], "png")
    OUT_PATHS[1].parent.mkdir(parents=True, exist_ok=True)
    OUT_PATHS[1].write_bytes(OUT_PATHS[0].read_bytes())
    (ROOT / "Видение проекта" / "planning_classes.puml").write_text(
        PUML.read_text(encoding="utf-8"), encoding="utf-8",
    )
    for p in OUT_PATHS:
        print(f"OK {p} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
