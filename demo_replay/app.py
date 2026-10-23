"""Demo en modo repetición: 10 reseñas extremas y lo que respondió el sistema, paso a paso.

No ejecuta ningún modelo: muestra lo que produjo el pipeline completo (clasificador mRoBERTa,
RAG, generador Qwen 27B, comprobaciones y juez Gemma 12B), ejecutado antes en local sobre una
GPU AMD. Solo necesita Gradio y `casos.json` (scripts/build_replay.py), así que corre en un
servidor sin GPU. Para probar reseñas nuevas hay que pedir una sesión en directo.

Uso: python demo_replay/app.py     # http://127.0.0.1:7861
"""

import json
from pathlib import Path

import gradio as gr

DATA = json.loads((Path(__file__).parent / "casos.json").read_text(encoding="utf-8"))
CASES = {c["id"]: c for c in DATA["casos"]}
REPO = "https://github.com/JaviRomano/Spanish-hotel-review-LLM"
CONTACT = "https://github.com/JaviRomano"

INTRO = f"""# ¿Cómo responde una IA a las reseñas difíciles de un hotel?

Diez reseñas escritas a propósito para ponerla a prueba (sarcasmo, insultos, amenazas legales,
instrucciones ocultas, datos falsos…). Para cada una, **qué se esperaba** (escrito antes de
generar), **qué respondió** el sistema y **si la publicaría o la pasaría a una persona**.

Todo se generó **en local, sobre una GPU AMD**: clasificador mRoBERTa → contexto del hotel (RAG)
→ borrador con Qwen 27B → comprobaciones y un segundo modelo como juez. Los hoteles son ficticios.
[Código, informes y cifras]({REPO})."""

LIVE = (
    f"> 🔬 **Esto es una repetición: aquí no se genera nada en directo.** ¿Quieres probarlo con tus "
    f"propias reseñas? [Pide una prueba en vivo]({CONTACT}) y despliego el modelo desde mi ordenador."
)


def label(c: dict) -> str:
    icon = "✅" if c["decision"] == "publicable" else "👤"
    return f"{icon} {c['id']} · {c['tipo']}" if c["tipo"] else f"{icon} {c['id']}"


def show(case_id: str | None):
    c = CASES.get(case_id)
    if c is None:
        return ("",) * 5
    review = f"**{c['hotel']}**\n\n> " + c["review"].replace("\n", "\n> ")
    expected = c["esperado"] or "—"
    if c["decision"] == "publicable":
        decision = "### ✅ Se publicaría sin revisión"
    else:
        decision = "### 👤 Pasa a una persona antes de publicar\n" + "\n".join(
            f"- {r}" for r in c["reasons"]
        )
    passed = sum(j["cumple"] for j in c["judge"])
    judge = f"**Juez: {passed}/{len(c['judge'])} criterios cumplidos**\n\n" + "\n".join(
        f"- {'✅' if j['cumple'] else '❌'} {j['criterio']}"
        + ("" if j["cumple"] else f": «{j['evidencia']}»")
        for j in c["judge"]
    )
    probs = " · ".join(f"{k} {v:.2f}" for k, v in c["probs"].items())
    detail = (
        f"**Sentimiento (clasificador):** {c['sentiment']}, confianza {c['confidence']:.3f} "
        f"(umbral {DATA['umbral']}) — {probs}\n\n"
        "**Políticas recuperadas:** " + (", ".join(c["politicas"]) or "—")
        + "\n\n**Peticiones detectadas:** " + (", ".join(c["peticiones"]) or "ninguna")
        + ("\n\n**Ficha del hotel:**\n```\n" + c["ficha"] + "\n```" if c["ficha"] else "")
    )  # fmt: skip
    return review, expected, c["response"] or "(sin respuesta)", decision, judge + "\n\n" + detail


with gr.Blocks(title="Reseñas difíciles · modo repetición") as demo:
    gr.Markdown(INTRO)
    gr.Markdown(LIVE)
    options = [(label(c), c["id"]) for c in DATA["casos"]]
    case = gr.Dropdown(
        options, value=options[0][1], label="Reseña (✅ se publica · 👤 pasa a una persona)"
    )
    with gr.Row():
        with gr.Column():
            review = gr.Markdown(label="Reseña")
            gr.Markdown("**Qué se esperaba de una buena respuesta**")
            expected = gr.Markdown()
        with gr.Column():
            response = gr.Textbox(label="Respuesta generada", lines=12, interactive=False)
            decision = gr.Markdown()
    with gr.Accordion("Cómo llegó a esa decisión (juez, clasificador, contexto)", open=False):
        detail = gr.Markdown()
    outputs = [review, expected, response, decision, detail]
    case.change(show, case, outputs)
    demo.load(show, case, outputs)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7861)
