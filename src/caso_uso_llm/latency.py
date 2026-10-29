"""Fase 9 · Latencia por etapa del uso interactivo: ¿cuánto de cada reseña es carga de modelos?

Reproduce la demo (app.py): el clasificador se carga una vez; en cada repetición se descargan
todos los modelos de Ollama, se precargan el juez y el generador (como `app.warm_up`) y se
procesan las reseñas de la muestra una a una con `pipeline.run([reseña])`, de modo que ocurren
las recargas reales (el generador de 27B y el juez de 12B no caben juntos en la VRAM).

Sin caché de resultados (`run(no_cache=True)`): ninguna llamada al LLM lee ni escribe
results/*cache*; los embeddings de las reseñas se piden de nuevo (los de kb/ salen del disco,
como en la demo). La primera reseña de cada repetición se informa aparte.

Muestra fija y versionada (evals/latencia/muestra_v1.json): 3 reseñas que hoy se publican y 3 que
van a revisión, según results/pipeline_cola.json, elegidas con la semilla del proyecto.

Salida: results/latencia_<prompt>_<fecha>.jsonl (ids, tiempos y modelos; ningún texto) y
reports/phase9_latencia.md.

Uso: uv run just latencia                  # 3 repeticiones, prompt v6
     uv run just latencia --reps 5
     uv run just latencia --informe results/latencia_v6_20261029-2130.jsonl   # solo el informe
"""

import argparse
import json
import random
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from caso_uso_llm import timing
from caso_uso_llm.evals.judge import JUDGE_MODEL
from caso_uso_llm.evals.judge import OPTIONS as JUDGE_OPTIONS
from caso_uso_llm.generate.prompts import RAG_PROMPTS
from caso_uso_llm.generate.run import MODEL
from caso_uso_llm.generate.run import OPTIONS as GEN_OPTIONS
from caso_uso_llm.log import log
from caso_uso_llm.paths import EVALS, RESULTS, ROOT
from caso_uso_llm.pipeline import PROMPT, QUEUE, RUBRIC
from caso_uso_llm.rag.retrieve import EMBED_MODEL
from caso_uso_llm.seed import DEFAULT_SEED

SAMPLE = EVALS / "latencia" / "muestra_v1.json"
GEN_CTX, JUDGE_CTX = GEN_OPTIONS["num_ctx"], JUDGE_OPTIONS["num_ctx"]
REPORT = ROOT / "reports" / "phase9_latencia.md"
PUB, REV = "publicable", "revisión humana"
STAGES = ("normalizacion", "clasificador", "embeddings", "carga_generador", "analisis",
          "respuesta", "checks", "carga_juez", "juez", "enrutado")  # fmt: skip
# Estratos de la muestra: (decisión en la cola, grupo, filtro). Uno de cada, intercalados.
STRATA = (
    (PUB, "sintético", lambda it: True),  # el único sintético que se publica
    (REV, "sintético", lambda it: it["hotel"] is not None),
    (PUB, "AHR", lambda it: it["meta"]["rating"] == 4),
    (REV, "AHR", lambda it: it["meta"]["rating"] == 1),
    (PUB, "AHR", lambda it: it["meta"]["rating"] == 5),
    (REV, "AHR", lambda it: it["meta"]["rating"] == 3),
)


def build_sample(seed: int = DEFAULT_SEED) -> list[dict]:
    """6 reseñas de la cola de la demostración: 3 publicables y 3 a revisión, intercaladas."""
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    rng = random.Random(seed)
    sample = []
    for decision, group, keep in STRATA:
        pool = [it for it in queue if it["decision"] == decision
                and it["meta"]["grupo"] == group and keep(it)]  # fmt: skip
        it = rng.choice(sorted(pool, key=lambda x: x["id"]))
        sample.append({"id": it["id"], "hotel": it["hotel"], "title": it.get("title", ""),
                       "text": it["text"], "meta": it["meta"], "decision_cola": decision})  # fmt: skip
    return sample


def load_sample() -> list[dict]:
    if not SAMPLE.exists():
        SAMPLE.parent.mkdir(parents=True, exist_ok=True)
        doc = {"descripcion": "Muestra fija de la medición de latencia (latency.build_sample, "
               f"semilla {DEFAULT_SEED}, a partir de {QUEUE.relative_to(ROOT).as_posix()}).",
               "items": build_sample()}  # fmt: skip
        text = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
        SAMPLE.write_text(text, encoding="utf-8", newline="\n")
    return json.loads(SAMPLE.read_text(encoding="utf-8"))["items"]


def loaded_models() -> list[str]:
    """Modelos en VRAM con su contexto: si cambia el contexto, Ollama recarga el modelo."""
    import ollama

    return sorted(f"{m.model} (ctx {m.context_length})" for m in ollama.ps().models)


def unload_all() -> None:
    """Descarga todos los modelos de Ollama y espera a que la VRAM quede libre."""
    import ollama

    for m in (x.split(" (")[0] for x in loaded_models()):
        if m.startswith(EMBED_MODEL):
            ollama.embed(model=m, input=[], keep_alive=0)
        else:
            ollama.generate(model=m, prompt="", keep_alive=0)
    for _ in range(60):
        if not loaded_models():
            return
        time.sleep(0.5)
    raise RuntimeError(f"Ollama no ha descargado los modelos: {loaded_models()}")


def ollama_version() -> str:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=5) as r:
            return json.load(r)["version"]
    except OSError:
        return "desconocida"


def measure(reps: int, prompt: str) -> Path:
    from caso_uso_llm.classify.infer import SentimentEnsemble
    from caso_uso_llm.ollama_gpu import require_gpu
    from caso_uso_llm.pipeline import run

    sample = load_sample()
    path = RESULTS / f"latencia_{prompt}_{datetime.now():%Y%m%d-%H%M}.jsonl"
    meta = {"id": "_meta", "fecha": datetime.now().isoformat(timespec="seconds"),
            "ollama": ollama_version(), "generador": MODEL, "juez": JUDGE_MODEL,
            "embeddings": EMBED_MODEL, "prompt": prompt, "rubrica": RUBRIC, "reps": reps,
            "muestra": SAMPLE.relative_to(ROOT).as_posix()}  # fmt: skip
    path.write_text(json.dumps(meta, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    timing.enable(path, after_stage=loaded_models)
    log(f"Latencia: {len(sample)} reseñas × {reps} repeticiones, prompt {prompt} → {path.name}")

    timing.begin("_arranque_clasificador")
    with timing.stage("carga_clasificador"):
        classifier = SentimentEnsemble()
    timing.end()
    for rep in range(reps):
        unload_all()
        timing.begin("_warm_up", rep=rep)
        for model, ctx, name in ((JUDGE_MODEL, JUDGE_CTX, "warm_up_juez"),
                                 (MODEL, GEN_CTX, "warm_up_generador")):  # fmt: skip
            with timing.stage(name):
                require_gpu(model, ctx)
        timing.end()
        for pos, item in enumerate(sample):
            timing.begin(item["id"], rep=rep, posicion=pos, grupo=item["meta"]["grupo"],
                         decision_cola=item["decision_cola"])  # fmt: skip
            t0 = time.perf_counter()
            it = run([{k: item[k] for k in ("id", "hotel", "title", "text", "meta")}],
                     classifier, prompt, no_cache=True)[0]  # fmt: skip
            rec = timing.end(total_s=time.perf_counter() - t0, decision=it["decision"],
                             sentimiento=it["sentiment"])  # fmt: skip
            log(f"rep {rep + 1}/{reps} · {pos + 1}/{len(sample)} {item['id']}: "
                f"{rec['total_s']:.1f} s · {it['decision']}")  # fmt: skip
    timing.enable(None)
    return path


# --- Informe --------------------------------------------------------------------------------


def _q(xs, p) -> float:
    return float(np.percentile(xs, p)) if xs else float("nan")


def _fmt(xs) -> str:
    return f"{_q(xs, 50):.1f} / {_q(xs, 90):.1f}" if xs else "—"


PRELOAD = {"carga_generador": "generador", "carga_juez": "juez"}  # etapa -> clave de meta
MIN_LOAD = 0.5  # s; por debajo, el modelo ya estaba cargado


def loads(rec: dict, meta: dict) -> list[tuple[str, str, float]]:
    """Cargas de modelo de una reseña: (etapa, modelo, segundos).

    La precarga de `require_gpu` (generate con el prompt vacío) no devuelve métricas: Ollama
    responde con todo a cero aunque cargue el modelo. Esas etapas solo cargan, así que su tiempo
    de pared es tiempo de carga.
    """
    out = [(c["etapa"], c["modelo"], c["load"]) for c in rec["llamadas"]
           if not c["cached"] and c["load"] > MIN_LOAD]  # fmt: skip
    out += [(e["etapa"], meta[PRELOAD[e["etapa"]]], e["s"]) for e in rec["etapas"]
            if e["etapa"] in PRELOAD and e["s"] > MIN_LOAD]  # fmt: skip
    return out


def split_review(rec: dict, meta: dict) -> dict:
    """Tiempo de una reseña: carga de modelos, inferencia en Ollama y resto (CPU, Python, HTTP)."""
    load = sum(s for _, _, s in loads(rec, meta))
    infer = sum(c["prompt_eval"] + c["eval"] for c in rec["llamadas"] if not c["cached"])
    return {"total": rec["total_s"], "carga": load, "inferencia": infer,
            "resto": rec["total_s"] - load - infer}  # fmt: skip


def write_report(path: Path) -> None:
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    meta = next(r for r in rows if r["id"] == "_meta")
    reviews = [r for r in rows if not r["id"].startswith("_")]
    warm = [r for r in rows if r["id"] == "_warm_up"]
    clf = next((r for r in rows if r["id"] == "_arranque_clasificador"), None)
    cached = sum(c["cached"] for r in reviews for c in r["llamadas"])
    first = [r for r in reviews if r["posicion"] == 0]
    rest = [r for r in reviews if r["posicion"] > 0]
    n_items = len({r["id"] for r in reviews})

    L = [
        "# Fase 9 · Latencia por etapa (uso interactivo)",
        "",
        f"Generado por `uv run just latencia` a partir de `{path.relative_to(ROOT).as_posix()}`. "
        "No editar a mano.",
        "",
        f"- Fecha: {meta['fecha']} · Ollama {meta['ollama']}",
        f"- Generador `{meta['generador']}` (prompt {meta['prompt']}) · juez `{meta['juez']}` "
        f"(rúbrica {meta['rubrica']}) · embeddings `{meta['embeddings']}` · clasificador mRoBERTa "
        "(3 semillas, CPU)",
        f"- Muestra: `{meta['muestra']}`, {n_items} reseñas × {meta['reps']} repeticiones = "
        f"{len(reviews)} medidas. Cada repetición descarga todos los modelos, precarga juez y "
        "generador (como la app) y procesa las reseñas una a una.",
        f"- Sin caché de resultados: {cached} llamadas al LLM salieron de la caché "
        + ("(correcto: todas se midieron)." if cached == 0 else "(**la medición no es válida**)."),
        "",
        "Cifras: **mediana / p90 en segundos**. Con tan pocas medidas el p90 es casi el máximo.",
        "",
        "## ¿Cuánto es carga y cuánto inferencia?",
        "",
        "Carga = `load_duration` de las llamadas a Ollama más el tiempo de pared de la precarga "
        "de `require_gpu` (un generate con el prompt vacío que carga el modelo pero devuelve "
        "las métricas a cero). Inferencia = "
        "`prompt_eval_duration` + `eval_duration`. Resto = clasificador en CPU, normalización, "
        "comprobaciones y comunicación con Ollama.",
        "",
        "| Reseñas | n | Total | Carga | Inferencia | Resto | % carga (suma) |",
        "|---|---|---|---|---|---|---|",
    ]
    groups = (("Primera de cada repetición", first), ("Resto", rest),
              *((f"Resto · destino {d}", [r for r in rest if r["decision"] == d]) for d in (PUB, REV)))  # fmt: skip
    for label, recs in groups:
        parts = [split_review(r, meta) for r in recs]
        col = {k: [p[k] for p in parts] for k in ("total", "carga", "inferencia", "resto")}
        share = sum(col["carga"]) / sum(col["total"]) if parts else float("nan")
        L.append(f"| {label} | {len(recs)} | {_fmt(col['total'])} | {_fmt(col['carga'])} | "
                 f"{_fmt(col['inferencia'])} | {_fmt(col['resto'])} | {share:.0%} |")  # fmt: skip

    L += ["", "## Tiempo de pared por etapa", "",
          "| Etapa | Primera reseña | Resto | Carga en la etapa (resto) | Modelos en VRAM al acabar |",
          "|---|---|---|---|---|"]  # fmt: skip
    for st in STAGES:
        wall = lambda recs, st=st: [e["s"] for r in recs for e in r["etapas"] if e["etapa"] == st]  # noqa: E731
        load = [sum(x for e, _, x in loads(r, meta) if e == st) for r in rest]
        after = Counter(", ".join(e.get("despues", [])) or "ninguno"
                        for r in rest for e in r["etapas"] if e["etapa"] == st)  # fmt: skip
        vram = after.most_common(1)[0][0] if after else "—"
        L.append(f"| {st} | {_fmt(wall(first))} | {_fmt(wall(rest))} | {_fmt(load)} | {vram} |")

    L += ["", "## Cargas de modelo por reseña (resto)", "",
          "| Modelo | Cargas por reseña (mediana) | De ellas, en la precarga de `require_gpu` | "
          "Tiempo por carga (mediana / p90) |",
          "|---|---|---|---|"]  # fmt: skip
    per_model, counts, pre = defaultdict(list), defaultdict(list), defaultdict(list)
    models = (meta["generador"], meta["juez"], meta["embeddings"])
    for r in rest:
        found = loads(r, meta)
        for _, m, x in found:
            per_model[m].append(x)
        for m in models:
            counts[m].append(sum(fm == m for _, fm, _ in found))
            pre[m].append(sum(fm == m and e in PRELOAD for e, fm, _ in found))
    for m in models:
        L.append(
            f"| `{m}` | {_q(counts[m], 50):.0f} | {_q(pre[m], 50):.0f} | {_fmt(per_model[m])} |"
        )

    tokens = defaultdict(list)
    for r in rest:
        for c in r["llamadas"]:
            if not c["cached"] and c["tipo"] == "chat":
                tokens[c["etapa"]].append((c["prompt_eval_count"], c["eval_count"],
                                           c["prompt_eval"], c["eval"]))  # fmt: skip
    L += ["", "## Inferencia por llamada (resto)", "",
          "| Etapa | Tokens de entrada | Tokens generados | prompt_eval (s) | eval (s) |",
          "|---|---|---|---|---|"]  # fmt: skip
    for st, ts in tokens.items():
        cols = list(zip(*ts, strict=True))
        L.append(f"| {st} | {_q(cols[0], 50):.0f} | {_q(cols[1], 50):.0f} | {_fmt(cols[2])} | "
                 f"{_fmt(cols[3])} |")  # fmt: skip

    L += ["", "## Arranque (una vez por sesión de la app)", ""]
    if clf:
        L.append(f"- Carga del clasificador (3 × mRoBERTa en CPU): {clf['etapas'][0]['s']:.1f} s.")
    for name in ("warm_up_juez", "warm_up_generador"):
        xs = [e["s"] for r in warm for e in r["etapas"] if e["etapa"] == name]
        L.append(f"- `{name}` (con los modelos descargados): {_fmt(xs)} s (n = {len(xs)}).")

    changed = sorted({(r["id"], r["decision_cola"], r["decision"]) for r in reviews
                      if r["decision"] != r["decision_cola"]})  # fmt: skip
    L += ["", "## Destino observado frente a la cola cacheada", ""]
    if changed:
        L.append(
            "Sin caché, estas reseñas acabaron con otro destino que en "
            "`results/pipeline_cola.json` (las tablas usan el destino observado):"
        )
        L += [f"- `{i}`: cola «{a}» → medido «{b}»" for i, a, b in changed]
    else:
        L.append("Todas las reseñas acabaron con el mismo destino que en la cola cacheada.")

    L += ["", "## Todas las mediciones (results/latencia_*.jsonl)", "",
          "Reseñas sin contar la primera de cada repetición. Cargas del generador por reseña: 2 "
          "indica la doble carga (precarga con otro contexto y recarga en el análisis).", "",
          "| Fichero | Fecha | Ollama | Prompt | n | Total | Carga | % carga | Cargas del generador |",
          "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for f in sorted(RESULTS.glob("latencia_*.jsonl")):
        rs = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x]
        m = next(r for r in rs if r["id"] == "_meta")
        rr = [r for r in rs if not r["id"].startswith("_") and r["posicion"] > 0]
        parts = [split_review(r, m) for r in rr]
        tot, car = [x["total"] for x in parts], [x["carga"] for x in parts]
        gen = [sum(fm == m["generador"] for _, fm, _ in loads(r, m)) for r in rr]
        share = sum(car) / sum(tot) if tot else float("nan")
        L.append(f"| `{f.name}` | {m['fecha'][:16]} | {m['ollama']} | {m['prompt']} | {len(rr)} | "
                 f"{_q(tot, 50):.1f} | {_q(car, 50):.1f} | {share:.0%} | {_q(gen, 50):.0f} |")  # fmt: skip

    L += ["", "## Limitaciones", "",
          f"- Muestra pequeña ({n_items} reseñas, {len(rest)} medidas sin contar la primera de cada "
          "repetición): las cifras sirven para ver el orden de magnitud de carga frente a "
          "inferencia, no para afinar milisegundos.",
          "- Caché de páginas del sistema: con 32 GB de RAM, los ficheros de los modelos quedan en "
          "memoria tras la primera carga, así que las recargas miden RAM → VRAM, no disco. Es lo "
          "que ocurre en la demo; un arranque desde disco solo se mediría tras reiniciar.",
          "- La caché de prefijos de Ollama sigue activa (como en la demo): los prompts de sistema "
          "repetidos pueden evaluarse más rápido cuando el modelo sigue cargado.",
          "- Se mide `pipeline.run`; la interfaz de Gradio añade su propio tiempo (pequeño).",
          f"- Las cifras dependen de la versión de Ollama ({meta['ollama']}) y de su llama.cpp."]  # fmt: skip
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    log(f"Informe: {REPORT.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--prompt", default=PROMPT, choices=RAG_PROMPTS)
    ap.add_argument("--informe", help="solo regenera el informe a partir de este JSONL")
    args = ap.parse_args()
    path = ROOT / args.informe if args.informe else measure(args.reps, args.prompt)
    write_report(path)


if __name__ == "__main__":
    main()
