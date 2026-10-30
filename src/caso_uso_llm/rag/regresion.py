"""Fase 9 · Regresión de prompts en las mismas condiciones: ¿se adopta v9 en el pipeline?

`rag-generar` / `rag-juez` comparan ficheros generados en momentos distintos (cada uno con la kb/
de su commit): una diferencia mezclaría el prompt con la base de conocimiento. Aquí todas las
versiones pasan por el pipeline actual (detector de trampas v2, misma kb/, mismos 54 casos de la
demostración) y por el mismo juez, con la rúbrica v2h y la ficha:

- suspensos por criterio y respuestas reales que cumplen todo;
- destino con el enrutado del pipeline (juez v2g, como en producción) y publicables;
- comparación por pares con la base (v6), en los dos órdenes (lo inconsistente cuenta como empate);
- aperturas: respuestas con saludo «Estimado/a…» y la primera frase más repetida.

Criterio automático para adoptar v9 (decisión de Javier, 2026-10-30): no más suspensos de «no
admite culpa» que v6 y no perder por pares frente a v6. Falta después la valoración humana de
reseñas NUEVAS: este informe no la sustituye.

Uso: uv run just regresion                    # v6, v8 y v9
     uv run just regresion --prompts v6,v9
"""

import argparse
import json
import re
from collections import Counter

from caso_uso_llm.evals.judge import JUDGE_MODEL, compare, judge
from caso_uso_llm.evals.rubric import IDS, criterios
from caso_uso_llm.generate.run import MODEL, Cache
from caso_uso_llm.log import log
from caso_uso_llm.paths import RESULTS, ROOT
from caso_uso_llm.pipeline import (
    JUDGE_CACHE,
    PUBLISH,
    QUEUE,
    ficha,
    generate_stage,
    judge_stage,
)

RUBRIC = "v2h"
BASE = "v6"
REPORT = ROOT / "reports" / "phase9_regresion.md"
OUT = RESULTS / "phase9_regresion.json"
NAMES = {c.id: c.nombre for c in criterios(RUBRIC)}
SALUDO = re.compile(r"^\s*Estimad[oa]s?\b", re.IGNORECASE)


def demo_items() -> list[dict]:
    """Los 54 casos de la demostración (14 sintéticos con hotel y 40 reales del AHR)."""
    cola = json.loads(QUEUE.read_text(encoding="utf-8"))
    return [{k: c[k] for k in ("id", "hotel", "text", "meta") if k in c}
            | {"title": c.get("title", "")} for c in cola]  # fmt: skip


def first_sentence(response: str) -> str:
    """Primera frase tras el saludo (si lo hay), en sus 5 primeras palabras."""
    lines = [x.strip() for x in response.strip().splitlines() if x.strip()]
    if lines and SALUDO.match(lines[0]) and len(lines) > 1:
        lines = lines[1:]
    first = re.split(r"(?<=[.!?])\s", lines[0])[0] if lines else ""
    return " ".join(first.split()[:5])


def run(prompts: list[str]) -> dict:
    from caso_uso_llm.classify.infer import SentimentEnsemble

    items, classifier = demo_items(), SentimentEnsemble()
    jcache = Cache(JUDGE_CACHE)
    res = {}
    for p in prompts:
        log(f"== {p}: pipeline (generación) sobre {len(items)} casos")
        out = generate_stage(items, classifier, p)
        out = judge_stage(out)  # enrutado de producción (juez v2g)
        log(f"== {p}: juez {RUBRIC} con ficha")
        for it in out:
            if it["response"] is not None:
                v = judge(it["review"], it["response"], jcache, RUBRIC, ficha(it["hotel"]))
                it["judge_v2h"] = {k: v[k]["cumple"] for k in IDS}
        res[p] = out
    pairs = {}
    for p in prompts:
        if p == BASE:
            continue
        log(f"== pares {BASE} frente a {p}")
        score = Counter()
        for a, b in zip(res[BASE], res[p], strict=True):
            if a["response"] is None or b["response"] is None:
                continue
            f = ficha(a["hotel"])
            ab = compare(a["review"], a["response"], b["response"], jcache, f)
            ba = compare(a["review"], b["response"], a["response"], jcache, f)
            winner = BASE if (ab, ba) == ("A", "B") else p if (ab, ba) == ("B", "A") else "empate"
            score[winner] += 1
        pairs[p] = dict(score)
    return {"res": res, "pairs": pairs}


def summarize(res: dict, pairs: dict) -> dict:
    s = {}
    for p, out in res.items():
        judged = [it for it in out if "judge_v2h" in it]
        real = [it for it in judged if it["meta"]["grupo"] == "AHR"]
        genuine = [it for it in judged if it.get("genuina") is not False]
        firsts = Counter(first_sentence(it["response"]) for it in genuine)
        top, top_n = firsts.most_common(1)[0] if firsts else ("", 0)
        s[p] = {
            "suspensos": {k: sum(not it["judge_v2h"][k] for it in judged) for k in IDS},
            "reales_cumplen_todo": sum(all(it["judge_v2h"].values()) for it in real),
            "reales": len(real),
            "publicables": sum(it["decision"] == PUBLISH for it in out),
            "trampas": sum(it.get("genuina") is False for it in out),
            "saludo": sum(bool(SALUDO.match(it["response"])) for it in genuine),
            "genuinas": len(genuine),
            "primera_frase_top": top,
            "primera_frase_top_n": top_n,
        }
    for p, score in pairs.items():
        s[p]["pares_vs_base"] = score
    return s


def write_report(s: dict) -> None:
    prompts = list(s)
    L = [
        "# Fase 9 · Regresión de prompts en las mismas condiciones",
        "",
        f"Generado por `uv run just regresion` · generador `{MODEL}` · juez `{JUDGE_MODEL}` con "
        f"rúbrica `{RUBRIC}` y ficha · pipeline actual (detector de trampas v2, `kb/` actual) "
        "sobre los 54 casos de la demostración (14 sintéticos, 40 reales del AHR). No editar a mano.",
        "",
        "## Suspensos del juez por criterio",
        "",
        "| Criterio | " + " | ".join(prompts) + " |",
        "|---|" + "---|" * len(prompts),
    ]
    for k in IDS:
        L.append(f"| {NAMES[k]} | " + " | ".join(str(s[p]["suspensos"][k]) for p in prompts) + " |")
    L += [
        "",
        "## Resumen",
        "",
        "| | " + " | ".join(prompts) + " |",
        "|---|" + "---|" * len(prompts),
        "| Reales que cumplen todo | "
        + " | ".join(f"{s[p]['reales_cumplen_todo']}/{s[p]['reales']}" for p in prompts)
        + " |",
        "| Publicables (enrutado de producción) | "
        + " | ".join(str(s[p]["publicables"]) for p in prompts)
        + " |",
        "| Reseñas trampa | " + " | ".join(str(s[p]["trampas"]) for p in prompts) + " |",
        "| Empiezan con «Estimado/a…» | "
        + " | ".join(f"{s[p]['saludo']}/{s[p]['genuinas']}" for p in prompts)
        + " |",
        "| Primera frase más repetida | "
        + " | ".join(
            f"«{s[p]['primera_frase_top']}…» ({s[p]['primera_frase_top_n']})" for p in prompts
        )
        + " |",  # fmt: skip
    ]
    L += ["", f"## Por pares frente a {BASE} (los dos órdenes; lo inconsistente, empate)", ""]
    for p in prompts:
        if p != BASE:
            sc = s[p]["pares_vs_base"]
            L.append(f"- {p}: gana {sc.get(p, 0)}, pierde {sc.get(BASE, 0)}, "
                     f"empata {sc.get('empate', 0)}.")  # fmt: skip
    if "v9" in s and BASE in s:
        culpa_ok = s["v9"]["suspensos"]["sin_culpa"] <= s[BASE]["suspensos"]["sin_culpa"]
        sc = s["v9"]["pares_vs_base"]
        pares_ok = sc.get("v9", 0) >= sc.get(BASE, 0)
        L += [
            "",
            "## Criterio automático de adopción de v9",
            "",
            f"- «No admite culpa»: v9 {s['v9']['suspensos']['sin_culpa']} frente a {BASE} "
            f"{s[BASE]['suspensos']['sin_culpa']} → {'cumple' if culpa_ok else 'NO cumple'}.",
            f"- Por pares frente a {BASE}: {'no pierde' if pares_ok else 'PIERDE'} "
            f"({sc.get('v9', 0)} a {sc.get(BASE, 0)}).",
            f"- **{'Pasa' if culpa_ok and pares_ok else 'No pasa'}** la parte automática. Falta la "
            "valoración humana de reseñas nuevas (no las 42 con las que se escribió v9).",
        ]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", default="v6,v8,v9")
    args = ap.parse_args()
    prompts = args.prompts.split(",")
    if BASE not in prompts:
        prompts.insert(0, BASE)
    r = run(prompts)
    s = summarize(r["res"], r["pairs"])
    OUT.write_text(json.dumps({"resumen": s, "respuestas": {p: [
        {"id": it["id"], "response": it["response"], "decision": it["decision"],
         "reasons": it["reasons"], "judge_v2h": it.get("judge_v2h")} for it in out]
        for p, out in r["res"].items()}}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")  # fmt: skip
    write_report(s)
    log(f"Informe: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
