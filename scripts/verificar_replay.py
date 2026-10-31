"""Verifica la página de repetición (docs/index.html) en un navegador real y guarda capturas.

- Capturas a 380 y 1440 px, tema claro y oscuro: cabecera, p08 y p02 -> docs/screenshots/.
- Sin errores de consola ni desbordamiento horizontal.
- Contraste WCAG AA (4,5:1) del texto de badges, cajas y avisos, medido con los colores que
  calcula el navegador en los dos temas.
- Teclado: el selector cambia de caso con las flechas y los fragmentos resaltados muestran su
  explicación al enfocarlos con el tabulador.
- Formulario de prueba en vivo: de punta a punta contra el importador, sin enviar nada a Google.

Playwright no es dependencia del proyecto:
    uv run --with playwright python scripts/verificar_replay.py
"""

import json
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs

from playwright.sync_api import sync_playwright

from caso_uso_llm.formulario import parse_row
from caso_uso_llm.rag import kb

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


def check_form(browser) -> list[str]:
    """Formulario de punta a punta sin Google: se inyecta una configuración de prueba, se intercepta
    el envío y el importador debe aceptar lo que sale de la página."""
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    if ('id="liveform"' in html) == ('id="livetext"' in html):
        return [
            "prueba en vivo: la página debe llevar el formulario o el texto, no ambos ni ninguno"
        ]
    if 'id="liveform"' not in html:
        return []
    fake = '"formulario": {"url": "https://docs.google.com/forms/d/e/PRUEBA/formResponse", "entry": "entry.1"}'
    assert '"formulario": null' in html or '"formulario": {' in html
    html = re.sub(r'"formulario": (null|\{[^}]*\})', fake, html, count=1)
    sent, problems = [], []
    with tempfile.TemporaryDirectory() as tmp:
        page_file = Path(tmp) / "index.html"
        page_file.write_text(html, encoding="utf-8")
        page = browser.new_page(viewport={"width": 380, "height": 840})
        page.route(
            "https://docs.google.com/**",
            lambda r: (sent.append(r.request.post_data), r.fulfill(status=200, body="")),
        )
        page.goto(page_file.as_uri())
        page.click("#livebtn")
        page.click("#sendform")  # vacío: debe rechazarlo sin enviar
        if sent or "cada reseña" not in page.inner_text("#formstatus"):
            problems.append("formulario: envía o no avisa con los campos vacíos")
        page.locator("#formreviews textarea").first.fill("Primera reseña de prueba.")
        page.click("#addreview")
        page.locator("#formreviews textarea").nth(1).fill("Segunda reseña de prueba.")
        page.locator("#formreviews select").nth(1).select_option(index=1)
        page.fill("#f-nick", "prueba.1")
        page.fill("#f-contact", "linkedin.com/in/prueba")
        page.check("#f-consent")
        page.click("#sendform")
        page.wait_for_function("document.getElementById('formstatus').className.includes('good')")
        overflow = page.evaluate("document.documentElement.scrollWidth") - 380
        if overflow > 0:
            problems.append(f"formulario: desborda {overflow} px en móvil")
        page.close()
    if len(sent) != 1:
        return [*problems, f"formulario: {len(sent)} envíos, se esperaba 1"]
    raw = parse_qs(sent[0])["entry.1"][0]
    reviews, contact = parse_row("31/10/2026 12:00:00", raw, set(kb.fichas()))
    if len(reviews) != 2 or contact != "linkedin.com/in/prueba" or reviews[0]["hotel"] is not None:
        problems.append(
            f"formulario: el importador no recibe lo enviado: {json.dumps(reviews)[:200]}"
        )
    return problems


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
        problems += check_form(browser)
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
