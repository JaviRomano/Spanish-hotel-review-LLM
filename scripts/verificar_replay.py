"""Verifica la página de repetición (docs/index.html) en un navegador real y guarda capturas.

- Capturas a 380 y 1440 px, tema claro y oscuro: cabecera, p08 y p02 -> docs/screenshots/.
- Sin errores de consola ni desbordamiento horizontal.
- Contraste WCAG AA (4,5:1) del texto de badges, cajas y avisos, medido con los colores que
  calcula el navegador en los dos temas.
- Teclado: el selector cambia de caso con las flechas y los fragmentos resaltados muestran su
  explicación al enfocarlos con el tabulador.

Playwright no es dependencia del proyecto:
    uv run --with playwright python scripts/verificar_replay.py
"""

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs" / "index.html").as_uri()
SHOTS = ROOT / "docs" / "screenshots"
# Texto sobre fondo de color: selector del elemento cuyo color y fondo se comparan
CONTRAST = [".pill.ok", ".pill.no", ".pill.partial", ".pill.mode", ".pill.neutral", ".note",
            ".rating p", ".rating .head", ".alertbox", ".stamp", ".reasons li",
            ".spec dt", ".spec dd", ".label", ".btn.primary", "mark",
            ".inspect td", ".criterion p", ".flow li span"]  # fmt: skip


def _rgb(s: str) -> tuple[float, ...]:
    return tuple(float(x) for x in re.findall(r"[\d.]+", s)[:3])


def _lum(c: tuple[float, ...]) -> float:
    lin = [
        (v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in c
    ]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((_lum(_rgb(a)), _lum(_rgb(b))), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


BG = """el => { let n = el; while (n) { const c = getComputedStyle(n).backgroundColor;
  if (c && !c.startsWith('rgba(0, 0, 0, 0)') && c !== 'transparent') return c; n = n.parentElement; }
  return getComputedStyle(document.body).backgroundColor; }"""


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in ("light", "dark"):
            for width, height in ((380, 840), (1440, 1000)):
                page = browser.new_page(
                    viewport={"width": width, "height": height}, color_scheme=theme
                )
                errors = []
                page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
                page.on(
                    "console", lambda m, errors=errors: m.type == "error" and errors.append(m.text)
                )
                for view, hash_ in (("cabecera", ""), ("p08", "#p08"), ("p02", "#p02")):
                    page.goto(PAGE + hash_)
                    page.wait_for_timeout(300)
                    if hash_:
                        page.locator("#summary").scroll_into_view_if_needed()
                    page.screenshot(path=SHOTS / f"{view}_{width}_{theme}.png")
                    overflow = page.evaluate("document.documentElement.scrollWidth") - width
                    if overflow > 0:
                        problems.append(f"{view} {width} {theme}: desborda {overflow} px")
                    for sel in CONTRAST:
                        for loc in page.locator(sel).all()[:3]:
                            if not loc.is_visible():
                                continue
                            fg = loc.evaluate("el => getComputedStyle(el).color")
                            r = ratio(fg, loc.evaluate(BG))
                            if r < 4.5:
                                problems.append(
                                    f"{theme} {width} {view}: contraste {r:.2f} en {sel}"
                                )
                problems += [f"{theme} {width}: error de consola: {e}" for e in errors]
                page.close()

        # Teclado: el selector responde a las flechas y los resaltados muestran su explicación
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(PAGE + "#p02")
        page.focus("#case")
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(200)
        if page.evaluate("location.hash") == "#p02":
            problems.append("teclado: las flechas no cambian de caso en el selector")
        page.goto(PAGE + "#p02")
        page.wait_for_timeout(200)
        page.focus("mark")
        if not page.locator("mark .tip").first.is_visible():
            problems.append("teclado: el resaltado enfocado no muestra su explicación")
        browser.close()

    shots = sorted(f.name for f in SHOTS.glob("*.png"))
    print(f"{len(shots)} capturas en {SHOTS.relative_to(ROOT)}")
    print(
        "\n".join(problems)
        if problems
        else "OK: sin errores de consola, sin desbordes, contraste AA y teclado"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
