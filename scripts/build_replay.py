"""Construye la página estática del modo repetición (docs/index.html, servida por GitHub Pages).

Toma las reseñas propias escritas para la demo (results/demo_propias.json, de `just pipeline
--csv … --out …`) y una selección de la demostración (evals/demo/seleccion_replay.json, sobre
results/pipeline_cola.json) con una nota sobre cada caso, y las incrusta como JSON en
scripts/replay_template.html. Un solo fichero, sin servidor ni modelos: solo lo que la página
muestra (nada de pesos ni cachés).

Uso: uv run python scripts/build_replay.py
"""

import json
from pathlib import Path

from caso_uso_llm.evals.rubric import IDS, criterios
from caso_uso_llm.pipeline import RUBRIC, THRESHOLD
from caso_uso_llm.rag import kb

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (ROOT / "results" / "demo_propias.json",)  # las reseñas propias, completas
# Más una selección de la demostración, con una nota escrita después de ver la respuesta
DEMO = ROOT / "results" / "pipeline_cola.json"
SELECTION = ROOT / "evals" / "demo" / "seleccion_replay.json"
TEMPLATE = ROOT / "scripts" / "replay_template.html"
OUT = ROOT / "docs" / "index.html"
REPO = "https://github.com/JaviRomano/Spanish-hotel-review-LLM"
LINKEDIN = "https://www.linkedin.com/in/franciscojavier-fernandezrumi/"  # prueba en vivo
GROUP = {
    "propio": "Reseñas propias",
    "sintético": "Casos sintéticos",
    "AHR": "Reseñas reales (AHR)",
}


def compact(it: dict, names: dict, policies: dict) -> dict:
    meta = it.get("meta", {})
    hotel = kb.fichas().get(it["hotel"]) if it.get("hotel") else None
    return {
        "id": it["id"],
        "grupo": GROUP.get(meta.get("grupo"), meta.get("grupo", "")),
        "tipo": meta.get("tipo") or (f"{meta['rating']}★" if meta.get("rating") else ""),
        "esperado": meta.get("esperado", ""),
        "nota": "",
        "hotel": f"{hotel['nombre']} ({hotel['ciudad']})" if hotel else "Sin ficha",
        "ficha": kb.ficha_texto(it["hotel"]) if hotel else "",
        "review": it["review"],
        "sentiment": it["sentiment"],
        "confidence": round(it["confidence"], 3),
        "probs": {k: round(v, 3) for k, v in it["probs"].items()},
        "decision": it["decision"],
        "reasons": it["reasons"],
        "response": it.get("response"),
        "judge": [
            {
                "criterio": names[k],
                "cumple": it["judge"][k]["cumple"],
                "evidencia": it["judge"][k]["evidencia"],
            }
            for k in IDS
        ]
        if it.get("judge")
        else [],  # fmt: skip
        "politicas": [policies[p] for p in it.get("politicas", [])],
        "aspectos": (it.get("analysis") or {}).get("aspectos", []),
        "peticiones": (it.get("analysis") or {}).get("peticiones", []),
    }


def main() -> None:
    names = {c.id: c.nombre for c in criterios(RUBRIC)}
    policies = {d.id: d.payload["titulo"] for d in kb.politicas()}
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    skip = set(selection.get("excluir_propias", []))
    cases = []
    for src in SOURCES:
        if src.exists():
            cases += [
                compact(it, names, policies)
                for it in json.loads(src.read_text(encoding="utf-8"))
                if it["id"] not in skip
            ]
    demo = {it["id"]: it for it in json.loads(DEMO.read_text(encoding="utf-8"))}
    for sel in selection["casos"]:
        cases.append(compact(demo[sel["id"]], names, policies) | {"nota": sel["nota"]})
    data = json.dumps({"umbral": THRESHOLD, "casos": cases}, ensure_ascii=False, indent=1)
    # Dentro de <script>, «</» cerraría la etiqueta antes de tiempo
    page = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__DATA__", data.replace("</", "<\\/"))
        .replace("__REPO__", REPO)
        .replace("__LINKEDIN__", LINKEDIN)
    )
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"{len(cases)} casos -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
