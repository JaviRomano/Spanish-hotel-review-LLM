"""GIF del recorrido guiado (docs/img/recorrido.gif): la página real, paso a paso, sin ejecutar modelos.

Abre docs/index.html, entra en el recorrido y hace una captura de cada paso. Nada se dibuja a mano:
si cambia la página, basta con volver a ejecutarlo.

Uso: uv run --with playwright python scripts/grabar_gif.py
"""

import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs" / "index.html").as_uri()
OUT = ROOT / "docs" / "img" / "recorrido.gif"
VIEWPORT = {"width": 1200, "height": 760}
WIDTH = 900  # px del GIF: legible en el README y con un tamaño razonable
HOLD_MS = 4500  # tiempo de lectura por paso
HERO_MS = 3000
COLORS = 96


def shot(page) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot())).convert("RGB")


def frames() -> list[Image.Image]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, color_scheme="light")
        page.goto(PAGE)
        page.wait_for_timeout(300)
        out = [shot(page)]
        page.click("#tour")
        steps = page.evaluate(
            "JSON.parse(document.getElementById('data').textContent).recorrido.length"
        )
        for i in range(steps):
            page.locator(".desk").evaluate("e => e.scrollIntoView()")
            page.wait_for_timeout(150)
            out.append(shot(page))
            if i < steps - 1:
                page.click("#next")
                page.wait_for_timeout(150)
        browser.close()
    return out


def main() -> None:
    images = frames()
    height = round(images[0].height * WIDTH / images[0].width)
    small = [im.resize((WIDTH, height), Image.Resampling.LANCZOS) for im in images]
    palette = [im.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
               for im in small]  # fmt: skip
    durations = [HERO_MS] + [HOLD_MS] * (len(palette) - 1)
    palette[0].save(OUT, save_all=True, append_images=palette[1:], duration=durations, loop=0,
                    optimize=True)  # fmt: skip
    print(f"{OUT.relative_to(ROOT)}: {len(palette)} fotogramas, {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
