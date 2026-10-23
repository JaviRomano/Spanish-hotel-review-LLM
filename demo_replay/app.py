"""Demo en modo repetición: respuestas a reseñas de hotel generadas antes, en local, por el pipeline.

No ejecuta ningún modelo: muestra lo que produjo cada paso (clasificador mRoBERTa, RAG,
generador Qwen 27B, comprobaciones y juez Gemma 12B) para cada reseña. Solo necesita Gradio y
`casos.json` (generado por scripts/build_replay.py), así que corre en un servidor sin GPU.

Uso: python demo_replay/app.py     # http://127.0.0.1:7861
"""

import json
from pathlib import Path

import gradio as gr

DATA = json.loads((Path(__file__).parent / "casos.json").read_text(encoding="utf-8"))
CASES = {c["id"]: c for c in DATA["casos"]}
GROUPS = ["Todas", *dict.fromkeys(c["grupo"] for c in DATA["casos"])]
REPO = "https://github.com/JaviRomano/Spanish-hotel-review-LLM"

INTRO = f"""# Respuestas a reseñas de hotel · modo repetición

Cada reseña pasó por el pipeline completo **en local, sobre una GPU AMD**: clasificador mRoBERTa
→ RAG con la ficha del hotel, políticas y respuestas aprobadas → borrador con Qwen 27B →
comprobaciones y juez Gemma 12B → **publicar o pasar a una persona**.
Aquí **no se genera nada en directo**: ves las salidas reales que produjo el sistema.
Los hoteles y sus fichas son ficticios. [Código, informes y cifras]({REPO})."""

FOOTER = (
    "Reseñas reales del corpus *Andalusian Hotels' Reviews* (CC BY-NC 4.0), con los datos "
    "personales enmascarados. Casos sintéticos y reseñas propias escritos para probar el sistema."
)


def label(c: dict) -> str:
    icon = "✅" if c["decision"] == "publicable" else "👤"
    tipo = f" · {c['tipo']}" if c["tipo"] else ""
    return f"{icon} {c['id']}{tipo}"


def choices(group: str) -> list[tuple[str, str]]:
    return [(label(c), c["id"]) for c in DATA["casos"] if group in ("Todas", c["grupo"])]


def filter_cases(group: str):
    opts = choices(group)
    return gr.update(choices=opts, value=opts[0][1] if opts else None)


def show(case_id: str | None):
    c = CASES.get(case_id)
    if c is None:
        return ("",) * 6
    if c["decision"] == "publicable":
        decision = "### ✅ Se publicaría sin revisión"
    else:
        decision = "### 👤 Pasa a revisión humana\n" + "\n".join(f"- {r}" for r in c["reasons"])
    probs = " · ".join(f"{k} {v:.2f}" for k, v in c["probs"].items())
    decision += (
        f"\n\n**Sentimiento:** {c['sentiment']} (confianza {c['confidence']:.2f}, umbral "
        f"{DATA['umbral']}) — {probs}"
    )
    if c["esperado"]:
        decision += f"\n\n**Qué se esperaba (escrito antes de generar):** {c['esperado']}"
    review = f"**{c['grupo']}** · {c['hotel']}\n\n> " + c["review"].replace("\n", "\n> ")
    judge = "\n".join(
        f"- {'✅' if j['cumple'] else '❌'} {j['criterio']}"
        + ("" if j["cumple"] else f": «{j['evidencia']}»")
        for j in c["judge"]
    )
    context = (
        "**Políticas recuperadas:** " + (", ".join(c["politicas"]) or "—")
        + "\n\n**Peticiones detectadas:** " + (", ".join(c["peticiones"]) or "ninguna")
        + "\n\n**Aspectos (cita literal de la reseña):**\n"
        + "\n".join(f"- {a['categoria']} · {a['polaridad']}: «{a['cita']}»" for a in c["aspectos"])
    )  # fmt: skip
    ficha = f"```\n{c['ficha']}\n```" if c["ficha"] else "Sin ficha: el hotel no está registrado."
    return review, decision, c["response"] or "(sin respuesta)", judge, context, ficha


with gr.Blocks(title="Reseñas de hotel · modo repetición") as demo:
    gr.Markdown(INTRO)
    with gr.Row():
        group = gr.Dropdown(GROUPS, value=GROUPS[0], label="Conjunto", scale=1)
        first = choices(GROUPS[0])
        case = gr.Dropdown(
            first, value=first[0][1], label="Reseña (✅ publicable · 👤 revisión)", scale=3
        )
    with gr.Row():
        with gr.Column():
            review = gr.Markdown()
            decision = gr.Markdown()
        with gr.Column():
            response = gr.Textbox(label="Borrador generado", lines=12, interactive=False)
    with gr.Accordion("Juez (8 criterios, con cita como evidencia de cada suspenso)", open=True):
        judge = gr.Markdown()
    with gr.Accordion("Contexto y análisis", open=False):
        context = gr.Markdown()
    with gr.Accordion("Ficha del hotel", open=False):
        ficha = gr.Markdown()
    gr.Markdown(FOOTER)
    outputs = [review, decision, response, judge, context, ficha]
    group.change(filter_cases, group, case)
    case.change(show, case, outputs)
    demo.load(show, case, outputs)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7861)
