"""Pipeline completo (pasos [1]–[7] de la arquitectura) y cola de revisión humana.

reseña + hotel → [1] normalización y PII → [2] sentimiento y confianza (mRoBERTa, CPU)
→ [3] aspectos en JSON → [4] RAG (ficha por id, políticas, respuestas aprobadas)
→ [5] respuesta (prompt v6) → [6] guardarraíles (comprobaciones deterministas + juez v2g con ficha)
→ [7] «publicable» o «revisión humana», con los motivos.

Va a revisión humana si se cumple CUALQUIERA de estas condiciones:
- el clasificador y el LLM (campo `sentimiento` del análisis) no coinciden: el clasificador no
  entiende el sarcasmo (p06 de las reseñas propias: positivo con 0,93 y el LLM, negativo);
- la respuesta usa el nombre de una persona de la reseña (sin NER todavía, ver checks.py);
- la reseña es negativa o neutral (REVIEW_LABELS), o la confianza del clasificador es menor que
  el umbral elegido en validación (0,85; results/phase3b_realista.json). Las neutrales van siempre
  a revisión desde la primera demostración: las tres que se publicaban rozaban el umbral (0,851)
  y el neutral es la clase más débil del clasificador (F1 0,549 en AHR, Fase 3);
- el cliente pide algo (reembolso, compensación, respuesta…): solo una persona puede decidir;
- el análisis no es un JSON válido;
- salta alguna comprobación determinista (promesa, culpa expresa, tuteo, plazo, importe, dato
  fuera de la ficha, contradice al cliente, nombra la ficha, longitud o firma);
- el juez suspende algún criterio.

Se ejecuta por etapas (clasificar todo, recuperar todo, generar todo, juzgar todo) porque el
generador de 27B y el juez de 12B no caben juntos en la VRAM con contexto: alternarlos por
reseña obligaría a recargarlos cada vez.

Uso: uv run just pipeline                         # demostración: casos sintéticos + 40 del AHR
     uv run just pipeline --csv entrada.csv       # columnas: id, hotel (opcional), title, text
     uv run just pipeline --csv terceros.csv --vivo --out data/live/x.json  # reseñas de terceros
     uv run just pipeline --jsonl data/live/resenas_recogidas.jsonl          # siempre en data/live
"""

import argparse
import json
from collections import Counter
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from caso_uso_llm import timing
from caso_uso_llm.classify.datasets import load_ahr_ood
from caso_uso_llm.evals.judge import JUDGE_MODEL, judge
from caso_uso_llm.evals.judge import OPTIONS as JUDGE_OPTIONS
from caso_uso_llm.evals.rubric import IDS, criterios
from caso_uso_llm.generate import checks as C
from caso_uso_llm.generate.prompts import RAG_PROMPTS
from caso_uso_llm.generate.run import CACHE, MODEL, Cache, NoCache, analyze
from caso_uso_llm.generate.run import OPTIONS as GEN_OPTIONS
from caso_uso_llm.log import log
from caso_uso_llm.ollama_gpu import require_gpu
from caso_uso_llm.paths import DATA_LIVE, EVALS, RESULTS, ROOT
from caso_uso_llm.rag import kb
from caso_uso_llm.rag.generate_rag import (
    K_EXAMPLES,
    K_POLICIES,
    RAG_CASES,
    ficha_checks,
    generate_reply,
)
from caso_uso_llm.rag.retrieve import Embedder, Retriever
from caso_uso_llm.seed import DEFAULT_SEED
from caso_uso_llm.spec import GENUINIDAD_V2

if TYPE_CHECKING:  # torch solo hace falta al clasificar, no para enrutar (CI sin torch)
    from caso_uso_llm.classify.infer import SentimentEnsemble

PROMPT = "v6"
RUBRIC = "v2g"
JUDGE_CACHE = RESULTS / "phase6_judge_cache.jsonl"
THRESHOLD = json.loads((RESULTS / "phase3b_realista.json").read_text(encoding="utf-8"))["coverage"][
    "solo_confianza"
]["threshold"]
QUEUE = RESULTS / "pipeline_cola.json"
# Reseñas de terceros (demo en vivo, recogidas): su caché y su salida van fuera de git, como su
# texto. El consentimiento cubre guardarlas para evaluar el sistema, no publicarlas en el repo, y
# la caché guarda citas literales de la reseña (análisis) y las respuestas.
LIVE_CACHE = DATA_LIVE / "cache_generador.jsonl"
LIVE_JUDGE_CACHE = DATA_LIVE / "cache_juez.jsonl"
LIVE_QUEUE = DATA_LIVE / "pipeline_vivo.json"
REPORT = ROOT / "reports" / "phase5_pipeline.md"
AHR_PER_RATING = 8
PUBLISH, REVIEW, PENDING = "publicable", "revisión humana", "pendiente de juez"
REVIEW_LABELS = ("negativo", "neutral")  # sentimientos que nunca se publican sin revisión

# Comprobaciones deterministas que mandan la respuesta a revisión (nombre legible -> función).
ALERTS = {
    # Primero: es el motivo de fondo cuando aparece (p08: no basta con «reseña negativa»)
    "accidente o riesgo legal": lambda c: bool(c.get("incidente")),
    "promesa (regla)": lambda c: c["promise"],
    "culpa expresa (regla)": lambda c: c["liability"],
    "tuteo o dialecto": lambda c: c["tuteo"] or c["dialect"],
    "plazo o acción dada por hecha": lambda c: c["plazo"],
    "servicio que la ficha dice que no existe": lambda c: bool(c["servicio_inexistente"]),
    "precio u horario fuera de la ficha": lambda c: bool(c["cifra_inventada"]),
    "contradice al cliente": lambda c: c["contradice"],
    "da un importe": lambda c: bool(c["importe"]),
    "nombra la ficha o las políticas": lambda c: c["nombra_fuente"],
    "longitud o firma": lambda c: not (c["length_ok"] and c["signature_ok"]),
    "nombre de una persona en la respuesta": lambda c: bool(c.get("nombres")),
    "habla de una estancia que no hubo": lambda c: c.get("estancia_inexistente", False),
    "menciona un problema de higiene u olor": lambda c: bool(c.get("higiene")),
    "copia 4+ palabras de la reseña": lambda c: bool(c.get("copia_literal")),
}
NAMES = {c.id: c.nombre for c in criterios(RUBRIC)}


def ficha(hotel: str | None) -> str:
    return kb.ficha_texto(hotel) if hotel else "No disponible."


def caches(live: bool) -> tuple:
    """Rutas de la caché del generador y del juez: las versionadas o las de terceros."""
    return (LIVE_CACHE, LIVE_JUDGE_CACHE) if live else (CACHE, JUDGE_CACHE)


def run(
    items: list[dict],
    classifier: "SentimentEnsemble | None" = None,
    prompt: str = PROMPT,
    live: bool = False,
    no_cache: bool = False,
) -> list[dict]:
    """Pipeline completo: generate_stage + judge_stage (ver sus docstrings)."""
    out = generate_stage(items, classifier, prompt, live, no_cache)
    return judge_stage(out, live, no_cache)


def generate_stage(
    items: list[dict],
    classifier: "SentimentEnsemble | None" = None,
    prompt: str = PROMPT,
    live: bool = False,
    no_cache: bool = False,
) -> list[dict]:
    """Pasos [1]–[5] y comprobaciones deterministas. Ninguna reseña sale de aquí publicable: las
    que tienen respuesta quedan en PENDING hasta que judge_stage añade el veredicto.

    items: dicts con id, text y opcionalmente title, hotel y meta (se copia tal cual).

    `classifier`: ensamble ya cargado (la app lo carga una vez; tarda ~25 s).
    `live`: reseñas de terceros; las llamadas al LLM se cachean en data/live (fuera de git).
    `no_cache`: medir latencia; ninguna llamada al LLM lee ni escribe la caché de resultados y
    los embeddings de estas reseñas se piden de nuevo a Ollama (los de kb/ salen del disco,
    como en la demo). Cada paso se mide con timing.stage si la medición está activada.
    """
    gen_cache, _ = caches(live)
    if live:
        DATA_LIVE.mkdir(parents=True, exist_ok=True)
    log(f"{len(items)} reseñas · umbral de confianza {THRESHOLD} · prompt {prompt} · juez {RUBRIC}")
    out = [{**it, "hotel": it.get("hotel") or None, "reasons": []} for it in items]

    log("[2] Sentimiento (mRoBERTa, 3 semillas, CPU)")
    from caso_uso_llm.classify.infer import SentimentEnsemble, prepare

    with timing.stage("normalizacion"):
        texts = [prepare(it["text"], it.get("title", "")) for it in out]
    with timing.stage("clasificador"):
        classifier = classifier or SentimentEnsemble()
        preds = classifier.predict(texts)
    for it, text, p in zip(out, texts, preds, strict=True):
        it.update(review=text, sentiment=p.label, confidence=p.confidence, probs=p.probs)

    log("[4] Recuperación (políticas híbrida, ejemplos densa)")
    with timing.stage("embeddings"):
        embedder = Embedder(keep_alive=0, persist=not no_cache)
        if no_cache:
            embedder.forget(texts)
        pols, exs = Retriever(kb.politicas(), embedder), Retriever(kb.respuestas(), embedder)
        ctx = {it["id"]: (pols.search(it["review"], K_POLICIES, "hibrida"),
                          exs.search(it["review"], K_EXAMPLES, "densa")) for it in out}  # fmt: skip

    log(f"[3][5] Aspectos y respuesta ({MODEL})")
    with timing.stage("carga_generador"):
        require_gpu(MODEL, GEN_OPTIONS["num_ctx"])
    cache = NoCache() if no_cache else Cache(gen_cache)
    for i, it in enumerate(out, 1):
        with timing.stage("analisis"):
            analysis, error = analyze(it["review"], cache)
        if analysis is None:
            it.update(analysis=None, response=None, reasons=["análisis inválido"])
            continue
        p, e = ctx[it["id"]]
        with timing.stage("respuesta"):
            # Antitrampa (detector v2) con cualquier prompt, también el base (v6): una trampa va
            # siempre a revisión. Fecha de referencia: la de recepción de la reseña, si la hay.
            today = date.fromisoformat(it["fecha_ref"]) if it.get("fecha_ref") else None
            gen = generate_reply(prompt, it["review"], analysis, it["hotel"], p, e, cache,
                                 detect_traps=True, trap_system=GENUINIDAD_V2, today=today)  # fmt: skip
        response = gen["response"]
        it["genuina"], it["motivo_trampa"] = gen["genuina"], gen.get("motivo_trampa", "")
        it["recortes"] = gen.get("recortes", [])  # v9: finalidad recortada tras «revisaremos»
        with timing.stage("checks"):
            checks = C.run_checks(response, analysis["aspectos"])
            checks.update(ficha_checks(response, it["review"], it["hotel"]))
            checks["nombres"] = C.person_names(response, it["review"])
            checks["incidente"] = C.incident_terms(it["review"])
        it.update(analysis=analysis, response=response, checks=checks,
                  politicas=[d.id for d in p], ejemplos=[d.id for d in e])  # fmt: skip
        if i % 10 == 0:
            log(f"   {i}/{len(out)}")
    for it in out:
        it["decision"] = destination(it)
    return out


def judge_stage(out: list[dict], live: bool = False, no_cache: bool = False) -> list[dict]:
    """Pasos [6]–[7]: veredicto del juez y enrutado final de la salida de generate_stage."""
    _, judge_cache = caches(live)
    log(f"[6] Juez {JUDGE_MODEL} (rúbrica {RUBRIC}, con ficha)")
    with timing.stage("carga_juez"):
        require_gpu(JUDGE_MODEL, JUDGE_OPTIONS["num_ctx"])
    jcache = NoCache() if no_cache else Cache(judge_cache)
    with timing.stage("juez"):
        for it in out:
            if it["response"] is not None:
                v = judge(it["review"], it["response"], jcache, RUBRIC, ficha(it["hotel"]))
                it["judge"] = {k: v[k] for k in IDS}

    log("[7] Enrutado")
    with timing.stage("enrutado"):
        for it in out:
            it["reasons"] += route(it)
            it["decision"] = REVIEW if it["reasons"] else PUBLISH
    return out


def pre_judge_reasons(it: dict) -> list[str]:
    """Motivos de revisión que se conocen antes del juez."""
    if it["response"] is None:
        return []
    if it.get("genuina") is False:  # reseña trampa: respuesta irónica, nunca sin revisión
        return [f"posible reseña trampa ({it.get('motivo_trampa', '')})"]
    r = []
    if it["sentiment"] in REVIEW_LABELS:
        r.append({"negativo": "reseña negativa", "neutral": "reseña neutral"}[it["sentiment"]])
    if it["confidence"] < THRESHOLD:
        r.append(f"confianza {it['confidence']:.3f} < {THRESHOLD}")
    llm = it["analysis"].get("sentimiento")
    if (
        llm and llm != it["sentiment"]
    ):  # segunda opinión: p. ej., sarcasmo que el clasificador no ve
        r.append(f"el clasificador ({it['sentiment']}) y el LLM ({llm}) no coinciden")
    if it["analysis"]["peticiones"]:
        r.append("el cliente pide: " + "; ".join(it["analysis"]["peticiones"]))
    r += [name for name, fn in ALERTS.items() if fn(it["checks"])]
    return r


def judge_reasons(it: dict) -> list[str]:
    """Criterios que suspende el juez. Sin veredicto no hay enrutado posible: error explícito."""
    if it["response"] is None or it.get("genuina") is False:
        return []
    if "judge" not in it:
        raise ValueError(f"{it['id']}: sin veredicto del juez; el destino es «{PENDING}»")
    return [f"juez: {NAMES[k]}" for k in IDS if not it["judge"][k]["cumple"]]


def route(it: dict) -> list[str]:
    return pre_judge_reasons(it) + judge_reasons(it)


def destination(it: dict) -> str:
    """Destino de una reseña sin modificarla: PENDING mientras falte el veredicto del juez, de
    modo que nada se publica antes de que el juez termine."""
    needs_judge = it.get("response") is not None and it.get("genuina") is not False
    if needs_judge and "judge" not in it:
        return PENDING
    return REVIEW if it["reasons"] or route(it) else PUBLISH


def can_approve(it: dict) -> bool:
    """Una persona solo puede aprobar (o el sistema publicar) una reseña con veredicto del juez."""
    return destination(it) != PENDING


def demo_items(seed: int = DEFAULT_SEED) -> list[dict]:
    """Casos sintéticos con hotel (adversariales y de ficha) + reseñas reales del AHR.

    El AHR no se usó para entrenar el clasificador ni para desarrollar los prompts: es el test de
    referencia fuera de distribución. Sus hoteles no están en kb/, así que van sin ficha.
    """
    adv = json.loads((EVALS / "adversarial" / "generacion_v1.json").read_text(encoding="utf-8"))
    rag = json.loads(RAG_CASES.read_text(encoding="utf-8"))
    hotels = rag["hoteles_generacion_v1"]
    items = [{"id": c["id"], "hotel": hotels[c["id"]], "text": c["review"],
              "meta": {"grupo": "sintético", "tipo": c["tipo"]}} for c in adv["cases"]]  # fmt: skip
    items += [{"id": c["id"], "hotel": c["hotel"], "text": c["review"],
               "meta": {"grupo": "sintético", "tipo": c["tipo"]}} for c in rag["cases"]]  # fmt: skip
    ahr = (
        load_ahr_ood().groupby("rating", group_keys=False).sample(AHR_PER_RATING, random_state=seed)
    )
    items += [{"id": f"ahr-{r.id}", "title": r.title, "text": r.text,
               "meta": {"grupo": "AHR", "rating": int(r.rating), "label3": r.label3}}
              for r in ahr.itertuples()]  # fmt: skip
    return items


def read_csv(path: str) -> list[dict]:
    """CSV propio: id, hotel (opcional), title, text y, si los hay, tipo y esperado (van en meta).

    Separador detectado (`;` o `,`). Filas con el texto vacío se ignoran (plantilla a medias).
    """
    df = pd.read_csv(path, sep=None, engine="python", dtype=str, encoding="utf-8-sig").fillna("")
    df = df[df["text"].str.strip() != ""]
    return [
        {"id": r["id"], "hotel": r.get("hotel") or None, "title": r.get("title", ""),
         "text": r["text"], "meta": {"grupo": "propio", "tipo": r.get("tipo", ""),
                                     "esperado": r.get("esperado", "")}}
        for _, r in df.iterrows()
    ]  # fmt: skip


def read_jsonl(path: str) -> list[dict]:
    """Reseñas de la demo en modo recogida (recoger.py): el nick va solo en meta."""
    rows = [json.loads(x) for x in (ROOT / path).read_text(encoding="utf-8").splitlines() if x]
    return [
        {"id": r["id"], "hotel": r.get("hotel"), "title": r.get("title", ""), "text": r["text"],
         "fecha_ref": r["fecha"][:10] if r.get("fecha") else None,  # «hoy» para esa reseña
         "meta": {"grupo": "recogida", "nick": r.get("nick", "")}}
        for r in rows if r["text"].strip()
    ]  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="CSV con columnas id, hotel (opcional), title, text")
    ap.add_argument("--jsonl", help="reseñas recogidas (data/live/resenas_recogidas.jsonl)")
    ap.add_argument("--out", help="JSON de salida (por defecto, la cola de la demostración)")
    ap.add_argument("--prompt", default=PROMPT, choices=RAG_PROMPTS, help="prompt del generador")
    ap.add_argument(
        "--vivo",
        action="store_true",
        help="el CSV es de terceros: caché y salida en data/live (con --jsonl, siempre)",
    )
    args = ap.parse_args()
    items = (
        read_csv(args.csv) if args.csv else read_jsonl(args.jsonl) if args.jsonl else demo_items()
    )
    if not items:
        raise SystemExit("No hay reseñas con texto en el CSV.")
    live = bool(args.jsonl) or args.vivo
    out_path = ROOT / args.out if args.out else LIVE_QUEUE if live else QUEUE
    if live and not out_path.resolve().is_relative_to(DATA_LIVE):
        raise SystemExit(
            f"Reseñas de terceros: la salida tiene que ir en {DATA_LIVE} (fuera de git)."
        )
    out = run(items, prompt=args.prompt, live=live)
    queue = [it for it in out if it["decision"] == "revisión humana"]
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )
    if not (args.csv or args.jsonl):  # el informe es el de la demostración (sintéticos + AHR)
        write_report(out)
    log(
        f"OK: {len(out) - len(queue)} publicables, {len(queue)} a revisión → {out_path.relative_to(ROOT)}"
    )


def reason_kind(reason: str) -> str:
    """Agrupa motivos para contarlos: «confianza 0.71 < 0.85» -> «confianza baja»."""
    if reason.startswith("confianza"):
        return f"confianza < {THRESHOLD}"
    if reason.startswith("el clasificador"):
        return "el clasificador y el LLM no coinciden"
    if reason.startswith("el cliente pide"):
        return "el cliente pide algo"
    return reason


def write_report(out: list[dict]) -> None:
    syn = [it for it in out if it["meta"]["grupo"] == "sintético"]
    ahr = [it for it in out if it["meta"]["grupo"] == "AHR"]
    L = [
        "# Fase 5 · Pipeline completo y cola de revisión humana",
        "",
        f"Generado por `uv run just pipeline` · clasificador mRoBERTa (ensamble de 3 semillas, CPU), "
        f"umbral {THRESHOLD} · generador `{MODEL}` con prompt {PROMPT} y RAG · juez `{JUDGE_MODEL}` "
        f"con rúbrica {RUBRIC} y ficha. No editar a mano.",
        "",
        f"Entrada: {len(syn)} casos **sintéticos** con hotel de `kb/` (adversariales y de ficha contra "
        f"cliente) y {len(ahr)} reseñas **reales** del AHR ({AHR_PER_RATING} por puntuación), que no "
        "se usaron para entrenar ni para desarrollar los prompts; sus hoteles no están en `kb/` y van "
        "sin ficha.",
        "",
        "## Decisión",
        "",
        "| Grupo | Publicables | A revisión humana |",
        "|---|---|---|",
    ]
    for label, rows in (
        ("sintéticos", syn),
        *((f"AHR {k}★", [it for it in ahr if it["meta"]["rating"] == k]) for k in range(1, 6)),
    ):
        pub = sum(it["decision"] == "publicable" for it in rows)
        L.append(f"| {label} | {pub}/{len(rows)} | {len(rows) - pub}/{len(rows)} |")
    reasons = Counter(reason_kind(r) for it in out for r in it["reasons"])
    L += [
        "",
        "## Motivos de revisión (una reseña puede tener varios)",
        "",
        "| Motivo | Reseñas |",
        "|---|---|",
    ]
    L += [f"| {m} | {n} |" for m, n in reasons.most_common()]
    hits = sum(it["sentiment"] == it["meta"]["label3"] for it in ahr)
    L += ["", f"Clasificador en estas {len(ahr)} reseñas del AHR: acierta {hits}/{len(ahr)} "
          "(muestra pequeña: la cifra de referencia es el F1 de la Fase 3).", ""]  # fmt: skip
    L += [
        "## Casos sintéticos",
        "",
        "| Caso | Hotel | Sentimiento (confianza) | Decisión | Motivos |",
        "|---|---|---|---|---|",
    ]
    for it in syn:
        L.append(f"| `{it['id']}` | {it['hotel']} | {it['sentiment']} ({it['confidence']:.2f}) | "
                 f"{it['decision']} | {'; '.join(it['reasons']) or '—'} |")  # fmt: skip
    pub = [it for it in out if it["decision"] == "publicable"]
    L += ["", f"## Respuestas que se publicarían sin revisión ({len(pub)})", "",
          "Son las que más importa leer: nadie las revisaría antes de publicarlas.", ""]  # fmt: skip
    for it in pub:
        L += [
            f"**`{it['id']}`** · {it['sentiment']} ({it['confidence']:.2f})",
            "",
            f"> {it['review'][:400]}",
            "",
            it["response"],
            "",
        ]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
