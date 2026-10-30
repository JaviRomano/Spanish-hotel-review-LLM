"""Formulario HTML para escribir reseñas a mano en tandas de 10 (data/live/formulario_tandas.html).

Cada reseña: quién la escribe (nick), hotel (con lo que dice su ficha), fecha de la reseña,
título, texto y, opcionalmente, tipo y qué se espera de una buena respuesta (no llegan a los
modelos). Guarda el progreso en el navegador, avisa de textos repetidos y exporta cada tanda como
resenas_tanda_NN.jsonl con el formato que lee `just pipeline --jsonl` (el mismo que recoger.py);
también importa una tanda ya exportada para seguir con ella. Los datos personales se enmascaran
al procesarlas (classify.infer.prepare), no aquí.

Las tandas son reseñas NUEVAS para validar v9 sin sobreajuste: no las ha visto ningún prompt.

Uso: uv run python scripts/formulario_tandas.py
     -> abrir data/live/formulario_tandas.html; dejar los .jsonl exportados en data/live/
     uv run just pipeline --jsonl data/live/resenas_tanda_01.jsonl --prompt v9 --out data/live/tanda_01_v9.json
"""
# ruff: noqa: E501  (CSS y JavaScript en línea)

import json
from pathlib import Path

from caso_uso_llm.rag import kb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "live" / "formulario_tandas.html"
PER_BATCH = 10

TIPOS = [
    "positiva", "neutral", "negativa", "mixta (elogios y queja)", "sarcasmo", "incidente grave",
    "pide compensación", "premisa falsa", "acusación al personal", "dialecto o jerga",
    "muy corta", "muy larga", "trampa o broma", "fuera de tema",
]  # fmt: skip

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--bd:#c8c8c8;--card:#f6f6f4;--muted:#5f5f5b;--accent:#2a78d6;--ok:#1f7a3d;--ko:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#1c1c1b;--fg:#ececea;--bd:#4a4a47;--card:#262625;--muted:#a9a8a2;--accent:#5a9be8;--ok:#5fd18a;--ko:#ff8a80}}
*{box-sizing:border-box}
body{font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0 auto;max-width:1100px;padding:0 16px 80px}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--bd);padding:10px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center;z-index:2}
header b{margin-right:auto}
button,label.btn,select.tanda{font:inherit;padding:6px 12px;border:1px solid var(--bd);border-radius:6px;background:var(--card);color:var(--fg);cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.prog{font-size:.9rem;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--bd);border-left:6px solid var(--bd);border-radius:8px;padding:12px;margin:14px 0}
.card.done{border-left-color:var(--ok)}.card.dup{border-left-color:var(--ko)}
.num{font-weight:600;margin-bottom:4px}
.row{display:grid;grid-template-columns:1fr 1.4fr 160px;gap:10px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media (max-width:760px){.row,.row2{grid-template-columns:1fr}}
.lab{display:block;font-size:.8rem;color:var(--muted);margin:8px 0 3px}
input,select,textarea{width:100%;font:inherit;padding:6px 8px;border:1px solid var(--bd);border-radius:6px;background:var(--bg);color:var(--fg)}
textarea{resize:vertical}
.ficha{font-size:.82rem;color:var(--muted);white-space:pre-wrap;margin-top:4px}
.warn{color:var(--ko);font-size:.85rem;margin-top:4px}
details{margin:12px 0}summary{cursor:pointer}
"""

JS = """
const HOTELS = __HOTELS__, TIPOS = __TIPOS__, PER = __PER__, KEY = "formulario_tandas_v1";
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
let state = load(); state.tandas = state.tandas || {"1": []}; state.actual = state.actual || "1";
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };
const today = () => new Date().toISOString().slice(0, 10);
const blank = () => ({nick: state.nick || "", hotel: Object.keys(HOTELS)[0], fecha: today(), title: "", text: "", tipo: "", esperado: ""});
const rows = () => { const t = state.tandas[state.actual]; while (t.length < PER) t.push(blank()); return t; };
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const norm = s => s.toLowerCase().replace(/\\s+/g, " ").trim();

function allTexts() {  // textos de todas las tandas, para avisar de repetidos
  const seen = {};
  for (const [n, t] of Object.entries(state.tandas)) t.forEach((r, i) => { if (r.text.trim()) (seen[norm(r.text)] ||= []).push(`${n}.${i + 1}`); });
  return seen;
}

function render() {
  const sel = document.getElementById("tanda");
  sel.innerHTML = Object.keys(state.tandas).map(n => `<option ${n === state.actual ? "selected" : ""}>${n}</option>`).join("");
  const seen = allTexts(), t = rows();
  document.getElementById("list").innerHTML = t.map((r, i) => {
    const dup = r.text.trim() && seen[norm(r.text)].length > 1;
    const h = HOTELS[r.hotel];
    return `<div class="card ${dup ? "dup" : r.text.trim() ? "done" : ""}" data-i="${i}">
      <div class=num>Reseña ${state.actual}.${i + 1}</div>
      <div class=row>
        <div><span class=lab>Quién la escribe (nick, no el nombre)</span><input data-f=nick value="${esc(r.nick)}"></div>
        <div><span class=lab>Hotel</span><select data-f=hotel>${Object.keys(HOTELS).map(k => `<option value="${esc(k)}" ${k === r.hotel ? "selected" : ""}>${esc(HOTELS[k].label)}</option>`).join("")}</select></div>
        <div><span class=lab>Fecha de la reseña</span><input type=date data-f=fecha value="${esc(r.fecha)}"></div>
      </div>
      ${h.ficha ? `<details><summary>Ficha del hotel</summary><div class=ficha>${esc(h.ficha)}</div></details>` : ""}
      <span class=lab>Título (opcional)</span><input data-f=title value="${esc(r.title)}">
      <span class=lab>Reseña</span><textarea data-f=text rows=5>${esc(r.text)}</textarea>
      ${dup ? `<div class=warn>Texto repetido en: ${seen[norm(r.text)].join(", ")}</div>` : ""}
      <div class=row2>
        <div><span class=lab>Tipo (opcional, no llega al modelo)</span><select data-f=tipo><option></option>${TIPOS.map(x => `<option ${x === r.tipo ? "selected" : ""}>${x}</option>`).join("")}</select></div>
        <div><span class=lab>Qué esperas de una buena respuesta (opcional, no llega al modelo)</span><input data-f=esperado value="${esc(r.esperado)}"></div>
      </div></div>`;
  }).join("");
  const done = t.filter(r => r.text.trim()).length;
  document.getElementById("prog").textContent = `Tanda ${state.actual}: ${done}/${PER}`;
}

document.addEventListener("input", e => {
  const f = e.target.dataset.f; if (!f) return;
  const i = +e.target.closest(".card").dataset.i, r = rows()[i];
  r[f] = e.target.value;
  if (f === "nick") state.nick = e.target.value;
  save();
  if (f === "hotel" || f === "tipo") render(); else {
    const done = rows().filter(x => x.text.trim()).length;
    document.getElementById("prog").textContent = `Tanda ${state.actual}: ${done}/${PER}`;
    e.target.closest(".card").classList.toggle("done", !!r.text.trim());
  }
});
document.addEventListener("focusout", e => { if (e.target.dataset.f === "text") render(); });
document.getElementById("tanda").onchange = e => { state.actual = e.target.value; save(); render(); };
document.getElementById("nueva").onclick = () => {
  const n = String(Math.max(...Object.keys(state.tandas).map(Number)) + 1);
  state.tandas[n] = []; state.actual = n; save(); render(); window.scrollTo(0, 0);
};

function exportar() {
  const t = rows(), seen = allTexts(), n = String(state.actual).padStart(2, "0");
  const ok = t.filter(r => r.text.trim());
  if (!ok.length) return alert("La tanda no tiene ninguna reseña con texto.");
  const sinNick = ok.filter(r => !/^[\\w.\\-]{2,30}$/.test(r.nick.trim())).length;
  if (sinNick) return alert(`${sinNick} reseña(s) sin nick válido (2 a 30 letras, números, punto, guion o _).`);
  const dups = ok.filter(r => seen[norm(r.text)].length > 1).length;
  if (dups && !confirm(`${dups} reseña(s) tienen el texto repetido. ¿Exportar igualmente?`)) return;
  const lines = ok.map((r, i) => JSON.stringify({
    id: `man-${n}-${String(t.indexOf(r) + 1).padStart(2, "0")}`, fecha: r.fecha || today(), nick: r.nick.trim(),
    origen: "manual: escrita por una persona", consentimiento: true, hotel: HOTELS[r.hotel].id,
    title: r.title.trim(), text: r.text.trim(), tipo: r.tipo, esperado: r.esperado.trim(), tanda: Number(state.actual)}));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\n") + "\\n"], {type: "application/x-ndjson"}));
  a.download = `resenas_tanda_${n}.jsonl`; a.click();
}
document.getElementById("exp").onclick = exportar;

document.getElementById("imp").onchange = async e => {
  const file = e.target.files[0]; if (!file) return;
  const recs = (await file.text()).split("\\n").filter(x => x.trim()).map(x => JSON.parse(x));
  const n = String(recs[0]?.tanda || Math.max(...Object.keys(state.tandas).map(Number)) + 1);
  if (state.tandas[n]?.some(r => r.text.trim()) && !confirm(`La tanda ${n} ya tiene reseñas. ¿Sustituirla?`)) return;
  const byHotel = Object.fromEntries(Object.entries(HOTELS).map(([k, h]) => [h.id, k]));
  state.tandas[n] = recs.map(r => ({nick: r.nick || "", hotel: byHotel[r.hotel] ?? "", fecha: (r.fecha || today()).slice(0, 10),
    title: r.title || "", text: r.text || "", tipo: r.tipo || "", esperado: r.esperado || ""}));
  state.actual = n; save(); render(); e.target.value = "";
};
render();
"""


def main() -> None:
    hotels = {"": {"id": None, "label": "Sin ficha (hotel no registrado)", "ficha": ""}}
    for h in kb.fichas().values():
        hotels[h["id"]] = {"id": h["id"], "label": f"{h['id']} · {h['nombre']} ({h['ciudad']})",
                           "ficha": kb.ficha_texto(h["id"])}  # fmt: skip
    js = (JS.replace("__HOTELS__", json.dumps(hotels, ensure_ascii=False))
          .replace("__TIPOS__", json.dumps(TIPOS, ensure_ascii=False)).replace("__PER__", str(PER_BATCH)))  # fmt: skip
    page = (
        "<!doctype html><html lang=es><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Reseñas en tandas</title><style>{CSS}</style></head><body>"
        "<header><b>Reseñas a mano · tandas de 10</b><span id=prog class=prog></span>"
        "<select id=tanda class=tanda title='Tanda'></select><button id=nueva>Nueva tanda</button>"
        "<label class=btn>Importar tanda<input id=imp type=file accept='.jsonl' hidden></label>"
        "<button id=exp class=primary>Exportar tanda (.jsonl)</button></header>"
        "<details><summary>Cómo se usa</summary><ul>"
        "<li>Escribe reseñas como las escribiría un cliente real: con su tono, sus erratas o su "
        "dialecto. Mejor si las escriben personas que no han probado antes la demo.</li>"
        "<li>No pongas datos personales reales (nombres, teléfonos, correos).</li>"
        "<li>«Tipo» y «Qué esperas» sirven para valorar después; no llegan a los modelos.</li>"
        "<li>Se guarda solo en este navegador. Al terminar cada tanda, expórtala y deja el "
        "<code>.jsonl</code> en <code>data/live/</code> (fuera de git). Con «Importar tanda» "
        "se recupera una exportada.</li></ul></details>"
        "<div id=list></div>"
        f"<script>{js}</script></body></html>"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"Formulario: {OUT}")


if __name__ == "__main__":
    main()
