"""Hoja de etiquetado a ciegas de la relevancia de la recuperación (Fase 5).

Muestra cada consulta de evals/retrieval/consultas_v1.json con todas las políticas y todas las
respuestas aprobadas, para marcar las relevantes. Es a ciegas: no lleva las etiquetas de Claude ni
el orden de ningún buscador. Guarda el progreso en el navegador y exporta
`id;politicas;respuestas;notas` para evals/retrieval/relevancia_primera_pasada.csv, que no se
corrige después de comparar.

Uso: uv run just hoja-relevancia
"""
# ruff: noqa: E501  (textos y JS: partirlos los haría menos legibles)

import json
import random
from pathlib import Path

from calibracion_vista import CSS as BASE_CSS
from calibracion_vista import esc

from caso_uso_llm.rag import kb
from caso_uso_llm.seed import DEFAULT_SEED

ROOT = Path(__file__).resolve().parents[1]
QUERIES = ROOT / "evals" / "retrieval" / "consultas_v1.json"
ADVERSARIAL = ROOT / "evals" / "adversarial" / "generacion_v1.json"
OUT = ROOT / "evals" / "retrieval" / "relevancia_vista.html"
NONE = "ninguna"  # distingue «ninguna es relevante» de «sin contestar»

CRITERIO = [
    (
        "Política relevante",
        "quien responde la necesita para no equivocarse o no prometer de más en esta reseña.",
    ),
    (
        "Respuesta relevante",
        "trata el mismo tipo de problema y serviría de ejemplo para responder a esta reseña, aunque sea de otro hotel.",
    ),
]

CSS = (
    BASE_CSS
    + """
fieldset{border:1px solid var(--bd);border-radius:4px;margin:0;padding:.4rem .6rem;min-width:0}
legend{font-size:.8rem;color:var(--muted);text-transform:uppercase}
fieldset label{display:block;padding:.15rem 0;cursor:pointer}
fieldset label.none{border-bottom:1px solid var(--bd);margin-bottom:.25rem;font-weight:600}
"""
)

JS = r"""
const KEY = "relevancia_humana_v1", GROUPS = ["politicas", "respuestas"];
const state = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } })();
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };
const entry = id => state[id] = state[id] || {politicas: [], respuestas: [], notas: ""};
const complete = id => GROUPS.every(g => ((state[id] || {})[g] || []).length > 0);
function refresh() {
  let n = 0;
  for (const id of IDS) {
    const ok = complete(id); n += ok;
    document.getElementById("card-" + id).classList.toggle("done", ok);
  }
  document.getElementById("prog").textContent = n + " de " + IDS.length + " completas";
}
function paint() {
  document.querySelectorAll("input[type=checkbox]").forEach(i => {
    i.checked = ((state[i.dataset.id] || {})[i.dataset.g] || []).includes(i.value);
  });
  document.querySelectorAll("textarea").forEach(t => { t.value = (state[t.dataset.id] || {}).notas || ""; });
}
document.addEventListener("change", e => {
  const t = e.target;
  if (t.type !== "checkbox") return;
  const s = entry(t.dataset.id), g = t.dataset.g;
  if (t.value === NONE) s[g] = t.checked ? [NONE] : [];  // «ninguna» excluye al resto
  else s[g] = [...s[g].filter(v => v !== NONE && v !== t.value), ...(t.checked ? [t.value] : [])];
  save(); paint(); refresh();
});
document.addEventListener("input", e => {
  const t = e.target;
  if (t.tagName === "TEXTAREA") { entry(t.dataset.id).notas = t.value; save(); }
});
const q = s => '"' + s.replace(/"/g, '""') + '"';
function csv() {
  const L = ["id;politicas;respuestas;notas"];
  for (const id of IDS) {
    const s = state[id] || {};
    L.push([id, (s.politicas || []).sort().join("|"), (s.respuestas || []).sort().join("|"), q(s.notas || "")].join(";"));
  }
  return L.join("\n") + "\n";
}
document.getElementById("exp").onclick = () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + csv()], {type: "text/csv;charset=utf-8"}));
  a.download = "relevancia_primera_pasada.csv"; a.click();
};
paint(); refresh();
"""


def rows(seed: int = DEFAULT_SEED) -> list[dict]:
    """Solo id y texto: las etiquetas de Claude no deben llegar a la hoja."""
    adv = {
        c["id"]: c["review"] for c in json.loads(ADVERSARIAL.read_text(encoding="utf-8"))["cases"]
    }
    out = []
    for q in json.loads(QUERIES.read_text(encoding="utf-8"))["consultas"]:
        qid = q.get("adversarial") or q["id"]
        out.append({"id": qid, "texto": adv[qid] if "adversarial" in q else q["texto"]})
    random.Random(seed).shuffle(out)
    return out


def checks(qid: str, group: str, docs: list[tuple[str, str, str]]) -> str:
    none = (f"<label class=none><input type=checkbox data-id={qid} data-g={group} value={NONE}> "
            "Ninguna</label>")  # fmt: skip
    items = "".join(
        f"<label title='{esc(full).replace(chr(39), '&#39;')}'>"
        f"<input type=checkbox data-id={qid} data-g={group} value={did}> {esc(short)}</label>"
        for did, short, full in docs
    )
    return none + items


def main() -> None:
    policies = [(d.id, d.payload["titulo"], d.payload["texto"]) for d in kb.politicas()]
    replies = [(d.id, d.payload["resena"][:95] + "…", d.payload["resena"]) for d in kb.respuestas()]
    ref_pol = "".join(f"<li><b>{esc(s)}</b><small>{esc(f)}</small></li>" for _, s, f in policies)
    ref_res = "".join(
        f"<li>{esc(d.payload['resena'])}<small>{esc(d.payload['respuesta'])}</small></li>"
        for d in kb.respuestas()
    )
    criterio = "".join(f"<li><b>{n}:</b> {esc(t)}</li>" for n, t in CRITERIO)
    body = [
        "<header><b>Relevancia a ciegas</b><span id=prog></span>",
        "<button class=main id=exp>Descargar etiquetas (CSV)</button></header>",
        f"<details class=guia open><summary>Criterio</summary><ul>{criterio}</ul><p>Marca lo que "
        "necesitarías tú, no lo que crees que encontraría un buscador. Si dudas, deja una nota.</p></details>",
        f"<details class=guia><summary>Las {len(policies)} políticas, completas</summary><ul>{ref_pol}</ul></details>",
        f"<details class=guia><summary>Las {len(replies)} respuestas aprobadas, completas</summary><ul>{ref_res}</ul></details>",
    ]
    data = rows()
    for r in data:
        qid = r["id"]
        body.append(
            f"<section class=card id=card-{qid}><h2>{qid}</h2>"
            f"<div class=lab>Reseña</div><div class=txt>{esc(r['texto'])}</div><br><div class=cols>"
            f"<fieldset><legend>Políticas</legend>{checks(qid, 'politicas', policies)}</fieldset>"
            f"<fieldset><legend>Respuestas aprobadas</legend>{checks(qid, 'respuestas', replies)}</fieldset>"
            f"</div><textarea rows=2 data-id={qid} placeholder='Notas (dudas, casos frontera)'></textarea></section>"
        )
    script = f"const IDS={json.dumps([r['id'] for r in data])},NONE={json.dumps(NONE)};{JS}"
    doc = (
        "<!doctype html><html lang=es><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Relevancia a ciegas</title><style>{CSS}</style><body>{''.join(body)}"
        f"<script>{script}</script></body></html>"
    )
    OUT.write_text(doc, encoding="utf-8", newline="\n")
    print(OUT)


if __name__ == "__main__":
    main()
