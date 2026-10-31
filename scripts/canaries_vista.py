"""Hoja para escribir canaries manuales (evals/canaries/manuales_v1.json).

Empieza con fallos reales del generador que el juez deja pasar: la respuesta es la real y el criterio
y el motivo son los del autor (p08 sale sin criterio: lo elige él). El resto los escribe él. Guarda
en el navegador y descarga el JSON; se evalúa con `just canaries-manuales`.

Uso: uv run just hoja-canaries
"""
# ruff: noqa: E501  (textos y JS: partirlos los haría menos legibles)

import json
from pathlib import Path

from calibracion_vista import CSS as BASE_CSS
from calibracion_vista import esc

from caso_uso_llm.evals.rubric import criterios
from caso_uso_llm.pipeline import RUBRIC
from caso_uso_llm.rag import kb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "canaries" / "manuales_vista.html"
SEEDS = ROOT / "evals" / "gold" / "semillas_fase4.json"
OWN = ROOT / "results" / "demo_propias.json"
RATINGS = ROOT / "evals" / "demo" / "valoracion_propias.json"
HUMAN_WHY = {
    "v2-adv-culpa-legal": (
        ["sin_culpa"],
        "Debe reconocer la gravedad y mostrar preocupación por el menor, sin admitir responsabilidades legales que aún no se han investigado.",
    ),
    "v2-adv-inyeccion": (
        ["aspecto", "sin_invencion"],
        "La reseña solo dice «estancia normal» y la respuesta habla de «su comentario respecto a la habitación».",
    ),
}

CSS = (
    BASE_CSS
    + """
.grid{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
@media (max-width:800px){.grid{grid-template-columns:1fr}}
label.f{display:block;font-size:.8rem;color:var(--muted);text-transform:uppercase;margin-top:.5rem}
select{font:inherit;padding:.25rem}
.crits label{display:inline-block;margin:.15rem .9rem .15rem 0;cursor:pointer}
.row{display:flex;gap:1rem;flex-wrap:wrap;align-items:center}
button.quit{font:inherit;cursor:pointer}
#err{color:#b3261e;font-weight:600}
"""
)

JS = r"""
const KEY = "canaries_manuales_v1";
let items = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || START; } catch (e) { return START; } })();
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(items)); } catch (e) {} };
const el = (tag, props = {}) => Object.assign(document.createElement(tag), props);
function field(it, key, label, rows) {
  const box = el("div"), t = el("textarea", {rows, value: it[key] || ""});
  box.append(el("label", {className: "f", textContent: label}), t);
  t.addEventListener("input", () => { it[key] = t.value; save(); });
  return box;
}
function render() {
  const root = document.getElementById("list"); root.replaceChildren();
  items.forEach((it, i) => {
    const card = el("section", {className: "card"});
    card.append(el("h2", {textContent: `${i + 1}. ${it.origen === "real" ? "Fallo real" : "Manual"}`}));
    const row = el("div", {className: "row"});
    const clase = el("select"); clase.append(new Option("Canary: respuesta mala", "canary"), new Option("Control: respuesta correcta", "control")); clase.value = it.clase;
    const hotel = el("select"); hotel.append(new Option("Sin ficha", "")); for (const [id, name] of HOTELS) hotel.append(new Option(name, id)); hotel.value = it.hotel || "";
    const quit = el("button", {className: "quit", type: "button", textContent: "Quitar"});
    clase.onchange = () => { it.clase = clase.value; save(); render(); };
    hotel.onchange = () => { it.hotel = hotel.value; save(); };
    quit.onclick = () => { items.splice(i, 1); save(); render(); };
    row.append(clase, hotel, quit); card.append(row);
    const grid = el("div", {className: "grid"});
    grid.append(field(it, "review", "Reseña", 6), field(it, "response", "Respuesta del hotel", 6));
    card.append(grid);
    if (it.clase === "canary") {
      const crits = el("div", {className: "crits"});
      crits.append(el("label", {className: "f", textContent: "Criterios que el juez debe suspender"}));
      for (const [id, name] of CRITERIA) {
        const box = el("input", {type: "checkbox", checked: it.expected_fail.includes(id)}), l = el("label");
        box.onchange = () => { it.expected_fail = it.expected_fail.filter(x => x !== id).concat(box.checked ? [id] : []); save(); };
        l.append(box, " " + name); crits.append(l);
      }
      card.append(crits);
    }
    card.append(field(it, "por_que", "Por qué", 2));
    root.append(card);
  });
  const c = items.filter(x => x.clase === "canary").length;
  document.getElementById("prog").textContent = `${c} canaries · ${items.length - c} controles`;
}
function problems() {
  return items.flatMap((it, i) => {
    const p = [];
    if (!it.review.trim() || !it.response.trim()) p.push(`${i + 1}: falta reseña o respuesta`);
    if (it.clase === "canary" && !it.expected_fail.length) p.push(`${i + 1}: falta el criterio`);
    return p;
  });
}
document.getElementById("add").onclick = () => { items.push({clase: "canary", origen: "manual", hotel: "", review: "", response: "", expected_fail: [], por_que: ""}); save(); render(); };
document.getElementById("exp").onclick = () => {
  const p = problems(); document.getElementById("err").textContent = p.join(" · ");
  if (p.length) return;
  const doc = {description: DESCRIPTION, is_synthetic: true, items: items.map((it, i) => ({id: `man-${String(i + 1).padStart(2, "0")}`, ...it, expected_fail: it.clase === "canary" ? it.expected_fail : []}))};
  const a = el("a", {href: URL.createObjectURL(new Blob([JSON.stringify(doc, null, 1) + "\n"], {type: "application/json"})), download: "manuales_v1.json"});
  a.click();
};
render();
"""


def start_items() -> list[dict]:
    seeds = {it["id"]: it for it in json.loads(SEEDS.read_text(encoding="utf-8"))["items"]}
    items = [
        {"clase": "canary", "origen": "real", "hotel": "", "review": seeds[i]["review"],
         "response": seeds[i]["response"], "expected_fail": crit, "por_que": why}
        for i, (crit, why) in HUMAN_WHY.items()
    ]  # fmt: skip
    own = next(x for x in json.loads(OWN.read_text(encoding="utf-8")) if x["id"] == "p08")
    why = json.loads(RATINGS.read_text(encoding="utf-8"))["valoraciones"]["p08"]["motivo"]
    return [*items, {"clase": "canary", "origen": "real", "hotel": own["hotel"], "review": own["review"],
                     "response": own["response"], "expected_fail": [], "por_que": why}]  # fmt: skip


def main() -> None:
    hotels = [[k, f"{h['nombre']} ({h['ciudad']})"] for k, h in kb.fichas().items()]
    crit = [[c.id, c.nombre] for c in criterios(RUBRIC)]
    description = "Canaries escritos por el autor, o fallos reales del generador etiquetados por él. SINTÉTICO salvo origen=real."
    data = (f"const START={json.dumps(start_items(), ensure_ascii=False)},HOTELS={json.dumps(hotels, ensure_ascii=False)},"
            f"CRITERIA={json.dumps(crit, ensure_ascii=False)},DESCRIPTION={json.dumps(description, ensure_ascii=False)};")  # fmt: skip
    help_text = "Canary: una respuesta mala que el juez debe suspender. Control: una correcta, aunque incómoda, que no debe suspender. Mejor un fallo sutil y parecido a los reales que uno obvio. Sin datos de personas reales."
    doc = (
        "<!doctype html><html lang=es><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Canaries manuales</title><style>{CSS}</style><body>"
        "<header><b>Canaries manuales</b><span id=prog></span>"
        "<button class=main id=add type=button>Añadir canary</button>"
        "<button class=main id=exp type=button>Descargar manuales_v1.json</button><span id=err></span></header>"
        f"<p>{esc(help_text)}</p><div id=list></div>"
        f"<script>{data.replace('</', '<' + chr(92) + '/')}{JS}</script></body></html>"
    )
    OUT.write_text(doc, encoding="utf-8", newline="\n")
    print(OUT)


if __name__ == "__main__":
    main()
