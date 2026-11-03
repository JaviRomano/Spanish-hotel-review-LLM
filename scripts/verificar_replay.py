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
PAGE_EN = (ROOT / "docs" / "en" / "index.html").as_uri()
SHOTS = ROOT / "docs" / "screenshots"
# Texto de la interfaz que no debe quedar en la versión inglesa
SPANISH = ("pasa a una persona", "se publica sola", "Mi valoración", "Puerta", "Motivos de la puerta",
           "Inspección del juez", "sin valorar", "Paso ", "Criterio escrito", "Ver más")  # fmt: skip
# Texto sobre fondo de color: selector del elemento cuyo color y fondo se comparan
CONTRAST = [".pill.ok", ".pill.no", ".pill.partial", ".pill.mode", ".pill.neutral", ".note",
            ".rating p", ".rating .head", ".alertbox", ".stamp", ".reasons li",
            ".headline", ".evidence > p", "table.data td", ".label", ".btn.primary", "mark",
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


def check_english(browser) -> list[str]:
    """Versión inglesa: sin errores ni desbordes, todos los casos sin interfaz en español."""
    problems = []
    for width in (375, 1280):
        page = browser.new_page(viewport={"width": width, "height": 800})
        errors = []
        page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
        page.goto(PAGE_EN)
        ids = page.evaluate("[...document.getElementById('case').options].map(o => o.value)")
        for case in ids:
            page.select_option("#case", case)
            page.wait_for_timeout(30)
            text = " ".join(
                page.inner_text(s) for s in ("#summary", "#stamp", "#h-judge", "#reasons")
            )
            problems += [f"inglés {case}: queda «{w}»" for w in SPANISH if w in text]
            if page.evaluate("document.documentElement.scrollWidth") > width:
                problems.append(f"inglés {width} {case}: desborda")
        problems += [f"inglés {width}: error de consola: {e}" for e in errors]
        page.close()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(PAGE_EN)
    page.click(".fold summary")
    page.click('a[href="#resultados"]')
    page.wait_for_timeout(200)
    if page.evaluate("location.hash") != "#resultados":
        problems.append("inglés: el enlace a resultados no funciona")
    page.locator("table.matrix a").last.click()
    page.wait_for_timeout(200)
    if page.input_value("#case") != page.evaluate("location.hash.slice(1)"):
        problems.append("inglés: la matriz no abre su caso")
    if page.get_attribute('a[hreflang="es"]', "href") != "../":
        problems.append("inglés: falta el enlace a la versión en español")
    page.close()
    return problems


def check_tour(browser) -> list[str]:
    """Al recorrer los casos no queda ningún aviso vacío, y el botón se oculta durante el recorrido."""
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(PAGE)
    page.click("#tour")
    problems = []
    if page.locator("#tour").is_visible():
        problems.append("recorrido: el botón sigue visible durante el recorrido")
    steps = page.evaluate(
        "JSON.parse(document.getElementById('data').textContent).recorrido.length"
    )
    for _ in range(steps):
        if page.locator("#alert").is_visible() and not page.inner_text("#alert").strip():
            problems.append(f"recorrido: aviso vacío en {page.input_value('#case')}")
        page.click("#next")
    page.close()
    return problems


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


def check_text(browser) -> list[str]:
    """Jerarquía de títulos sin saltos y un solo «Por eso» en el texto y los pasos."""
    page = browser.new_page()
    page.goto(PAGE)
    levels = page.evaluate("[...document.querySelectorAll('h1,h2,h3,h4')].map(h => +h.tagName[1])")
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    page.close()
    problems = []
    if levels[0] != 1 or any(b - a > 1 for a, b in zip(levels, levels[1:], strict=False)):
        problems.append(f"títulos: la jerarquía tiene saltos: {levels}")
    if len(re.findall("por eso", html, re.IGNORECASE)) != 1:
        problems.append("texto: debe quedar un solo «Por eso»")
    return problems


def check_links(browser) -> list[str]:
    """Matriz, enlaces a secciones y resaltado al tocarlo en una pantalla táctil."""
    problems = []
    page = browser.new_context(viewport={"width": 375, "height": 760}, has_touch=True).new_page()
    page.goto(PAGE)
    page.click(".fold summary")
    page.click('a[href="#resultados"]')
    page.wait_for_timeout(200)
    if page.evaluate("location.hash") != "#resultados":
        problems.append("enlaces: un enlace a una sección lo captura el visor de casos")
    page.goto(PAGE + "#conjuntos")
    page.wait_for_timeout(200)
    if page.evaluate("location.hash") != "#conjuntos":
        problems.append("enlaces: abrir la página en una sección no la respeta")
    page.locator("table.matrix a").last.click()
    page.wait_for_timeout(200)
    if page.input_value("#case") != page.evaluate("location.hash.slice(1)"):
        problems.append("matriz: el identificador no abre su caso en el visor")
    page.goto(PAGE + "#p02")
    page.wait_for_timeout(200)
    page.locator("mark").first.tap()
    if not page.locator("mark .tip").first.is_visible():
        problems.append("táctil: tocar un resaltado no muestra su explicación")
    page.close()
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
        problems += check_links(browser)
        problems += check_tour(browser)
        problems += check_english(browser)
        problems += check_text(browser)
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
