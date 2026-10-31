"""Relevancia del RAG: etiquetas de Claude frente a la primera pasada humana a ciegas.

Compara evals/retrieval/consultas_v1.json (Claude) con relevancia_primera_pasada.csv (persona, sin
ver las de Claude ni el orden de ningún buscador) y repite la evaluación de la recuperación con cada
juego de etiquetas. La primera pasada no se corrige después de ver esto, y el resultado no se usa
para afinar la recuperación: con 30 consultas sintéticas sería sobreajuste.

Uso: uv run just relevancia  (necesita Ollama con bge-m3)
"""

import csv
import json

import numpy as np
from sklearn.metrics import cohen_kappa_score

from caso_uso_llm.paths import EVALS, RESULTS, ROOT
from caso_uso_llm.rag import kb
from caso_uso_llm.rag.eval_retrieval import load_queries, per_query
from caso_uso_llm.rag.generate_rag import K_EXAMPLES, K_POLICIES
from caso_uso_llm.rag.retrieve import METHODS, Embedder, Retriever
from caso_uso_llm.seed import DEFAULT_SEED

HUMAN = EVALS / "retrieval" / "relevancia_primera_pasada.csv"
OUT = RESULTS / "phase5_relevancia.json"
REPORT = ROOT / "reports" / "phase5_relevancia_humana.md"
# Índice -> (documentos, cuántos toma el prompt, método que usa el pipeline)
INDICES = {
    "politicas": (kb.politicas, K_POLICIES, "hibrida"),
    "respuestas": (kb.respuestas, K_EXAMPLES, "densa"),
}
NONE = "ninguna"
N_BOOT = 2000


def read_human() -> dict[str, dict]:
    with HUMAN.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    parse = lambda s: [] if s == NONE else s.split("|")  # noqa: E731
    return {
        r["id"]: {g: parse(r[g]) for g in INDICES} | {"notas": r["notas"].strip()} for r in rows
    }


def agreement(queries: list[dict], human: dict, group: str, doc_ids: list[str]) -> dict:
    a, b, exact, jaccard = [], [], 0, []
    for q in queries:
        c, h = set(q[group]), set(human[q["id"]][group])
        a += [d in c for d in doc_ids]
        b += [d in h for d in doc_ids]
        exact += c == h
        jaccard.append(len(c & h) / len(c | h) if c | h else 1.0)
    return {"kappa": float(cohen_kappa_score(a, b)), "iguales": exact,
            "jaccard": float(np.mean(jaccard)), "n_claude": sum(a), "n_humano": sum(b)}  # fmt: skip


def evaluate(rankings: dict, labels: dict[str, list[str]], k_prod: int) -> dict:
    """Métricas por método sobre las consultas con algún relevante según esas etiquetas."""
    out = {}
    for method, ranks in rankings.items():
        rows = []
        for qid, relevant in labels.items():
            if relevant:
                m = per_query(ranks[qid], relevant)
                m["id"], m[f"recall@{k_prod}"] = (
                    qid,
                    (len(set(ranks[qid][:k_prod]) & set(relevant)) / len(relevant)),
                )
                rows.append(m)
        out[method] = rows
    return out


def mean(rows: list[dict], key: str) -> float:
    return float(np.mean([r[key] for r in rows]))


def paired(a: list[dict], b: list[dict], key: str, seed: int = DEFAULT_SEED) -> tuple:
    """Diferencia media a - b por consulta, con IC 95 % por bootstrap."""
    d = np.array([x[key] - y[key] for x, y in zip(a, b, strict=True)])
    rng = np.random.default_rng(seed)
    boots = rng.choice(d, size=(N_BOOT, len(d))).mean(axis=1)
    return float(d.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def main() -> None:
    queries, human = load_queries(), read_human()
    assert {q["id"] for q in queries} == set(human), "la hoja no cubre las mismas consultas"
    embedder = Embedder()
    results: dict = {"n_queries": len(queries), "indices": {}}
    for group, (loader, k_prod, method_prod) in INDICES.items():
        docs = loader()
        retriever = Retriever(docs, embedder)
        rankings = {m: {q["id"]: [d.id for d in retriever.rank(q["texto"], m)] for q in queries}
                    for m in METHODS}  # fmt: skip
        claude = {q["id"]: q[group] for q in queries}
        person = {q["id"]: human[q["id"]][group] for q in queries}
        by_claude = evaluate(rankings, claude, k_prod)
        by_person = evaluate(rankings, person, k_prod)
        top = {qid: rankings[method_prod][qid][:k_prod] for qid in person}
        useful = sum(len(set(top[q]) & set(person[q])) for q in person)
        results["indices"][group] = {
            "n_docs": len(docs), "k_prod": k_prod,
            "metodo_prod": method_prod,
            "acuerdo": agreement(queries, human, group, [d.id for d in docs]),
            "claude": by_claude, "humano": by_person,
            "sin_relevante_humano": [q for q, v in person.items() if not v],
            "sin_relevante_claude": [q for q, v in claude.items() if not v],
            "documentos_produccion": len(person) * k_prod, "utiles_produccion": useful,
            "desacuerdos": [
                {"id": q["id"], "claude": sorted(claude[q["id"]]), "humano": sorted(person[q["id"]])}
                for q in queries if set(claude[q["id"]]) != set(person[q["id"]])
            ],
        }  # fmt: skip
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                   newline="\n")  # fmt: skip
    write_report(results, human)
    print(REPORT)


def write_report(results: dict, human: dict) -> None:
    L = [
        "# Fase 5 · Relevancia: etiquetas de Claude frente a una persona",
        "",
        f"Generado por `uv run just relevancia` · {results['n_queries']} consultas **sintéticas** "
        "redactadas por Claude. Primera pasada humana a ciegas, congelada antes de comparar "
        "([`relevancia_primera_pasada.csv`](../evals/retrieval/relevancia_primera_pasada.csv)). No editar a mano.",
        "",
    ]
    for group, r in results["indices"].items():
        a, k = r["acuerdo"], r["k_prod"]
        keys = ("recall@1", "recall@3", f"recall@{k}", "mrr")
        keys = tuple(dict.fromkeys(keys))
        L += [
            f"## {group.capitalize()} ({r['n_docs']} documentos; el prompt toma {k})",
            "",
            f"Acuerdo con Claude: kappa **{a['kappa']:.2f}** · {a['iguales']} de {results['n_queries']} "
            f"consultas idénticas · Jaccard medio {a['jaccard']:.2f} · relevantes marcados: "
            f"Claude {a['n_claude']}, persona {a['n_humano']}.",
            "",
            f"Consultas sin ningún relevante: Claude {len(r['sin_relevante_claude'])}, "
            f"persona {len(r['sin_relevante_humano'])}. Según la persona, de los "
            f"{r['documentos_produccion']} documentos que el pipeline ({r['metodo_prod']}) entregaría al prompt, "
            f"{r['utiles_produccion']} son relevantes.",
            "",
            "| Etiquetas | Método | n | " + " | ".join(keys) + " |",
            "|---|---|---|" + "---|" * len(keys),
        ]
        for name, title in (("claude", "Claude"), ("humano", "Persona")):
            for method, rows in r[name].items():
                vals = " | ".join(f"{mean(rows, x):.2f}" for x in keys)
                L.append(f"| {title} | {method} | {len(rows)} | {vals} |")
        p = r["humano"]
        L += ["", "Diferencias pareadas con etiquetas de la persona (IC 95 %, bootstrap):", ""]
        for x, y in (("hibrida", "densa"), ("hibrida", "bm25")):
            for key in ("mrr", f"recall@{k}"):
                d, lo, hi = paired(p[x], p[y], key)
                L.append(f"- {x} − {y}, {key}: {d:+.2f} ({lo:+.2f} a {hi:+.2f})")
        L += ["", f"### Desacuerdos ({len(r['desacuerdos'])})", "",
              "| Consulta | Claude | Persona | Nota |", "|---|---|---|---|"]  # fmt: skip
        for d in r["desacuerdos"]:
            note = human[d["id"]]["notas"].replace("|", "/").replace("\n", " ")
            L.append(f"| `{d['id']}` | {', '.join(d['claude']) or '—'} | "
                     f"{', '.join(d['humano']) or '—'} | {note} |")  # fmt: skip
        L.append("")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
