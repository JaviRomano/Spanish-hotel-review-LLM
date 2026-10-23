"""¿Sirve un generador pequeño para una demo en un servidor modesto? 27B frente a un modelo menor.

Mismo prompt (v6), mismo RAG y mismos 54 casos que la Fase 5; el modelo pequeño hace también el
análisis de aspectos, porque en el servidor no habría 27B. Se juzga con el juez ya validado
(Gemma 12B, rúbrica v2g con ficha), repitiendo antes su puerta de canaries, y se compara por
criterio y por pares (en los dos órdenes) contra las respuestas v6 del 27B.

Criterio de aceptación (fijado ANTES de ver resultados):
- JSON de aspectos válido en todos los casos;
- puerta del juez válida;
- no más suspensos que el 27B en «no admite culpa», «no promete» y «no confirma ni niega»;
- no perder claramente por pares (el 27B no gana más de la mitad de los pares consistentes).

Uso: uv run just modelo-pequeno [--model qwen3.5:9b]
"""

import argparse
import json
import statistics
import time

import ollama

from caso_uso_llm.evals.judge import JUDGE_MODEL, compare, judge
from caso_uso_llm.evals.rubric import IDS
from caso_uso_llm.generate import checks as C
from caso_uso_llm.generate.prompts import RESPONSE_PROMPTS
from caso_uso_llm.generate.run import CACHE, MODEL, Cache, analyze, respond
from caso_uso_llm.log import log
from caso_uso_llm.ollama_gpu import require_gpu
from caso_uso_llm.paths import RESULTS, ROOT
from caso_uso_llm.rag.generate_rag import cases, context_user, ficha_checks, retrieve_all
from caso_uso_llm.rag.generate_rag import results_path as rag_results
from caso_uso_llm.rag.judge_rag import CACHE as JUDGE_CACHE
from caso_uso_llm.rag.judge_rag import NAMES, RUBRIC, failed, ficha, gate
from caso_uso_llm.seed import DEFAULT_SEED

PROMPT = "v6"
SAFETY = ("sin_culpa", "sin_promesa", "sin_premisa")
GROUPS = (("real", "reales"), ("adversarial", "adversariales"), ("rag", "ficha vs. cliente"))


def slug(model: str) -> str:
    return model.replace(":", "-").replace("/", "-")


def out_path(model: str):
    return RESULTS / f"phase9_{slug(model)}.json"


def report_path(model: str):
    return ROOT / "reports" / f"phase9_{slug(model)}.md"


def vram(model: str) -> dict:
    for m in ollama.ps().models:
        if m.model == model or m.name == model:
            return {"size_gb": round(m.size / 1e9, 1), "vram_gb": round(m.size_vram / 1e9, 1)}
    return {}


def generate(model: str, seed: int) -> dict:
    df = cases(seed)
    context = retrieve_all(df)
    require_gpu(model)
    cache = Cache(CACHE)
    rows = []
    for i, row in df.iterrows():
        hotel = row["hotel"] if isinstance(row["hotel"], str) else None
        t0 = time.perf_counter()
        analysis, error = analyze(row["review"], cache, model)
        t_analysis = time.perf_counter() - t0
        r = {"id": row["id"], "kind": row["kind"], "hotel": hotel, "review": row["review"]}
        if analysis is None:
            rows.append({**r, "analysis_valid": False, "analysis_error": error})
            log(f"   [{i + 1}/{len(df)}] {row['id']}: análisis inválido")
            continue
        pols, exs = context[row["id"]]
        t0 = time.perf_counter()
        text = respond(RESPONSE_PROMPTS[PROMPT],
                       context_user(row["review"], analysis, hotel, pols, exs), cache, model)  # fmt: skip
        t_response = time.perf_counter() - t0
        checks = C.run_checks(text, analysis["aspectos"], list(row["must_not"]))
        checks.update(ficha_checks(text, row["review"], hotel))
        rows.append({**r, "analysis_valid": True, "response": text, "checks": checks,
                     "t_analysis": t_analysis, "t_response": t_response})  # fmt: skip
        log(f"   [{i + 1}/{len(df)}] {row['id']}: {t_analysis + t_response:.1f} s")
    return {"model": model, "vram": vram(model), "rows": rows}


def evaluate(small: dict) -> dict:
    require_gpu(JUDGE_MODEL)
    jcache = Cache(JUDGE_CACHE)
    g = gate(jcache)
    big = {r["id"]: r for r in json.loads(rag_results(PROMPT).read_text(encoding="utf-8"))}
    for r in small["rows"]:
        if not r["analysis_valid"]:
            continue
        f, b = ficha(r["hotel"]), big[r["id"]][PROMPT]["response"]
        r["verdict_small"] = judge(r["review"], r["response"], jcache, RUBRIC, f)
        r["verdict_big"] = judge(r["review"], b, jcache, RUBRIC, f)
        ab = compare(r["review"], b, r["response"], jcache, f)  # A = 27B
        ba = compare(r["review"], r["response"], b, jcache, f)  # A = pequeño
        first, second = (
            {"A": "27B", "B": "pequeño"}.get(ab, "empate"),
            {"A": "pequeño", "B": "27B"}.get(ba, "empate"),
        )
        r["pair"] = first if first == second else "empate"
        r["pair_consistent"] = first == second
    return g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3.5:9b")
    model = ap.parse_args().model
    log(f"Generador {model} frente a {MODEL} · prompt {PROMPT} · juez {JUDGE_MODEL} ({RUBRIC})")
    small = generate(model, DEFAULT_SEED)
    g = evaluate(small)
    small["gate"] = g
    out_path(model).write_text(
        json.dumps(small, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )
    write_report(small)
    log(f"OK: {out_path(model).relative_to(ROOT)} y {report_path(model).relative_to(ROOT)}")


def write_report(small: dict) -> None:
    model, rows = small["model"], small["rows"]
    ok = [r for r in rows if r["analysis_valid"]]
    times = [r["t_analysis"] + r["t_response"] for r in ok]
    fails = {
        k: {who: sum(k in failed(r[f"verdict_{who}"]) for r in ok) for who in ("big", "small")}
        for k in IDS
    }
    consistent = [r for r in ok if r["pair_consistent"]]
    big_wins = sum(r["pair"] == "27B" for r in ok)
    small_wins = sum(r["pair"] == "pequeño" for r in ok)
    accept = {
        "JSON de aspectos válido en todos los casos": len(ok) == len(rows),
        "Puerta del juez válida": small["gate"]["valid"],
        "No más suspensos de seguridad que el 27B": all(
            fails[k]["small"] <= fails[k]["big"] for k in SAFETY
        ),
        "El 27B no gana más de la mitad de los pares consistentes": big_wins <= len(consistent) / 2,
    }
    L = [
        f"# ¿Generador pequeño para la demo? `{MODEL}` frente a `{model}`",
        "",
        f"Generado por `uv run just modelo-pequeno --model {model}` · prompt {PROMPT} con RAG, mismos 54 "
        f"casos que la Fase 5 · juez `{JUDGE_MODEL}` con rúbrica {RUBRIC} y ficha. El modelo pequeño "
        "hace también el análisis de aspectos. No editar a mano.",
        "",
        "## Veredicto",
        "",
        f"**{'APTO' if all(accept.values()) else 'NO APTO'} para la demo** según los criterios "
        "fijados antes de ver los resultados:",
        "",
        *[f"- {'✅' if v else '❌'} {k}" for k, v in accept.items()],
        "",
        "## Coste",
        "",
        f"- Memoria en Ollama: {small['vram'].get('size_gb', '?')} GB "
        f"({small['vram'].get('vram_gb', '?')} GB en VRAM).",
        f"- Tiempo por reseña (análisis + respuesta, RX 7900 XTX, modelo ya cargado): mediana "
        f"{statistics.median(times):.1f} s, máximo {max(times):.1f} s. En una GPU de servidor pequeña "
        "(T4, L4) será más lento.",
        "",
        "## Calidad frente al 27B",
        "",
        f"Análisis JSON válido: {len(ok)}/{len(rows)}.",
        "",
        "| Grupo | Cumplen todos los criterios: 27B | pequeño |",
        "|---|---|---|",
    ]
    for kind, label in GROUPS:
        g = [r for r in ok if r["kind"] == kind]
        L.append(f"| {label} | {sum(not failed(r['verdict_big']) for r in g)}/{len(g)} | "
                 f"{sum(not failed(r['verdict_small']) for r in g)}/{len(g)} |")  # fmt: skip
    L += ["", "| Criterio | Suspensos 27B | Suspensos pequeño |", "|---|---|---|"]
    L += [f"| {NAMES[k]} | {fails[k]['big']} | {fails[k]['small']} |" for k in IDS]
    L += ["", f"Por pares, en los dos órdenes: consistentes {len(consistent)}/{len(ok)} · gana el 27B "
          f"{big_wins} · gana el pequeño {small_wins} · empate {len(ok) - big_wins - small_wins}.", ""]  # fmt: skip
    alerts = [(r["id"], k) for r in ok for k in ("promise", "liability", "tuteo", "dialect", "plazo")
              if r["checks"].get(k)] + [(r["id"], "importe") for r in ok if r["checks"].get("importe")]  # fmt: skip
    L += [
        f"Comprobaciones deterministas que saltan con el pequeño: {len(alerts)}"
        + (f" ({', '.join(f'{i}: {k}' for i, k in alerts)})" if alerts else "")
        + ".",
        "",
    ]
    L += ["## Suspensos del juez con el modelo pequeño", ""]
    for r in ok:
        for k in failed(r["verdict_small"]):
            L.append(f"- `{r['id']}` · {NAMES[k]}: «{r['verdict_small'][k]['evidencia'][:160]}»")
    L += ["", "## Respuestas del modelo pequeño en los casos adversariales", ""]
    for r in [r for r in ok if r["kind"] != "real"]:
        L += [
            f"**`{r['id']}`** (hotel {r['hotel']})",
            "",
            f"> {r['review']}",
            "",
            r["response"],
            "",
        ]
    report_path(model).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
