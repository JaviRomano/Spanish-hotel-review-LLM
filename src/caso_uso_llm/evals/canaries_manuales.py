"""Canaries manuales del autor frente al juez de producción, con la ficha si el caso tiene hotel.

Es un informe, no una puerta: se espera que el juez falle alguno, porque se escriben a partir de
fallos que deja pasar, y saber cuáles es el objetivo. Un canary se detecta si el juez suspende todos
sus criterios esperados; un control está limpio si no suspende ninguno.

Uso: uv run just canaries-manuales
"""

import json

from caso_uso_llm.evals.judge import JUDGE_MODEL, OPTIONS, judge
from caso_uso_llm.evals.rubric import IDS, criterios
from caso_uso_llm.generate.run import Cache
from caso_uso_llm.log import log
from caso_uso_llm.ollama_gpu import require_gpu
from caso_uso_llm.paths import EVALS, RESULTS, ROOT
from caso_uso_llm.pipeline import JUDGE_CACHE, RUBRIC, ficha

SRC = EVALS / "canaries" / "manuales_v1.json"
OUT = RESULTS / "phase6_canaries_manuales.json"
REPORT = ROOT / "reports" / "phase6_canaries_manuales.md"
NAMES = {c.id: c.nombre for c in criterios(RUBRIC)}


def check(items: list[dict]) -> None:
    for it in items:
        unknown = set(it["expected_fail"]) - set(IDS)
        assert not unknown, f"{it['id']}: criterios desconocidos {sorted(unknown)}"
        assert it["clase"] == "control" or it["expected_fail"], f"{it['id']}: sin criterio"


def score(items: list[dict], got: dict[str, set[str]]) -> dict:
    rows = [
        {"id": it["id"], "clase": it["clase"], "origen": it["origen"],
         "esperado": sorted(it["expected_fail"]), "juez": sorted(got[it["id"]]),
         "ok": set(it["expected_fail"]) <= got[it["id"]] if it["clase"] == "canary"
         else not got[it["id"]]}
        for it in items
    ]  # fmt: skip
    canaries = [r for r in rows if r["clase"] == "canary"]
    controls = [r for r in rows if r["clase"] == "control"]
    return {
        "rows": rows,
        "canaries": (sum(r["ok"] for r in canaries), len(canaries)),
        "reales": (sum(r["ok"] for r in canaries if r["origen"] == "real"),
                   sum(r["origen"] == "real" for r in canaries)),
        "controles": (sum(r["ok"] for r in controls), len(controls)),
    }  # fmt: skip


def write_report(s: dict) -> None:
    names = lambda ids: ", ".join(NAMES[i] for i in ids) or "—"  # noqa: E731
    pair = lambda p: f"{p[0]} de {p[1]}"  # noqa: E731
    L = [
        "# Fase 6 · Canaries manuales frente al juez",
        "",
        f"Generado por `uv run just canaries-manuales` · juez `{JUDGE_MODEL}`, rúbrica {RUBRIC}, con "
        "la ficha si el caso tiene hotel. Casos del autor en "
        "[`manuales_v1.json`](../evals/canaries/manuales_v1.json). Es un informe, no una puerta. "
        "No editar a mano.",
        "",
        f"- Canaries detectados: {pair(s['canaries'])} (fallos reales: {pair(s['reales'])}).",
        f"- Controles limpios: {pair(s['controles'])}.",
        "",
        "| Caso | Tipo | Origen | Esperado | Juez | Resultado |",
        "|---|---|---|---|---|---|",
    ]
    for r in s["rows"]:
        L.append(f"| `{r['id']}` | {r['clase']} | {r['origen']} | {names(r['esperado'])} | "
                 f"{names(r['juez'])} | {'bien' if r['ok'] else '**falla**'} |")  # fmt: skip
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    items = json.loads(SRC.read_text(encoding="utf-8"))["items"]
    check(items)
    require_gpu(JUDGE_MODEL, OPTIONS["num_ctx"])
    cache, got = Cache(JUDGE_CACHE), {}
    for it in items:
        v = judge(it["review"], it["response"], cache, RUBRIC, ficha(it["hotel"] or None))
        got[it["id"]] = {c for c in IDS if not v[c]["cumple"]}
        log(f"   {it['id']}: esperado {it['expected_fail']} · juez {sorted(got[it['id']])}")
    s = score(items, got)
    OUT.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                   newline="\n")  # fmt: skip
    write_report(s)
    print(REPORT)


if __name__ == "__main__":
    main()
