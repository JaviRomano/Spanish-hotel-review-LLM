"""Capturas de la demo para el README (Playwright; no es dependencia del proyecto).

Con la app en marcha (`uv run just app`), procesa un caso sintético y captura las dos pestañas en
docs/img/. Antes de capturar, LEER las dos respuestas: la captura del README debe mostrar una
respuesta correcta (la anterior, rag-carteles, admitía la culpa de forma implícita). La cola de
la app incluye las reseñas de la demo en vivo (data/live/): apartar cola_app.jsonl mientras se
captura para que no salgan reseñas ni nicks de terceros, y restaurar resenas_vivo.jsonl después.

Uso:
    uv run --with playwright playwright install chromium     # una vez
    uv run --with playwright python scripts/capturas.py
"""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
URL = "http://127.0.0.1:7860/?__theme=light"
CASE = "adv-4estrellas-queja"  # publicable: la explicación del wifi sale de la ficha
QUEUE_CASE = "ahr-ahr-683"  # reseña real de 4★ a revisión por confianza baja; borrador correcto


def main() -> None:
    adv = ROOT / "evals" / "adversarial"
    rag = json.loads((adv / "rag_v1.json").read_text(encoding="utf-8"))
    gen = json.loads((adv / "generacion_v1.json").read_text(encoding="utf-8"))
    hotels = rag["hoteles_generacion_v1"]  # los casos de la Fase 4 llevan el hotel aparte
    cases = rag["cases"] + [c | {"hotel": hotels[c["id"]]} for c in gen["cases"]]
    case = next(c for c in cases if c["id"] == CASE)
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1400, "height": 1000})
        page.goto(URL)
        hotel = page.get_by_label("Hotel")
        hotel.click()
        page.get_by_role("option", name=case["hotel"], exact=False).first.click()
        # La app guarda lo que se envía en data/live/resenas_vivo.jsonl: restaurar ese fichero
        # después de capturar (este caso es sintético, no una reseña de la demo en vivo).
        page.get_by_label("Tu nick (no tu nombre)").fill("demo")
        page.get_by_label("Reseña", exact=True).fill(case["review"])
        page.get_by_role("checkbox").first.check()
        page.get_by_role("button", name="Generar respuesta").click()
        page.get_by_text("Publicable sin revisión", exact=False).first.wait_for(timeout=600_000)
        page.get_by_text("Detalle del pipeline").click()
        page.wait_for_timeout(800)
        page.screenshot(path=OUT / "demo_respuesta.png", full_page=True)

        page.get_by_role("tab", name="Cola de revisión").click()
        page.wait_for_timeout(1500)
        selector = page.get_by_label("Reseña a revisar")
        selector.click()
        page.get_by_role("option", name=QUEUE_CASE, exact=True).first.click()
        page.wait_for_timeout(1500)
        page.screenshot(path=OUT / "demo_cola.png", full_page=True)
    print(sorted(p.name for p in OUT.glob("demo_*.png")))


if __name__ == "__main__":
    main()
