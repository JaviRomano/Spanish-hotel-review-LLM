"""Prepara la comparación de v6 frente a v6 sin saludo ni agradecimiento genérico.

Solo recorta texto ya generado (generate/aperturas.py): no llama a ningún modelo. Lo que recorta
sale de data/live/tandas_01-03_v6.json, 30 reseñas que no se usaron para escribir la regla, y se
queda en data/live (fuera de git).

Uso: uv run python scripts/variante_aperturas.py
     uv run python scripts/comparacion_ciegas.py hoja --a data/live/tandas_01-03_v6.json \
         --b data/live/tandas_01-03_v6sin.json --resenas data/live/tandas_01-03.jsonl --tag ciegas_aperturas
"""

import json

from caso_uso_llm.generate.aperturas import strip_opening
from caso_uso_llm.paths import ROOT

SRC = ROOT / "data" / "live" / "tandas_01-03_v6.json"
OUT = ROOT / "data" / "live" / "tandas_01-03_v6sin.json"


def main() -> None:
    items = json.loads(SRC.read_text(encoding="utf-8"))
    out = [it | {"response": strip_opening(it["response"])} for it in items if it.get("response")]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                   newline="\n")  # fmt: skip
    print(f"{len(out)} respuestas -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
