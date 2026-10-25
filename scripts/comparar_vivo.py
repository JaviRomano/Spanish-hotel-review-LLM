"""Hoja HTML para evaluar las respuestas v8 a las reseñas de los colaboradores (fuera de git).

Para cada reseña: la respuesta antigua (demo en vivo, prompt v6) con la nota de Javier, y la
respuesta nueva (prompt v8) con su decisión, motivos y comprobaciones. Se valora la nueva igual
que la antigua (valoración, repite expresiones, copia literal, notas) y se exporta
data/live/notas_v8.csv.

Uso: uv run python scripts/comparar_vivo.py   ->  data/live/comparacion_v8.html
"""
# ruff: noqa: E501  (CSS y JavaScript en línea)

import csv
import html
import json
from pathlib import Path

from caso_uso_llm.rag import kb

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "live"
OUT = LIVE / "comparacion_v8.html"

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--bd:#c8c8c8;--card:#f6f6f4;--muted:#5f5f5b;--ok:#1f7a3d;--warn:#9a6700;--ko:#b3261e;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root{--bg:#1c1c1b;--fg:#ececea;--bd:#4a4a47;--card:#262625;--muted:#a9a8a2;--ok:#5fd18a;--warn:#e3b341;--ko:#ff8a80;--accent:#5a9be8}}
*{box-sizing:border-box}
body{font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0 auto;max-width:1250px;padding:0 16px 80px}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--bd);padding:10px 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:2}
header b{margin-right:auto}
button{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
.card{background:var(--card);border:1px solid var(--bd);border-left:6px solid var(--bd);border-radius:8px;padding:14px;margin:18px 0}
.card.correcta{border-left-color:var(--ok)}.card.mejorable{border-left-color:var(--warn)}.card.incorrecta{border-left-color:var(--ko)}
.meta{color:var(--muted);font-size:.88rem;margin-bottom:6px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media (max-width:860px){.cols{grid-template-columns:1fr}}
.lab{font-size:.78rem;text-transform:uppercase;color:var(--muted);margin:8px 0 3px}
.txt{white-space:pre-wrap;background:var(--bg);border:1px solid var(--bd);border-radius:6px;padding:8px}
.old{opacity:.85}
.note{border-left:3px solid var(--warn);padding:4px 8px;margin-top:6px;font-size:.92rem}
ul{margin:4px 0;padding-left:18px;font-size:.92rem}
.row{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin-top:10px}
label{cursor:pointer}
textarea{width:100%;font:inherit;padding:6px 8px;border:1px solid var(--bd);border-radius:6px;background:var(--bg);color:var(--fg);margin-top:6px}
"""

JS = r"""
const KEY = "notas_v8_v1";
const st = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } })();
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} };
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
for (const id of IDS) {
  const s = get(id);
  document.querySelectorAll(`[data-id="${id}"]`).forEach(el => {
    if (el.type === "radio") el.checked = s.valoracion === el.value;
    else if (el.type === "checkbox") el.checked = !!s[el.dataset.k];
    else if (el.tagName === "TEXTAREA") el.value = s.notas || "";
  });
}
const q = s => '"' + String(s ?? "").replace(/"/g, '""') + '"';
document.getElementById("exp").onclick = () => {
  const L = ["id;valoracion_v8;repite_expresiones;copia_literal;notas_v8"];
  for (const id of IDS) { const s = get(id); L.push([q(id), q(s.valoracion), s.repite ? 1 : 0, s.copia ? 1 : 0, q(s.notas)].join(";")); }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + L.join("\n") + "\n"], {type: "text/csv;charset=utf-8"}));
  a.download = "notas_v8.csv"; a.click();
};
paint();
"""


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def main() -> None:
    old = {
        json.loads(x)["id"]: json.loads(x)
        for x in (LIVE / "resenas_vivo.jsonl").read_text(encoding="utf-8").splitlines()
        if x
    }
    notes = {
        r["id"]: r
        for r in csv.DictReader((LIVE / "notas_vivo.csv").open(encoding="utf-8-sig"), delimiter=";")
    }
    new = json.loads((LIVE / "colaboradores_v8.json").read_text(encoding="utf-8"))
    cards = []
    for it in new:
        rid, o, n = it["id"], old[it["id"]], notes.get(it["id"], {})
        hotel = kb.fichas().get(it["hotel"]) if it.get("hotel") else None
        decision = "✅ se publicaría" if it["decision"] == "publicable" else "👤 a revisión humana"
        trap = " · <b>tratada como reseña trampa</b>" if it.get("genuina") is False else ""
        reasons = "".join(f"<li>{esc(r)}</li>" for r in it["reasons"]) or "<li>—</li>"
        radios = "".join(
            f"<label><input type=radio name='v-{rid}' data-id='{rid}' data-k=valoracion value={v}> {t}</label>"
            for v, t in (
                ("correcta", "Correcta"),
                ("mejorable", "Mejorable"),
                ("incorrecta", "Incorrecta"),
            )
        )
        cards.append(f"""
<section class=card id='c-{rid}'>
  <div class=meta><b>{esc(o["nick"])}</b> · {esc(hotel["nombre"] if hotel else "sin ficha")} · {esc(rid)}</div>
  <div class=lab>Reseña</div><div class=txt>{esc(it["review"])}</div>
  <div class=cols>
    <div class=old><div class=lab>Antes (v6) · tu valoración: {esc(n.get("valoracion", "—"))}</div>
      <div class=txt>{esc(o.get("respuesta"))}</div>
      <div class=note>{esc(n.get("notas") or "sin notas")}</div></div>
    <div><div class=lab>Ahora (v8) · {decision}{trap}</div>
      <div class=txt>{esc(it.get("response"))}</div><ul>{reasons}</ul></div>
  </div>
  <div class=row>{radios}
    <label><input type=checkbox data-id='{rid}' data-k=repite> Repite expresiones hechas</label>
    <label><input type=checkbox data-id='{rid}' data-k=copia> Copia trozos literales de la reseña</label></div>
  <textarea rows=3 data-id='{rid}' placeholder='Notas sobre la respuesta v8'></textarea>
</section>""")
    doc = (
        "<!doctype html><html lang=es><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Respuestas v8 a los colaboradores</title><style>{CSS}</style><body>"
        f"<header><b>Respuestas v8 · {len(new)} reseñas de colaboradores</b><span id=prog></span>"
        "<button id=exp>Descargar notas (CSV)</button></header>"
        + "".join(cards)
        + f"<script>const IDS={json.dumps([it['id'] for it in new])};{JS}</script></body></html>"
    )
    OUT.write_text(doc, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
