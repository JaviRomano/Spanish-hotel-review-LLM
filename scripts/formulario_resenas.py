"""Formulario HTML para escribir reseñas propias de la demo (evals/demo/formulario.html).

Cada reseña: hotel (con lo que dice su ficha), tipo, título, texto y qué se espera de una buena
respuesta. Guarda el progreso en el navegador y exporta resenas_propias.csv con el formato que
lee `just pipeline --csv` (separador `;`, UTF-8 con BOM). También importa un CSV ya exportado.

Uso: uv run python scripts/formulario_resenas.py
"""
# ruff: noqa: E501  (CSS y JavaScript en línea)

import json
from pathlib import Path

from caso_uso_llm.rag import kb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "demo" / "formulario.html"

TIPOS = [
    "sarcasmo", "malsonante", "insulto al personal", "amenaza", "acusación grave",
    "premisa falsa", "pide compensación", "inyección", "idiomas mezclados", "emojis o mayúsculas",
    "dialecto o jerga", "ambigua", "fuera de tema", "datos personales", "muy corta", "muy larga",
    "positiva", "neutral", "negativa",
]  # fmt: skip

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--bd:#c8c8c8;--card:#f6f6f4;--muted:#5f5f5b;--accent:#2a78d6;--ko:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#1c1c1b;--fg:#ececea;--bd:#4a4a47;--card:#262625;--muted:#a9a8a2;--accent:#5a9be8;--ko:#ff8a80}}
*{box-sizing:border-box}
body{font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0 auto;max-width:1100px;padding:0 16px 80px}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--bd);padding:10px 0;display:flex;gap:10px;flex-wrap:wrap;align-items:center;z-index:2}
header b{margin-right:auto}
button,label.btn{font:inherit;padding:6px 12px;border:1px solid var(--bd);border-radius:6px;background:var(--card);color:var(--fg);cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.card{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:12px;margin:14px 0}
.row{display:grid;grid-template-columns:110px 1fr 1fr;gap:10px}
@media (max-width:760px){.row{grid-template-columns:1fr}}
.lab{display:block;font-size:.8rem;color:var(--muted);margin:8px 0 3px}
input,select,textarea{width:100%;font:inherit;padding:6px 8px;border:1px solid var(--bd);border-radius:6px;background:var(--bg);color:var(--fg)}
textarea{resize:vertical}
.ficha{font-size:.85rem;color:var(--muted);white-space:pre-wrap;margin-top:6px}
.top{display:flex;justify-content:space-between;align-items:center}
.del{color:var(--ko);border-color:transparent;background:transparent}
details{margin:12px 0}
"""

JS = r"""
const KEY = "resenas_propias_v1";
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; } };
let rows = load();
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(rows)); } catch (e) {} };
const nextId = () => { let n = 1; const ids = new Set(rows.map(r => r.id)); while (ids.has("p" + String(n).padStart(2, "0"))) n++; return "p" + String(n).padStart(2, "0"); };
const count = () => { const n = rows.filter(r => r.text.trim()).length; return n + (n === 1 ? " reseña" : " reseñas") + " con texto"; };
const esc = s => String(s || "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

function render() {
  const box = document.getElementById("rows");
  box.innerHTML = rows.map((r, i) => `
    <section class="card">
      <div class="top"><b>${esc(r.id)}</b><button class="del" data-del="${i}">Eliminar</button></div>
      <div class="row">
        <div><span class="lab">Hotel</span><select data-i="${i}" data-k="hotel">
          <option value="">Sin ficha</option>
          ${Object.entries(HOTELS).map(([id, h]) => `<option value="${id}" ${r.hotel === id ? "selected" : ""}>${id}</option>`).join("")}
        </select></div>
        <div><span class="lab">Tipo</span><input list="tipos" data-i="${i}" data-k="tipo" value="${esc(r.tipo)}" placeholder="sarcasmo, malsonante…"></div>
        <div><span class="lab">Título (opcional)</span><input data-i="${i}" data-k="title" value="${esc(r.title)}"></div>
      </div>
      <div class="ficha">${r.hotel ? esc(HOTELS[r.hotel].nombre + "\n" + HOTELS[r.hotel].ficha) : "Sin ficha: el sistema no sabrá nada del hotel."}</div>
      <span class="lab">Reseña</span><textarea rows="4" data-i="${i}" data-k="text">${esc(r.text)}</textarea>
      <span class="lab">Qué haría una buena respuesta (escríbelo ANTES de ver el resultado)</span>
      <textarea rows="2" data-i="${i}" data-k="esperado" placeholder="no repetir el insulto; no confirmar que el parking era gratis…">${esc(r.esperado)}</textarea>
    </section>`).join("");
  document.getElementById("count").textContent = count();
}
document.addEventListener("input", e => {
  const t = e.target, i = t.dataset.i;
  if (i === undefined) return;
  rows[i][t.dataset.k] = t.value; save();
  if (t.dataset.k === "hotel") render();
  else document.getElementById("count").textContent = count();
});
document.addEventListener("click", e => {
  const d = e.target.dataset.del;
  if (d !== undefined && confirm("¿Eliminar " + rows[d].id + "?")) { rows.splice(+d, 1); save(); render(); }
});
document.getElementById("add").onclick = () => {
  rows.push({id: nextId(), hotel: "", tipo: "", title: "", text: "", esperado: ""}); save(); render();
  window.scrollTo(0, document.body.scrollHeight);
};
const COLS = ["id", "hotel", "tipo", "title", "text", "esperado"];
const q = s => '"' + String(s || "").replace(/"/g, '""') + '"';
document.getElementById("exp").onclick = () => {
  const lines = [COLS.join(";"), ...rows.filter(r => r.text.trim()).map(r => COLS.map(c => q(r[c])).join(";"))];
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + lines.join("\n") + "\n"], {type: "text/csv;charset=utf-8"}));
  a.download = "resenas_propias.csv"; a.click();
};
function parseCSV(text) {
  const out = []; let row = [], f = "", inq = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inq) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else inq = false; } else f += c; }
    else if (c === '"') inq = true;
    else if (c === ";") { row.push(f); f = ""; }
    else if (c === "\n") { row.push(f); out.push(row); row = []; f = ""; }
    else if (c !== "\r") f += c;
  }
  if (f || row.length) { row.push(f); out.push(row); }
  return out;
}
document.getElementById("imp").onchange = async e => {
  const file = e.target.files[0]; if (!file) return;
  const [head, ...data] = parseCSV((await file.text()).replace(/^﻿/, ""));
  const imported = data.filter(r => r.length > 1).map(r => Object.fromEntries(COLS.map(c => [c, r[head.indexOf(c)] || ""])));
  if (confirm(`¿Sustituir las ${rows.length} reseñas actuales por las ${imported.length} del fichero?`)) { rows = imported; save(); render(); }
  e.target.value = "";
};
if (!rows.length) rows.push({id: "p01", hotel: "", tipo: "", title: "", text: "", esperado: ""});
render();
"""


def main() -> None:
    hotels = {
        h["id"]: {"nombre": f"{h['nombre']} ({h['ciudad']})",
                  "ficha": "\n".join(f"· {k.replace('_', ' ')}: {v}" for k, v in h["servicios"].items())}
        for h in kb.fichas().values()
    }  # fmt: skip
    tipos = "".join(f"<option value='{t}'>" for t in TIPOS)
    doc = (
        "<!doctype html><html lang=es><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Reseñas propias</title><style>{CSS}</style><body>"
        "<header><b>Reseñas propias para la demo</b><span id=count></span>"
        "<button id=add>+ Añadir reseña</button>"
        "<label class=btn>Importar CSV<input id=imp type=file accept='.csv' hidden></label>"
        "<button id=exp class=primary>Descargar resenas_propias.csv</button></header>"
        "<details><summary>Cómo rellenarlo</summary><ul>"
        "<li>Reseñas <b>inventadas</b>: no copies reseñas reales de webs ni pongas datos personales reales.</li>"
        "<li>Elige un hotel para que el sistema tenga su ficha (sale debajo): sirve para provocar "
        "premisas falsas a propósito. «Sin ficha» prueba qué hace sin datos del hotel.</li>"
        "<li>Rellena «Qué haría una buena respuesta» <b>antes</b> de ver el resultado: así se mide "
        "si acierta sin depender de la opinión de nadie.</li>"
        "<li>Se guarda solo en este navegador. Al terminar, descarga el CSV y guárdalo en "
        "<code>evals/demo/resenas_propias.csv</code> (o dime dónde está).</li></ul></details>"
        f"<datalist id=tipos>{tipos}</datalist><div id=rows></div>"
        f"<script>const HOTELS={json.dumps(hotels, ensure_ascii=False)};{JS}</script></body></html>"
    )
    OUT.write_text(doc, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
