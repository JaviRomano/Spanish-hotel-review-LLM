"""Hoja HTML para anotar las respuestas de la demo en vivo (data/live/notas.html, fuera de git).

Una tarjeta por reseña de data/live/resenas_vivo.jsonl: nick, fecha, hotel, reseña, respuesta,
decisión con motivos y veredicto del juez. Para cada una: valoración, dos marcas (repite
expresiones hechas, copia trozos literales de la reseña) y notas. Guarda en el navegador y
exporta data/live/notas_vivo.csv (separador «;», UTF-8 con BOM).

Uso: uv run python scripts/notas_vivo.py [--prompt v8]
  --prompt: solo las reseñas respondidas con ese prompt (las anteriores a que se guardara el
  prompt son v6) -> data/live/notas_vivo_v8.html y notas_vivo_v8.csv
"""
# ruff: noqa: E501  (CSS y JavaScript en línea)

import argparse
import html
import json
from pathlib import Path

from caso_uso_llm.evals.rubric import criterios
from caso_uso_llm.rag import kb

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "live" / "resenas_vivo.jsonl"
OUT = ROOT / "data" / "live" / "notas.html"
NAMES = {c.id: c.nombre for c in criterios("v2g")}

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--bd:#c8c8c8;--card:#f6f6f4;--muted:#5f5f5b;--ok:#1f7a3d;--warn:#9a6700;--ko:#b3261e;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root{--bg:#1c1c1b;--fg:#ececea;--bd:#4a4a47;--card:#262625;--muted:#a9a8a2;--ok:#5fd18a;--warn:#e3b341;--ko:#ff8a80;--accent:#5a9be8}}
*{box-sizing:border-box}
body{font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0 auto;max-width:1200px;padding:0 16px 80px}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--bd);padding:10px 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:2}
header b{margin-right:auto}
button{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
.card{background:var(--card);border:1px solid var(--bd);border-left:6px solid var(--bd);border-radius:8px;padding:14px;margin:16px 0}
.card.correcta{border-left-color:var(--ok)}.card.mejorable{border-left-color:var(--warn)}.card.incorrecta{border-left-color:var(--ko)}
.meta{color:var(--muted);font-size:.88rem;margin-bottom:8px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media (max-width:820px){.cols{grid-template-columns:1fr}}
.lab{font-size:.78rem;text-transform:uppercase;color:var(--muted);margin:8px 0 3px}
.txt{white-space:pre-wrap;background:var(--bg);border:1px solid var(--bd);border-radius:6px;padding:8px}
ul{margin:4px 0;padding-left:18px}
.row{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin-top:10px}
label{cursor:pointer}
textarea{width:100%;font:inherit;padding:6px 8px;border:1px solid var(--bd);border-radius:6px;background:var(--bg);color:var(--fg);margin-top:6px}
details{margin-top:6px}
"""

JS = r"""
const KEY = "__KEY__";
const st = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } })();
// Servida por scripts/servir_notas.py (p. ej., desde el móvil por el túnel), las notas también
// se guardan en el PC: el progreso no depende del navegador ni del enlace del túnel.
const SERVED = location.protocol.startsWith("http");
let timer = null;
const push = () => { if (SERVED) fetch("estado", {method: "POST", body: JSON.stringify(st)}).catch(() => {}); };
const save = () => {
  try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {}
  clearTimeout(timer); timer = setTimeout(push, 800);
};
const get = id => (st[id] = st[id] || {});
function paint() {
  let n = 0;
  for (const id of IDS) {
    const v = get(id).valoracion || ""; if (v) n++;
    const c = document.getElementById("c-" + id);
    c.classList.remove("correcta", "mejorable", "incorrecta"); if (v) c.classList.add(v);
  }
  document.getElementById("prog").textContent = n + " de " + IDS.length + " valoradas";
}
document.addEventListener("change", e => {
  const t = e.target, id = t.dataset.id; if (!id) return;
  get(id)[t.dataset.k] = t.type === "checkbox" ? t.checked : t.value; save(); paint();
});
document.addEventListener("input", e => { const t = e.target; if (t.tagName === "TEXTAREA") { get(t.dataset.id).notas = t.value; save(); } });
function fill() { for (const id of IDS) {
  const s = get(id);
  document.querySelectorAll(`[data-id="${id}"]`).forEach(el => {
    if (el.type === "radio") el.checked = s.valoracion === el.value;
    else if (el.type === "checkbox") el.checked = !!s[el.dataset.k];
    else if (el.tagName === "TEXTAREA") el.value = s.notas || "";
  });
} }
const q = s => '"' + String(s ?? "").replace(/"/g, '""') + '"';
document.getElementById("exp").onclick = () => {
  const L = ["id;nick;valoracion;repite_expresiones;copia_literal;notas"];
  for (const id of IDS) { const s = get(id); L.push([q(id), q(NICKS[id]), q(s.valoracion), s.repite ? 1 : 0, s.copia ? 1 : 0, q(s.notas)].join(";")); }
  const csv = "﻿" + L.join("\n") + "\n";
  if (SERVED) {
    fetch("csv", {method: "POST", body: csv})
      .then(r => alert(r.ok ? "Notas guardadas en el PC (__CSV__)." : "No se pudo guardar en el PC."))
      .catch(() => alert("No se pudo guardar en el PC."));
    return;
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
  a.download = "__CSV__"; a.click();
};
fill(); paint();
if (SERVED) fetch("estado").then(r => r.ok ? r.json() : {}).then(srv => {
  for (const [id, v] of Object.entries(srv || {})) st[id] = Object.assign({}, v, st[id] || {});
  fill(); paint();
}).catch(() => {});
"""


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def card(r: dict) -> str:
    rid = r["id"]
    hotel = kb.fichas().get(r["hotel"]) if r.get("hotel") else None
    hotel_txt = f"{hotel['nombre']} ({hotel['ciudad']})" if hotel else "sin ficha"
    reasons = "".join(f"<li>{esc(m)}</li>" for m in r["motivos"]) or "<li>—</li>"
    failed = [NAMES.get(k, k) for k, ok in r.get("juez", {}).items() if not ok]
    judge = "aprueba los 8 criterios" if not failed else "suspende: " + ", ".join(failed)
    decision = "✅ se publicaría" if r["decision"] == "publicable" else "👤 a revisión humana"
    radios = "".join(
        f"<label><input type=radio name='v-{rid}' data-id='{rid}' data-k=valoracion value={v}> {t}</label>"
        for v, t in (
            ("correcta", "Correcta"),
            ("mejorable", "Mejorable"),
            ("incorrecta", "Incorrecta"),
        )
    )
    return f"""
<section class=card id='c-{rid}'>
  <div class=meta><b>{esc(r["nick"])}</b> · {esc(r["fecha"].replace("T", " "))} · {esc(hotel_txt)} · {esc(rid)}</div>
  <div class=cols>
    <div><div class=lab>Reseña</div><div class=txt>{esc(r["resena"])}</div></div>
    <div><div class=lab>Respuesta generada</div><div class=txt>{esc(r.get("respuesta") or "(sin respuesta)")}</div></div>
  </div>
  <details><summary>{decision} · sentimiento {esc(r["sentimiento"])} ({r["confianza"]:.2f}) · juez {esc(judge)}</summary><ul>{reasons}</ul></details>
  <div class=row>{radios}
    <label><input type=checkbox data-id='{rid}' data-k=repite> Repite expresiones hechas</label>
    <label><input type=checkbox data-id='{rid}' data-k=copia> Copia trozos literales de la reseña</label></div>
  <textarea rows=3 data-id='{rid}' placeholder='Notas: qué está bien, qué cambiarías y por qué'></textarea>
</section>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", help="solo las reseñas respondidas con este prompt")
    ap.add_argument("--desde", help="solo las reseñas desde esta fecha (AAAA-MM-DD)")
    args = ap.parse_args()
    rows = [json.loads(line) for line in SRC.read_text(encoding="utf-8").splitlines() if line]
    out, key, csv_name = OUT, "notas_vivo_v1", "notas_vivo.csv"
    if args.prompt:
        rows = [r for r in rows if r.get("prompt", "v6") == args.prompt]
        out = OUT.with_name(f"notas_vivo_{args.prompt}.html")
        key, csv_name = f"notas_vivo_{args.prompt}", f"notas_vivo_{args.prompt}.csv"
    if args.desde:
        rows = [r for r in rows if r["fecha"] >= args.desde]
        tag = args.desde.replace("-", "")
        out = out.with_name(f"{out.stem}_{tag}.html")
        key, csv_name = f"{key}_{tag}", csv_name.replace(".csv", f"_{tag}.csv")
    js = JS.replace("__KEY__", key).replace("__CSV__", csv_name)
    doc = (
        "<!doctype html><html lang=es><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Notas de la demo en vivo</title><style>{CSS}</style><body>"
        f"<header><b>Notas de la demo en vivo · {len(rows)} reseñas</b><span id=prog></span>"
        "<button id=exp>Descargar notas (CSV)</button></header>"
        + "".join(card(r) for r in rows)
        + f"<script>const IDS={json.dumps([r['id'] for r in rows])};"
        f"const NICKS={json.dumps({r['id']: r['nick'] for r in rows}, ensure_ascii=False)};{js}</script></body></html>"
    )
    out.write_text(doc, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
