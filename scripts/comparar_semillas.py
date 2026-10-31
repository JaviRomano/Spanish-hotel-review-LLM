"""Semillas del gold: etiquetas de Claude frente a la primera pasada humana a ciegas y al juez.

Compara evals/gold/semillas_fase4.json (Claude) con semillas_primera_pasada.csv (persona, con ids
opacos y sin ver las de Claude ni la versión del prompt) y con los veredictos ya guardados del juez
en results/phase6_juez.json. No llama a ningún modelo. La primera pasada no se corrige después de
ver esto.

Uso: uv run just semillas
"""

import csv
import json

from caso_uso_llm.evals.rubric import criterios
from caso_uso_llm.paths import EVALS, RESULTS, ROOT

GOLD = EVALS / "gold" / "semillas_fase4.json"
HUMAN = EVALS / "gold" / "semillas_primera_pasada.csv"
MAPPING = EVALS / "gold" / "semillas_mapa.json"
JUDGE = RESULTS / "phase6_juez.json"
OUT = RESULTS / "phase6_semillas.json"
REPORT = ROOT / "reports" / "phase6_semillas_humanas.md"
VERSIONS = ("v1", "v2", "v3")
NAMES = {c.id: c.nombre for c in criterios("v2")}


def fails(by_item: dict[str, list[str]]) -> set[tuple[str, str]]:
    return {(item, c) for item, cs in by_item.items() for c in cs}


def read_human() -> tuple[dict[str, list[str]], dict[str, str]]:
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    with HUMAN.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    assert set(mapping) == {r["id"] for r in rows}, "la hoja no cubre las mismas semillas"
    labels, notes = {}, {}
    for r in rows:
        real = mapping[r["id"]]
        labels[real] = [k.removeprefix("humano_") for k, v in r.items()
                        if k.startswith("humano_") and v == "0"]  # fmt: skip
        notes[real] = " ".join(r["notas"].split())
    return labels, notes


def compare(reference: set, other: set) -> dict:
    return {"referencia": len(reference), "coinciden": len(reference & other),
            "de_mas": len(other - reference)}  # fmt: skip


def main() -> None:
    gold = {it["id"]: sorted(it["no_cumple"]) for it in
            json.loads(GOLD.read_text(encoding="utf-8"))["items"]}  # fmt: skip
    human, notes = read_human()
    judge_doc = json.loads(JUDGE.read_text(encoding="utf-8"))["rubrics"]
    judge = {v: {r["id"]: r["got"] for r in judge_doc[v]["gold"]["rows"]} for v in VERSIONS}
    results = {
        "claude_frente_a_persona": compare(fails(human), fails(gold)),
        "juez_frente_a_persona": {v: compare(fails(human), fails(judge[v])) for v in VERSIONS},
        "juez_frente_a_claude": {v: compare(fails(gold), fails(judge[v])) for v in VERSIONS},
        "items": [
            {
                "id": i,
                "claude": gold[i],
                "persona": human[i],
                "juez_v2": sorted(judge["v2"][i]),
                "nota": notes[i],
            }
            for i in gold
        ],  # fmt: skip
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                   newline="\n")  # fmt: skip
    write_report(results)
    print(REPORT)


def write_report(r: dict) -> None:
    c = r["claude_frente_a_persona"]
    label = lambda ids: ", ".join(NAMES[i] for i in ids) or "—"  # noqa: E731
    L = [
        "# Fase 6 · Semillas del gold: etiquetas de Claude frente a una persona",
        "",
        "Generado por `uv run just semillas` · 10 respuestas reales del generador (prompts v1 y v2), "
        "8 criterios por respuesta. Primera pasada humana a ciegas, congelada antes de comparar "
        "([`semillas_primera_pasada.csv`](../evals/gold/semillas_primera_pasada.csv)). "
        "Los veredictos del juez son los de `results/phase6_juez.json`. No editar a mano.",
        "",
        f"Suspensos marcados: persona {c['referencia']}, Claude {c['coinciden'] + c['de_mas']}; "
        f"coinciden {c['coinciden']}.",
        "",
        "| Rúbrica del juez | Suspensos de la persona que detecta | Suspensos de más | "
        "Suspensos de Claude que detecta |",
        "|---|---|---|---|",
    ]
    for v in VERSIONS:
        p, g = r["juez_frente_a_persona"][v], r["juez_frente_a_claude"][v]
        L.append(f"| {v} | {p['coinciden']} de {p['referencia']} | {p['de_mas']} | "
                 f"{g['coinciden']} de {g['referencia']} |")  # fmt: skip
    L += ["", "## Por respuesta", "", "| Respuesta | Claude | Persona | Juez v2 | Nota |",
          "|---|---|---|---|---|"]  # fmt: skip
    for it in r["items"]:
        note = it["nota"].replace("|", "/")
        L.append(f"| `{it['id']}` | {label(it['claude'])} | {label(it['persona'])} | "
                 f"{label(it['juez_v2'])} | {note} |")  # fmt: skip
    L += [
        "",
        "Muestra muy pequeña: sirve para saber si el gold de Claude era fiable, no para medir el juez. "
        "La calibración del juez es [`phase6_calibracion.md`](phase6_calibracion.md).",
    ]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
