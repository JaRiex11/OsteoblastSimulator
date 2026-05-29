# -*- coding: utf-8 -*-
"""Рендер actual_classes.puml → PNG/SVG (для защиты)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from plantuml_render import render_diagram  # noqa: E402

PUML = ROOT / "docs" / "actual_classes.puml"
OUTPUTS = [
    ROOT / "docs" / "diagram_actual_classes.png",
    ROOT / "presentation" / "diagram_actual_classes.png",
    ROOT / "docs" / "diagram_actual_classes.svg",
]


def main() -> None:
    if not PUML.is_file():
        raise SystemExit(f"Нет файла: {PUML}")

    render_diagram(PUML, OUTPUTS[0], "png")
    render_diagram(PUML, OUTPUTS[1], "png")
    render_diagram(PUML, OUTPUTS[2], "svg")

    (ROOT / "presentation" / "actual_classes.puml").write_text(
        PUML.read_text(encoding="utf-8"), encoding="utf-8",
    )
    for p in OUTPUTS:
        print(f"OK {p} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
