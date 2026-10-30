"""Comparación a ciegas de dos versiones del prompt sobre las mismas reseñas (data/live, fuera de git).

`hoja`: para cada reseña, las dos respuestas como A y B en orden aleatorio (semilla fija) y con
ids opacos; la persona elige la mejor (o empate) y marca si publicaría cada una tal cual. La hoja
no lleva ninguna pista de la versión: la correspondencia va aparte, en <tag>_mapa.json (no
abrirlo antes de terminar). Guarda en el navegador y exporta <tag>.csv; servida con
scripts/servir_notas.py, guarda también en el PC (para valorar desde el móvil).

`resultado`: une el CSV con el mapa y cuenta victorias por versión, con una prueba de signos
exacta (los empates no cuentan), y cuántas respuestas de cada versión se publicarían tal cual.

Uso: uv run python scripts/comparacion_ciegas.py hoja --a data/live/tandas_01-03_v6.json \
         --b data/live/tandas_01-03_v9.json --resenas data/live/tandas_01-03.jsonl --tag ciegas_t01-03
     uv run python scripts/comparacion_ciegas.py resultado --tag ciegas_t01-03 \
         --informe reports/phase9_ciegas.md
"""
# ruff: noqa: E501  (CSS y JavaScript en línea)

import argparse
import csv
import html
import json
import random
import re
from pathlib import Path

from scipy.stats import binomtest

from caso_uso_llm.seed import DEFAULT_SEED

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "live"

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--bd:#c8c8c8;--card:#f6f6f4;--muted:#5f5f5b;--accent:#2a78d6;--ok:#1f7a3d}
@media (prefers-color-scheme:dark){:root{--bg:#1c1c1b;--fg:#ececea;--bd:#4a4a47;--card:#262625;--muted:#a9a8a2;--accent:#5a9be8;--ok:#5fd18a}}
*{box-sizing:border-box}
body{font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0 auto;max-width:1200px;padding:0 16px 80px}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--bd);padding:10px 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:2}
header b{margin-right:auto}
button{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
.card{background:var(--card);border:1px solid var(--bd);border-left:6px solid var(--bd);border-radius:8px;padding:14px;margin:16px 0}
.card.done{border-left-color:var(--ok)}
.meta{color:var(--muted);font-size:.88rem;margin-bottom:6px}
.review{white-space:pre-wrap;border-left:3px solid var(--bd);padding:6px 10px;margin:6px 0 10px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media (max-width:820px){.cols{grid-template-columns:1fr}}
.lab{font-size:.78rem;text-transform:uppercase;color:var(--muted);margin:8px 0 3px}
.resp{white-space:pre-wrap;background:var(--bg);border:1px solid var(--bd);border-radius:6px;padding:10px}
.pick{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0 4px}
label{cursor:pointer}
textarea{width:100%;font:inherit;padding:6px 8px;border:1px solid var(--bd);border-radius:6px;background:var(--bg);color:var(--fg)}
"""

JS = """
const IDS = __IDS__, KEY = "__KEY__";
const st = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } })();
const SERVED = location.protocol.startsWith("http");
let timer = null;
const push = () => { if (SERVED) fetch("estado", {method: "POST", body: JSON.stringify(st)}).catch(() => {}); };
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} clearTimeout(timer); timer = setTimeout(push, 800); };
const get = id => (st[id] = st[id] || {});
function paint() {
  let n = 0;
  for (const id of IDS) { const done = !!get(id).preferida; if (done) n++; document.getElementById("c-" + id).classList.toggle("done", done); }
  document.getElementById("prog").textContent = n + " de " + IDS.length + " comparadas";
}
document.addEventListener("change", e => {
  const t = e.target, id = t.dataset.id; if (!id) return;
  get(id)[t.dataset.k] = t.type === "checkbox" ? t.checked : t.value; save(); paint();
});
document.addEventListener("input", e => { const t = e.target; if (t.tagName === "TEXTAREA") { get(t.dataset.id).notas = t.value; save(); } });
function fill() { for (const id of IDS) { const s = get(id);
  document.querySelectorAll(`[data-id="${id}"]`).forEach(el => {
    if (el.type === "radio") el.checked = s.preferida === el.value;
    else if (el.type === "checkbox") el.checked = !!s[el.dataset.k];
    else if (el.tagName === "TEXTAREA") el.value = s.notas || "";
  }); } }
const q = s => '"' + String(s ?? "").replace(/"/g, '""') + '"';
document.getElementById("exp").onclick = () => {
  const L = ["id;preferida;a_publicable;b_publicable;notas"];
  for (const id of IDS) { const s = get(id); L.push([q(id), q(s.preferida), s.a_pub ? 1 : 0, s.b_pub ? 1 : 0, q(s.notas)].join(";")); }
  const out = "\\ufeff" + L.join("\\n") + "\\n";
  if (SERVED) { fetch("csv", {method: "POST", body: out}).then(r => alert(r.ok ? "Guardado en el PC (__CSV__)." : "No se pudo guardar en el PC.")).catch(() => alert("No se pudo guardar en el PC.")); return; }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([out], {type: "text/csv;charset=utf-8"})); a.download = "__CSV__"; a.click();
};
fill(); paint();
if (SERVED) fetch("estado").then(r => r.ok ? r.json() : {}).then(srv => {
  for (const [id, v] of Object.entries(srv || {})) st[id] = Object.assign({}, v, st[id] || {});
  fill(); paint();
}).catch(() => {});
"""


# El saludo delata la versión («Estimado cliente:» en v6, «Hola:»/«Saludos:» en v9) y ya lo decidió
# Javier: se quita de las dos respuestas para comparar solo el cuerpo.
GREETING = re.compile(
    r"^\s*(?:Estimad[oa]s?\b[^\n]*|Hola\s*[:,!]?|Saludos\s*[:,]?)[ \t]*\n+", re.IGNORECASE
)


def body(response: str) -> str:
    return GREETING.sub("", response, count=1)


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def hoja(a_path: Path, b_path: Path, resenas: Path, tag: str) -> None:
    a = {it["id"]: it for it in json.loads(a_path.read_text(encoding="utf-8"))}
    b = {it["id"]: it for it in json.loads(b_path.read_text(encoding="utf-8"))}
    src = {
        r["id"]: r for r in map(json.loads, resenas.read_text(encoding="utf-8").splitlines()) if r
    }
    ids = [i for i in a if i in b and a[i].get("response") and b[i].get("response")]
    rng = random.Random(f"{DEFAULT_SEED}-{tag}")
    rng.shuffle(ids)  # el orden tampoco delata la tanda
    mapa, cards = {}, []
    for n, rid in enumerate(ids, 1):
        opaque = f"c{n:02d}"
        swap = rng.random() < 0.5
        first, second = (b, a) if swap else (a, b)
        mapa[opaque] = {"id": rid, "A": b_path.stem if swap else a_path.stem,
                        "B": a_path.stem if swap else b_path.stem}  # fmt: skip
        r = src.get(rid, {})
        extra = " · ".join(x for x in (f"tipo: {r['tipo']}" if r.get("tipo") else "",
                                       f"esperado: {r['esperado']}" if r.get("esperado") else "") if x)  # fmt: skip
        cards.append(f"""<div class=card id="c-{opaque}">
  <div class=meta>{opaque} · hotel {esc(first[rid].get("hotel") or "sin ficha")}{" · " + esc(extra) if extra else ""}</div>
  <div class=review>{esc((r.get("title") + ". ") if r.get("title") else "")}{esc(r.get("text", first[rid].get("text")))}</div>
  <div class=cols>
    <div><div class=lab>Respuesta A</div><div class=resp>{esc(body(first[rid]["response"]))}</div>
      <label><input type=checkbox data-id={opaque} data-k=a_pub> La publicaría tal cual</label></div>
    <div><div class=lab>Respuesta B</div><div class=resp>{esc(body(second[rid]["response"]))}</div>
      <label><input type=checkbox data-id={opaque} data-k=b_pub> La publicaría tal cual</label></div>
  </div>
  <div class=pick>¿Cuál es mejor?
    <label><input type=radio name=p-{opaque} value=A data-id={opaque} data-k=preferida> A</label>
    <label><input type=radio name=p-{opaque} value=B data-id={opaque} data-k=preferida> B</label>
    <label><input type=radio name=p-{opaque} value=empate data-id={opaque} data-k=preferida> Empate</label>
  </div>
  <div class=lab>Notas (opcional)</div><textarea rows=2 data-id={opaque}></textarea>
</div>""")
    csv_name = f"{tag}.csv"
    js = (JS.replace("__IDS__", json.dumps(list(mapa))).replace("__KEY__", f"ciegas_{tag}")
          .replace("__CSV__", csv_name))  # fmt: skip
    page = (
        "<!doctype html><html lang=es><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Comparación a ciegas</title><style>{CSS}</style></head><body>"
        f"<header><b>Comparación a ciegas · {len(mapa)} reseñas</b><span id=prog></span>"
        f"<button id=exp>Exportar {csv_name}</button></header>"
        "<p class=meta>Cada reseña tiene dos respuestas de versiones distintas del sistema, en orden "
        "aleatorio. Elige la mejor (o empate) y marca las que publicarías tal cual. No hace falta "
        "justificar; las notas ayudan si algo destaca.</p>"
        + "".join(cards)
        + f"<script>{js}</script></body></html>"
    )
    (LIVE / f"{tag}.html").write_text(page, encoding="utf-8", newline="\n")
    (LIVE / f"{tag}_mapa.json").write_text(json.dumps(mapa, ensure_ascii=False, indent=1) + "\n",
                                           encoding="utf-8", newline="\n")  # fmt: skip
    print(f"Hoja: {LIVE / f'{tag}.html'} ({len(mapa)} reseñas) · mapa aparte: {tag}_mapa.json")


def resultado(tag: str, informe: Path | None = None) -> None:
    mapa = json.loads((LIVE / f"{tag}_mapa.json").read_text(encoding="utf-8"))
    with open(LIVE / f"{tag}.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    versions = sorted({m["A"] for m in mapa.values()} | {m["B"] for m in mapa.values()})
    wins = dict.fromkeys(versions, 0) | {"empate": 0}
    pub = dict.fromkeys(versions, 0)
    both = done = 0
    for r in rows:
        m = mapa[r["id"]]
        if r["preferida"]:
            done += 1
            wins["empate" if r["preferida"] == "empate" else m[r["preferida"]]] += 1
        pub[m["A"]] += r["a_publicable"] == "1"
        pub[m["B"]] += r["b_publicable"] == "1"
        both += r["a_publicable"] == "1" and r["b_publicable"] == "1"
    v1, v2 = versions
    decided = wins[v1] + wins[v2]
    p = binomtest(wins[v2], decided, 0.5).pvalue if decided else float("nan")
    print(f"Comparadas: {done} de {len(mapa)}")
    print(f"Gana {v1}: {wins[v1]} · gana {v2}: {wins[v2]} · empate: {wins['empate']}")
    print(f"Prueba de signos (sin empates, bilateral): p = {p:.3f}")
    print(f"Publicables tal cual: {v1} {pub[v1]}/{len(mapa)} · {v2} {pub[v2]}/{len(mapa)}")
    if informe:
        n = len(mapa)
        lines = [
            "# Fase 9 · Comparación humana a ciegas de dos versiones del prompt",
            "",
            f"Generado por `uv run python scripts/comparacion_ciegas.py resultado --tag {tag} "
            f"--informe {informe.relative_to(ROOT).as_posix()}`. No editar a mano.",
            "",
            f"- {n} reseñas nuevas escritas a mano (no son casos de desarrollo), respondidas con las "
            "dos versiones en las mismas condiciones. Las reseñas, las respuestas y las valoraciones "
            "quedan fuera de git (`data/live/`): aquí solo van los recuentos.",
            "- Valora una persona. Cada reseña muestra las dos respuestas como A y B en orden "
            "aleatorio, con ids opacos y sin el saludo (delataba la versión).",
            "",
            f"| | {v1} | {v2} |",
            "|---|---|---|",
            f"| Preferida | {wins[v1]} | {wins[v2]} |",
            f"| Publicable tal cual | {pub[v1]}/{n} | {pub[v2]}/{n} |",
            "",
            f"- Empates: {wins['empate']}; sin valorar: {n - done}. Publicables las dos: {both}.",
            f"- Prueba de signos exacta (bilateral, sin empates): p = {p:.2f}. Con {decided} "
            "comparaciones decididas, solo una preferencia muy clara sería significativa por sí sola.",
            "",
        ]
        informe.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"Informe: {informe}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hoja")
    h.add_argument("--a", type=Path, required=True)
    h.add_argument("--b", type=Path, required=True)
    h.add_argument("--resenas", type=Path, required=True)
    h.add_argument("--tag", required=True)
    r = sub.add_parser("resultado")
    r.add_argument("--tag", required=True)
    r.add_argument("--informe", type=Path, help="escribe los recuentos en reports/ (sin textos)")
    args = ap.parse_args()
    if args.cmd == "hoja":
        hoja(ROOT / args.a, ROOT / args.b, ROOT / args.resenas, args.tag)
    else:
        resultado(args.tag, ROOT / args.informe if args.informe else None)


if __name__ == "__main__":
    main()
