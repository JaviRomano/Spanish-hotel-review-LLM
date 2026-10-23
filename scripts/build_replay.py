"""Construye los datos del modo repetición (demo_replay/casos.json) desde los resultados del pipeline.

Junta las 54 reseñas de la demostración de la Fase 5 (results/pipeline_cola.json) y, si existen,
las reseñas propias (results/demo_propias.json, de `just pipeline --csv … --out …`). Guarda solo
lo que la demo muestra: nada de modelos, pesos ni cachés.

Uso: uv run python scripts/build_replay.py
"""

import json
from pathlib import Path

from caso_uso_llm.evals.rubric import IDS, criterios
from caso_uso_llm.pipeline import RUBRIC, THRESHOLD
from caso_uso_llm.rag import kb

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (ROOT / "results" / "demo_propias.json", ROOT / "results" / "pipeline_cola.json")
OUT = ROOT / "demo_replay" / "casos.json"
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
    cases = []
    for src in SOURCES:
        if src.exists():
            cases += [
                compact(it, names, policies) for it in json.loads(src.read_text(encoding="utf-8"))
            ]
    OUT.parent.mkdir(exist_ok=True)
    data = {"umbral": THRESHOLD, "casos": cases}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"{len(cases)} casos -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
