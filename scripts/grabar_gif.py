"""GIF del recorrido guiado, en español y en inglés: la página real, sin ejecutar modelos.

Abre docs/index.html y docs/en/index.html, entra en el recorrido y hace una captura de cada paso.
Nada se dibuja a mano: si cambia la página, basta con volver a ejecutarlo.

Uso: uv run --with playwright python scripts/grabar_gif.py
"""

import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = (("index.html", "recorrido.gif"), ("en/index.html", "recorrido_en.gif"))
VIEWPORT = {"width": 1200, "height": 760}
WIDTH = 900  # px del GIF: legible en el README y con un tamaño razonable
HOLD_MS = 4500  # tiempo de lectura por paso
HERO_MS = 3000
COLORS = 96


def shot(page) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot())).convert("RGB")


def frames(url: str) -> list[Image.Image]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, color_scheme="light")
        page.goto(url)
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


def record(source: str, name: str) -> None:
    images = frames((ROOT / "docs" / source).as_uri())
    height = round(images[0].height * WIDTH / images[0].width)
    small = [im.resize((WIDTH, height), Image.Resampling.LANCZOS) for im in images]
    palette = [im.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
               for im in small]  # fmt: skip
    durations = [HERO_MS] + [HOLD_MS] * (len(palette) - 1)
    out = ROOT / "docs" / "img" / name
    palette[0].save(out, save_all=True, append_images=palette[1:], duration=durations, loop=0,
                    optimize=True)  # fmt: skip
    print(f"{out.relative_to(ROOT)}: {len(palette)} fotogramas, {out.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    for source, name in VERSIONS:
        record(source, name)


if __name__ == "__main__":
    main()
