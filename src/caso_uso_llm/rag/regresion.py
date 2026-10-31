"""Fase 9 · Regresión de prompts en las mismas condiciones: ¿se adopta v9 en el pipeline?

`rag-generar` / `rag-juez` comparan ficheros generados en momentos distintos (cada uno con la kb/
de su commit): una diferencia mezclaría el prompt con la base de conocimiento. Aquí todas las
versiones pasan por el pipeline actual (detector de trampas v2, misma kb/, mismos 54 casos de la
demostración) y por el mismo juez, con la rúbrica v2i y la ficha:

- suspensos por criterio y respuestas reales que cumplen todo;
- destino con el enrutado del pipeline (juez v2g, como en producción) y publicables;
- comparación por pares con la base (v6), en los dos órdenes (lo inconsistente cuenta como empate);
- aperturas: saludos y la primera frase más repetida; finalidades recortadas tras «revisaremos».

Antes, dos puertas con canaries redactados por Claude: la del juez de pares v2 (prefiere el usted al
tuteo; no prefiere «Estimado» a «Hola») y la de la rúbrica v2i («Hola:» con usted cumple el
registro; el tuteo no).

Criterio (Javier, 2026-10-30, tras ver que el juez contradice sus decisiones de estilo): el juez
es un FILTRO DE SEGURIDAD; v9 no puede tener más suspensos que v6 en prometer compensaciones,
inventar datos ni confirmar o negar lo que no se puede comprobar. «No admite culpa» y los pares se
informan, pero no deciden: decide la valoración humana a ciegas de reseñas NUEVAS (las tandas).

Uso: uv run just regresion                    # v6, v8 y v9
     uv run just regresion --prompts v6,v9
"""

import argparse
import json
import re
from collections import Counter

from caso_uso_llm.evals.judge import JUDGE_MODEL, compare, judge
from caso_uso_llm.evals.rubric import IDS, criterios
from caso_uso_llm.evals.variedad import opening
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
from caso_uso_llm.spec import SALUDOS

RUBRIC = "v2i"
SAFETY = ("sin_promesa", "sin_invencion", "sin_premisa")  # filtro de seguridad para adoptar
BASE = "v6"
REPORT = ROOT / "reports" / "phase9_regresion.md"
OUT = RESULTS / "phase9_regresion.json"
NAMES = {c.id: c.nombre for c in criterios(RUBRIC)}
ESTIMADO = re.compile(r"^\s*Estimad[oa]s?\b", re.IGNORECASE)
PAIR_VERSION = "v2"  # el saludo no cuenta (judge.PAIR_SALUDO)
# Puerta del juez de pares: una reseña neutra inventada y tres respuestas redactadas por Claude.
CANARY_REVIEW = "Habitación limpia y amplia, el desayuno correcto. Volveríamos."
_BODY = (
    "Nos alegra que la habitación le resultara limpia y amplia, y tomamos nota de su opinión sobre "
    "el desayuno. Será un placer recibirle de nuevo cuando vuelva a visitarnos.\n\nEl equipo del hotel"
)
CANARY_HOLA, CANARY_ESTIMADO = f"Hola:\n\n{_BODY}", f"Estimado cliente:\n\n{_BODY}"
CANARY_TU = (
    "¡Hola!\n\nNos alegra que la habitación te pareciera limpia y amplia, y tomamos nota de lo que "
    "dices del desayuno. ¡Te esperamos cuando quieras volver!\n\nEl equipo del hotel"
)


def demo_items() -> list[dict]:
    """Los 54 casos de la demostración (14 sintéticos con hotel y 40 reales del AHR)."""
    cola = json.loads(QUEUE.read_text(encoding="utf-8"))
    return [{k: c[k] for k in ("id", "hotel", "text", "meta") if k in c}
            | {"title": c.get("title", "")} for c in cola]  # fmt: skip


def first_sentence(response: str) -> str:
    """Primera frase tras el saludo (si lo hay), en sus 5 primeras palabras."""
    return " ".join(opening(response)[1].split()[:5])


def both_orders(review: str, a: str, b: str, cache, f) -> str:
    """'A', 'B' o 'empate' con los dos órdenes (lo inconsistente cuenta como empate)."""
    ab = compare(review, a, b, cache, f, PAIR_VERSION)
    ba = compare(review, b, a, cache, f, PAIR_VERSION)
    return "A" if (ab, ba) == ("A", "B") else "B" if (ab, ba) == ("B", "A") else "empate"


def pair_gate(cache) -> dict:
    """El juez de pares v2 debe preferir el usted al tuteo y no preferir «Estimado» a «Hola»."""
    usted = both_orders(CANARY_REVIEW, CANARY_HOLA, CANARY_TU, cache, None)
    saludo = both_orders(CANARY_REVIEW, CANARY_HOLA, CANARY_ESTIMADO, cache, None)
    # Rúbrica v2i: «Hola:» con usted cumple el registro y el tuteo no (sin ficha: «No disponible.»)
    hola_ok = judge(CANARY_REVIEW, CANARY_HOLA, cache, RUBRIC, "No disponible.")["registro"][
        "cumple"
    ]
    tu_ok = judge(CANARY_REVIEW, CANARY_TU, cache, RUBRIC, "No disponible.")["registro"]["cumple"]
    return {"usted_frente_a_tu": usted, "hola_frente_a_estimado": saludo,
            "registro_hola_cumple": hola_ok, "registro_tuteo_cumple": tu_ok,
            "pasa": usted == "A" and saludo != "B" and hola_ok and not tu_ok}  # fmt: skip


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
    gate = pair_gate(jcache)
    log(f"Puerta del juez de pares: {gate}")
    pairs = {}
    for p in prompts:
        if p == BASE:
            continue
        log(f"== pares {BASE} frente a {p}")
        score = Counter()
        for a, b in zip(res[BASE], res[p], strict=True):
            if a["response"] is None or b["response"] is None:
                continue
            w = both_orders(a["review"], a["response"], b["response"], jcache, ficha(a["hotel"]))
            score[{"A": BASE, "B": p}.get(w, "empate")] += 1
        pairs[p] = dict(score)
    return {"res": res, "pairs": pairs, "gate": gate}


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
            "saludo": sum(bool(ESTIMADO.match(it["response"])) for it in genuine),
            "saludos_v9": " · ".join(
                f"{g.rstrip(':')} {sum(it['response'].lstrip().startswith(g.rstrip(':')) for it in genuine)}"
                for g in SALUDOS
            ),
            "genuinas": len(genuine),
            "recortadas": sum(bool(it.get("recortes")) for it in genuine),
            "primera_frase_top": top,
            "primera_frase_top_n": top_n,
        }
    for p, score in pairs.items():
        s[p]["pares_vs_base"] = score
    return s


def write_report(s: dict) -> None:
    prompts = [p for p in s if not p.startswith("_")]
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
        "| Empiezan con "
        + " · ".join(g.rstrip(":") for g in SALUDOS)
        + " | "
        + " | ".join(s[p]["saludos_v9"] for p in prompts)
        + " |",
        "| Finalidad recortada tras «revisaremos» | "
        + " | ".join(f"{s[p]['recortadas']}/{s[p]['genuinas']}" for p in prompts)
        + " |",
        "| Primera frase más repetida (tras el saludo) | "
        + " | ".join(
            f"«{s[p]['primera_frase_top']}…» ({s[p]['primera_frase_top_n']})" for p in prompts
        )
        + " |",  # fmt: skip
    ]
    gate = s["_puerta_pares"]
    L += ["", f"## Por pares frente a {BASE} (juez de pares {PAIR_VERSION}: el saludo no cuenta; "
          "los dos órdenes; lo inconsistente, empate)", "",
          f"Puertas (canaries redactados por Claude). Pares: usted frente a tuteo → «{gate['usted_frente_a_tu']}» "
          f"(debe ser A, el usted); «Hola:» frente a «Estimado cliente:» con el mismo texto → "
          f"«{gate['hola_frente_a_estimado']}» (no debe ser B). Rúbrica {RUBRIC}, registro: «Hola:» "
          f"con usted {'cumple' if gate['registro_hola_cumple'] else 'NO cumple'} (debe cumplir); "
          f"tuteo {'cumple' if gate['registro_tuteo_cumple'] else 'no cumple'} (no debe cumplir). **"
          + ("Pasan" if gate["pasa"] else "NO pasan: el juez no es válido para esta comparación")
          + "**.", ""]  # fmt: skip
    for p in prompts:
        if p != BASE:
            sc = s[p]["pares_vs_base"]
            L.append(f"- {p}: gana {sc.get(p, 0)}, pierde {sc.get(BASE, 0)}, "
                     f"empata {sc.get('empate', 0)}.")  # fmt: skip
    if "v9" in s and BASE in s:
        sv, sb = s["v9"]["suspensos"], s[BASE]["suspensos"]
        safe = {k: sv[k] <= sb[k] for k in SAFETY}
        ok = gate["pasa"] and all(safe.values())
        L += ["", "## Filtro de seguridad para adoptar v9", "",
              "v9 no puede suspender más que v6 en estos criterios (el resto se informa arriba, pero "
              "decide la valoración humana a ciegas de reseñas nuevas):", ""]  # fmt: skip
        L += [f"- {NAMES[k]}: v9 {sv[k]} frente a {BASE} {sb[k]} → "
              f"{'cumple' if safe[k] else 'NO cumple'}." for k in SAFETY]  # fmt: skip
        L += ["", f"**{'Pasa' if ok else 'No pasa'}** el filtro"
              + ("." if gate["pasa"] else " (las puertas del juez no pasan).")
              + (" Siguiente paso: valoración a ciegas de las tandas, v6 frente a v9." if ok else "")]  # fmt: skip
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
    s["_puerta_pares"] = r["gate"]
    OUT.write_text(json.dumps({"resumen": s, "respuestas": {p: [
        {"id": it["id"], "response": it["response"], "decision": it["decision"],
         "reasons": it["reasons"], "judge_v2h": it.get("judge_v2h")} for it in out]
        for p, out in r["res"].items()}}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")  # fmt: skip
    write_report(s)
    log(f"Informe: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
