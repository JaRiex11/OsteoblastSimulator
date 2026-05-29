# -*- coding: utf-8 -*-
"""
Рендер PlantUML в PNG/SVG.

В .puml типы пишутся как List~Cell~ (иначе сырые < ломают разбор).
После рендера SVG: ~ заменяются на &lt; &gt; — на картинке обычные угловые скобки.
"""
from __future__ import annotations

import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _is_png(data: bytes) -> bool:
    return len(data) > 5000 and data[:8] == b"\x89PNG\r\n\x1a\n"


def _is_svg(data: bytes) -> bool:
    return len(data) > 500 and (b"<svg" in data[:500] or b"<?xml" in data[:200])


# Порядок важен: сначала более длинные шаблоны
_GENERIC_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("List~List~int~~", "List&lt;List&lt;int&gt;&gt;"),
    ("Map~String, Object~", "Map&lt;String, Object&gt;"),
    ("Map~CellType, CellTypeParams~", "Map&lt;CellType, CellTypeParams&gt;"),
    ("List~StepStats~", "List&lt;StepStats&gt;"),
    ("List~Intent~", "List&lt;Intent&gt;"),
    ("List~Cell~", "List&lt;Cell&gt;"),
    ("List~int~", "List&lt;int&gt;"),
    ("List~float~", "List&lt;float&gt;"),
    ("List~Map~", "List&lt;Map&gt;"),
    ("Tuple~int, int~", "Tuple&lt;int, int&gt;"),
    ("Tuple~Simulation, LatticeGraph, List~", "Tuple&lt;Simulation, LatticeGraph, List&gt;"),
)


def fix_generics_in_svg(svg: str) -> str:
    """PlantUML/Kroki оставляют ~ в SVG; для отчёта — классические <>."""
    for old, new in _GENERIC_REPLACEMENTS:
        svg = svg.replace(old, new)
    # Остаточные Map~...~ / List~...~
    svg = re.sub(
        r"Map~([^~<]+)~",
        lambda m: f"Map&lt;{m.group(1)}&gt;",
        svg,
    )
    svg = re.sub(
        r"List~([^~<]+)~",
        lambda m: f"List&lt;{m.group(1)}&gt;",
        svg,
    )
    return svg


def render_kroki(puml_text: str, fmt: str = "svg") -> bytes:
    url = f"https://kroki.io/plantuml/{fmt}"
    body = puml_text.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8", "User-Agent": "bone-lattice-sim/1.0"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def render_plantuml_dotcom_post(puml_text: str, fmt: str = "svg") -> bytes:
    url = f"https://www.plantuml.com/plantuml/{fmt}"
    body = puml_text.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8", "User-Agent": "bone-lattice-sim/1.0"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def render_local_jar(puml_path: Path, out_path: Path, fmt: str = "svg") -> bytes | None:
    jar = Path(__file__).resolve().parents[1] / "tools" / "plantuml.jar"
    if not jar.is_file():
        return None
    ext = "png" if fmt == "png" else "svg"
    cmd = ["java", "-jar", str(jar), f"-t{ext}", "-o", str(out_path.parent), str(puml_path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        candidate = out_path.parent / f"{puml_path.stem}.{ext}"
        if candidate.is_file():
            data = candidate.read_bytes()
            if (fmt == "png" and _is_png(data)) or (fmt == "svg" and _is_svg(data)):
                return data
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return None


def fetch_svg(puml_text: str, puml_path: Path, out_path: Path) -> bytes:
    errors: list[str] = []
    for name, fn in (
        ("kroki POST", lambda: render_kroki(puml_text, "svg")),
        ("plantuml.com POST", lambda: render_plantuml_dotcom_post(puml_text, "svg")),
    ):
        try:
            candidate = fn()
            if _is_svg(candidate):
                print(f"  {name}: OK ({len(candidate)} bytes)")
                return candidate
            errors.append(f"{name}: invalid svg")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            errors.append(f"{name}: {e}")

    local = render_local_jar(puml_path, out_path, "svg")
    if local and _is_svg(local):
        print("  local plantuml.jar: OK")
        return local

    raise RuntimeError("Не удалось получить SVG:\n" + "\n".join(errors))


def svg_to_png_file(svg_path: Path, png_path: Path) -> bool:
    """SVG → PNG через resvg-js (npx), с корректными <> в подписях."""
    svg_path = svg_path.resolve()
    png_path = png_path.resolve()
    cmd = f'npx -y @resvg/resvg-js-cli "{svg_path}" "{png_path}"'
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=120,
            shell=True,
            cwd=str(svg_path.parent),
        )
        return png_path.is_file() and _is_png(png_path.read_bytes())
    except (FileNotFoundError, subprocess.CalledProcessError, OSError) as e:
        if sys.platform == "win32":
            print(f"  resvg: {e}")
        return False


def render_diagram(puml_path: Path, out_path: Path, fmt: str = "png") -> None:
    text = puml_path.read_text(encoding="utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    svg_raw = fetch_svg(text, puml_path, out_path)
    svg_text = fix_generics_in_svg(svg_raw.decode("utf-8"))

    svg_path = out_path.with_suffix(".svg")
    svg_path.write_text(svg_text, encoding="utf-8")

    if fmt == "svg":
        if out_path != svg_path:
            out_path.write_text(svg_text, encoding="utf-8")
        return

    if svg_to_png_file(svg_path, out_path):
        print("  PNG из SVG (resvg-js), типы с угловыми скобками")
        return

    raise RuntimeError(
        f"Не удалось собрать PNG из {svg_path}. Нужен Node.js (npx). "
        "В отчёт можно вставить SVG — в нём уже List<Cell>."
    )
