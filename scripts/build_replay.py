"""Construye la página estática del modo repetición (docs/index.html, servida por GitHub Pages).

Toma las reseñas propias escritas para la demo (results/demo_propias.json, de `just pipeline
--csv … --out …`) y una selección de la demostración (evals/demo/seleccion_replay.json, sobre
results/pipeline_cola.json) con una nota sobre cada caso, y las incrusta como JSON en
scripts/replay_template.html. Un solo fichero, sin servidor ni modelos: solo lo que la página
muestra (nada de pesos ni cachés). Genera también la imagen para redes (docs/og.png).

No genera ni cambia ninguna respuesta del modelo: todo lo que muestra sale de resultados ya
versionados. Las cifras de la cabecera se calculan aquí.

Uso: uv run python scripts/build_replay.py
"""

import json
import re
from pathlib import Path

import numpy as np

from caso_uso_llm.evals.judge import JUDGE_MODEL
from caso_uso_llm.evals.rubric import IDS, criterios
from caso_uso_llm.generate.run import MODEL
from caso_uso_llm.latency import _rows, split_review
from caso_uso_llm.paths import RESULTS
from caso_uso_llm.pipeline import PUBLISH, RUBRIC, THRESHOLD
from caso_uso_llm.rag import kb
from caso_uso_llm.rag.retrieve import EMBED_MODEL

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (ROOT / "results" / "demo_propias.json",)  # las reseñas propias, completas
# Más una selección de la demostración, con una nota escrita después de ver la respuesta
DEMO = ROOT / "results" / "pipeline_cola.json"
SELECTION = ROOT / "evals" / "demo" / "seleccion_replay.json"
RATINGS = ROOT / "evals" / "demo" / "valoracion_propias.json"  # del autor, frente a lo esperado
TEMPLATE = ROOT / "scripts" / "replay_template.html"
OUT = ROOT / "docs" / "index.html"
OG = ROOT / "docs" / "og.png"
PAGE_URL = "https://javiromano.github.io/Spanish-hotel-review-LLM/"
REPO = "https://github.com/JaviRomano/Spanish-hotel-review-LLM"
LINKEDIN = "https://www.linkedin.com/in/franciscojavier-fernandezrumi/"  # contacto y prueba en vivo
GITHUB = "https://github.com/JaviRomano"
AUTHOR = "Fco Javier Fdez"
ROLE = "Data Engineer / ML"
GPU = "AMD RX 7900 XTX"  # README, «Requisitos»: el hardware no está en ningún fichero de config
GROUP = {
    "propio": "Reseñas propias",
    "sintético": "Casos sintéticos",
    "AHR": "Reseñas reales (AHR)",
}
QUOTE = re.compile(r"«([^»]{6,})»")


def highlights(it: dict, response: str, extra_text: str, extra_label: str) -> list[dict]:
    """Fragmentos de la respuesta que algo ya señala, con su fuente: la evidencia de los
    criterios que suspende el juez y las frases que el autor cita entre comillas en su
    valoración o nota. Solo si aparecen literalmente en la respuesta; no se elige nada nuevo."""
    out = []
    for k in IDS:
        v = (it.get("judge") or {}).get(k, {})
        ev = (v.get("evidencia") or "").strip().strip("«»\"'")
        if not v.get("cumple", True) and ev and ev in response:
            out.append({"text": ev, "comment": f"Juez: no cumple «{NAMES[k]}»"})
    note = extra_text if len(extra_text) <= 220 else extra_text[:217].rsplit(" ", 1)[0] + "…"
    for q in QUOTE.findall(extra_text or ""):
        if q in response and all(q not in h["text"] for h in out):
            out.append({"text": q, "comment": f"{extra_label}: {note}"})
    return out


def compact(it: dict, policies: dict) -> dict:
    meta = it.get("meta", {})
    hotel = kb.fichas().get(it["hotel"]) if it.get("hotel") else None
    return {
        "id": it["id"],
        "grupo": GROUP.get(meta.get("grupo"), meta.get("grupo", "")),
        "tipo": meta.get("tipo") or (f"{meta['rating']}★" if meta.get("rating") else ""),
        "titulo": it.get("title", ""),
        "esperado": meta.get("esperado", ""),
        # Criterio escrito antes de generar (reseñas propias) o nota escrita después (resto)
        "eval_mode": "criterio_previo" if meta.get("esperado") else "nota_posterior",
        "nota": "",
        "valoracion": None,
        "highlights": [],
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
                "criterio": NAMES[k],
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


def summary(demo: dict) -> dict:
    """Cifras de la cabecera, calculadas aquí desde los resultados versionados (no a mano): la
    demostración de 54 reseñas y la última medición de latencia de cada variante.

    Riesgo con una referencia independiente del sistema: las estrellas que puso el cliente. «X de
    las 46 que van a revisión» sería 0 por construcción; «reseñas reales de 1–3★ publicadas sin
    revisión» no lo es."""
    items = list(demo.values())
    runs = {}
    for f in sorted(RESULTS.glob("latencia_*.jsonl")):
        meta, rr = _rows(f)
        runs[meta.get("variante", "base")] = (meta, rr)
    meta, rr = runs["base"]
    _, ra = runs["A"]
    low = [it for it in items if it["meta"].get("rating") in (1, 2, 3)]
    return {
        "total": len(items),
        "sinteticos": sum(it["meta"]["grupo"] == "sintético" for it in items),
        "publicables": sum(it["decision"] == PUBLISH for it in items),
        "publicables_positivas": sum(
            it["decision"] == PUBLISH and it["sentiment"] == "positivo" for it in items
        ),
        "riesgo_total": len(low),
        "riesgo_publicadas": sum(it["decision"] == PUBLISH for it in low),
        "segundos": round(float(np.median([split_review(r, meta)["total"] for r in rr]))),
        "borrador": round(float(np.median([r["visible_s"] for r in ra]))),
        "generador": MODEL,
        "juez": JUDGE_MODEL,
        "gpu": GPU,
    }


def _size(tag: str) -> str:
    """«qwen3.6:27b-q4_K_M» -> «27B»: el tamaño sale de la etiqueta del modelo."""
    m = re.search(r":(\d+)b", tag)
    return f" {m.group(1)}B" if m else ""


def stack() -> list[list[str]]:
    """Ficha técnica de la cabecera (etiqueta, valor): los modelos salen de sus constantes."""
    gen = MODEL.split(":")[0].replace("qwen", "Qwen") + _size(MODEL)
    judge = JUDGE_MODEL.split(":")[0].replace("gemma4", "Gemma 4") + _size(JUDGE_MODEL)
    return [["Generador", gen], ["Juez", judge], ["Recuperación", f"BM25 + {EMBED_MODEL}"],
            ["Clasificador", "mRoBERTa ×3"], ["Ejecución", "local · " + GPU.removeprefix("AMD ")]]  # fmt: skip


def og_image(s: dict) -> None:
    """Imagen para enlaces compartidos (1200×630), con las mismas cifras que la cabecera."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(12, 6.3), dpi=100)
    # Mismos colores que la página (tokens --paper, --ink, --muted, --rule, --accent)
    paper, ink, muted, rule, accent = "#f4f6f3", "#17201c", "#56615b", "#cdd4ce", "#0f5c4a"
    fig.patch.set_facecolor(paper)
    t = lambda x, y, s_, **kw: fig.text(x, y, s_, color=kw.pop("c", ink), **kw)  # noqa: E731
    t(0.06, 0.82, "¿Cómo responde una IA a las", fontsize=40, fontweight="bold", family="serif")
    t(0.06, 0.70, "reseñas difíciles de un hotel?", fontsize=40, fontweight="bold", family="serif")
    t(0.06, 0.60, f"Clasificador + RAG + generador + juez LLM, 100 % local · {AUTHOR}",
      fontsize=19, c=muted)  # fmt: skip
    kpis = [(f"{s['riesgo_publicadas']} de {s['riesgo_total']}", "reseñas reales de 1–3★\npublicadas sin revisión"),
            (f"{s['publicables']} de {s['total']}", "se publican solas\n(conservador por diseño)"),
            (f"{s['segundos']} s", f"por reseña en una\n{GPU}")]  # fmt: skip
    fig.lines.append(plt.Line2D([0.06, 0.94], [0.50, 0.50], transform=fig.transFigure, color=rule))
    for i, (big, small) in enumerate(kpis):
        x = 0.06 + i * 0.30
        t(x, 0.33, big, fontsize=44, fontweight="bold", family="serif", c=accent if i == 0 else ink)
        t(x, 0.15, small, fontsize=16, c=muted)
    fig.savefig(OG, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    policies = {d.id: d.payload["titulo"] for d in kb.politicas()}
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    ratings = json.loads(RATINGS.read_text(encoding="utf-8"))["valoraciones"]
    skip = set(selection.get("excluir_propias", []))
    cases = []
    for src in SOURCES:
        if src.exists():
            for it in json.loads(src.read_text(encoding="utf-8")):
                if it["id"] in skip:
                    continue
                c = compact(it, policies) | {"valoracion": ratings.get(it["id"])}
                motivo = (c["valoracion"] or {}).get("motivo", "")
                c["highlights"] = highlights(
                    it, c["response"] or "", motivo, "Valoración del autor"
                )
                cases.append(c)
    demo = {it["id"]: it for it in json.loads(DEMO.read_text(encoding="utf-8"))}
    for sel in selection["casos"]:
        it = demo[sel["id"]]
        c = compact(it, policies) | {"nota": sel["nota"], "titulo": sel["titulo"]}
        c["highlights"] = highlights(it, c["response"] or "", sel["nota"], "Nota posterior")
        cases.append(c)
    ids = {c["id"] for c in cases}
    tour = selection["recorrido"]
    missing = [s["id"] for s in tour if s["id"] not in ids]
    assert not missing, f"el recorrido nombra casos que la página no muestra: {missing}"
    s = summary(demo)
    doc = {"umbral": THRESHOLD, "casos": cases, "recorrido": tour, "resumen": s,
           "stack": stack()}  # fmt: skip
    data = json.dumps(doc, ensure_ascii=False, indent=1)
    # Dentro de <script>, «</» cerraría la etiqueta antes de tiempo
    page = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", data.replace("</", "<\\/"))
    for key, value in {"__REPO__": REPO, "__LINKEDIN__": LINKEDIN, "__GITHUB__": GITHUB,
                       "__AUTHOR__": AUTHOR, "__ROLE__": ROLE, "__PAGE_URL__": PAGE_URL}.items():  # fmt: skip
        page = page.replace(key, value)
    left = re.findall(r"__[A-Z_]+__", page)
    assert not left, f"marcadores sin sustituir en la plantilla: {sorted(set(left))}"
    OUT.write_text(page, encoding="utf-8", newline="\n")
    og_image(s)
    print(f"{len(cases)} casos -> {OUT.relative_to(ROOT)} · {OG.relative_to(ROOT)}")


NAMES = {c.id: c.nombre for c in criterios(RUBRIC)}

if __name__ == "__main__":
    main()
