"""Demo en modo repetición: reseñas ya evaluadas y contestadas, paso a paso.

No ejecuta ningún modelo: muestra lo que produjo el pipeline completo (clasificador mRoBERTa,
RAG, generador Qwen 27B, comprobaciones y juez Gemma 12B), ejecutado antes en local sobre una
GPU AMD. Solo necesita Gradio y `casos.json` (scripts/build_replay.py). Para probar reseñas
nuevas, quien la ve pide una prueba en vivo por LinkedIn y se arranca `just app-live`.

Uso: python demo_replay/app.py     # http://127.0.0.1:7861
"""

import json
from pathlib import Path

import gradio as gr

DATA = json.loads((Path(__file__).parent / "casos.json").read_text(encoding="utf-8"))
CASES = {c["id"]: c for c in DATA["casos"]}
REPO = "https://github.com/JaviRomano/Spanish-hotel-review-LLM"
# Perfil para pedir la prueba en vivo
LINKEDIN = "https://www.linkedin.com/in/franciscojavier-fernandezrumi/"
CONTACT = f"[Escríbeme por LinkedIn]({LINKEDIN})"

INTRO = f"""# ¿Cómo responde una IA a las reseñas difíciles de un hotel?

Reseñas ya evaluadas y contestadas por el sistema. Para cada una: **qué respondió**, **si la
publicaría o la pasaría a una persona** y por qué.

- **Reseñas propias:** escritas a propósito para ponerlo a prueba (amenazas legales,
  instrucciones ocultas, datos falsos, ataques al personal…), con **qué se esperaba** escrito
  *antes* de generar.
- **Selección de la demostración:** casos sintéticos y reseñas reales (TripAdvisor, corpus AHR),
  con una nota escrita *después* de leer la respuesta. Incluye fallos que el sistema no detecta.

Todo se generó **en local, sobre una GPU AMD**: clasificador mRoBERTa → contexto del hotel (RAG)
→ borrador con Qwen 27B → comprobaciones y un segundo modelo como juez. Los hoteles son ficticios.
[Código, informes y cifras]({REPO})."""

LIVE = f"""> 🔬 **Esto es una repetición: aquí no se genera nada en directo.**
> ¿Quieres probarlo con tus propias reseñas? {CONTACT} con
> «Prueba en vivo» y cuándo te viene bien. Arranco el sistema en mi ordenador y te paso un enlace y
> una contraseña. Cada reseña tarda alrededor de un minuto (una sola GPU), y lo que escribas se
> guarda solo para evaluar el sistema, sin tu nombre."""

GROUPS = {
    "Reseñas propias": "Propia",
    "Casos sintéticos": "Sintético",
    "Reseñas reales (AHR)": "Real",
}


def label(c: dict) -> str:
    icon = "✅" if c["decision"] == "publicable" else "👤"
    group = GROUPS.get(c["grupo"], c["grupo"])
    return f"{icon} {group} · {c['id']}" + (f" · {c['tipo']}" if c["tipo"] else "")


def context(c: dict) -> str:
    if c["esperado"]:
        return (
            "**Qué se esperaba de una buena respuesta** (escrito antes de generar)\n\n"
            + c["esperado"]
        )
    if c["nota"]:
        return "**Por qué está aquí** (nota escrita después de leer la respuesta)\n\n" + c["nota"]
    return ""


def show(case_id: str | None):
    c = CASES.get(case_id)
    if c is None:
        return ("",) * 5
    review = f"**{c['hotel']}**\n\n> " + c["review"].replace("\n", "\n> ")
    expected = context(c)
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


with gr.Blocks(title="Reseñas de hotel · modo repetición") as demo:
    gr.Markdown(INTRO)
    gr.Markdown(LIVE)
    options = [(label(c), c["id"]) for c in DATA["casos"]]
    case = gr.Dropdown(
        options, value=options[0][1], label="Reseña (✅ se publica · 👤 pasa a una persona)"
    )
    with gr.Row():
        with gr.Column():
            review = gr.Markdown(label="Reseña")
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
