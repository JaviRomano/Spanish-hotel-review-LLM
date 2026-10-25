"""Demo en modo recogida: solo el formulario, sin modelos (ni GPU ni clasificador).

Las personas envían su reseña con nick y consentimiento y se guarda, ya normalizada y con los
datos personales enmascarados, en data/live/resenas_recogidas.jsonl (fuera de git). No se genera
ninguna respuesta: se procesan después, en lote, cuando haya suficientes:

    uv run python -m caso_uso_llm.pipeline --jsonl data/live/resenas_recogidas.jsonl \
        --prompt v8 --out data/live/recogidas_v8.json

Sin cola ni JSON a la vista: quien escribe solo ve el formulario y la confirmación. La palabra
clave de apagado (DEMO_KILL) cierra la app y el túnel, como en app.py.

Uso: uv run just recoger   (sin contraseña: no hay modelos ni datos que proteger; con --auth,
DEMO_USER y DEMO_PASS)
"""

import json
import re
import threading
from datetime import datetime

import gradio as gr

from caso_uso_llm.data.normalize import mask_pii, normalize_text
from caso_uso_llm.log import log
from caso_uso_llm.paths import DATA
from caso_uso_llm.rag import kb

OUT = DATA / "live" / "resenas_recogidas.jsonl"
NICK = re.compile(r"^[\w.\-]{2,30}$")
CONSENT = (
    "Acepto que mi reseña (con mi nick, no mi nombre) se guarde para evaluar y mejorar el sistema. "
    "No incluyas datos personales: nombres reales, teléfonos ni correos."
)
NO_HOTEL = "Sin ficha (hotel no registrado)"
HOTELS = {f"{h['id']} · {h['nombre']} ({h['ciudad']})": h["id"] for h in kb.fichas().values()}
_LOCK = threading.Lock()


def shutdown() -> None:
    """Apaga a distancia: cierra el túnel (salvo DEMO_KILL_TUNNEL=0) y sale."""
    import os
    import subprocess
    import time

    time.sleep(3)  # deja que el aviso llegue al navegador
    if os.environ.get("DEMO_KILL_TUNNEL", "1") != "0":
        subprocess.run(["taskkill", "/IM", "cloudflared.exe", "/F"], capture_output=True)
        log("Túnel de Cloudflare cerrado")
    log("Recogida apagada a distancia")
    os._exit(0)


def is_kill(text: str) -> bool:
    import os

    kill = os.environ.get("DEMO_KILL", "").strip().lower()
    return bool(kill) and text.strip().lower() == kill


def submit(nick: str, consent: bool, hotel_label: str, title: str, text: str):
    if is_kill(text):  # no se guarda como reseña
        threading.Thread(target=shutdown, daemon=True).start()
        return "### 🔌 Recogida cerrada\nEl enlace deja de funcionar.", title, text
    nick = nick.strip()
    if not NICK.match(nick):
        raise gr.Error("Escribe un nick de 2 a 30 caracteres (letras, números, punto, guion o _).")
    if not consent:
        raise gr.Error("Para enviar la reseña hay que aceptar que se guarde.")
    if not text.strip():
        raise gr.Error("Escribe o pega una reseña.")
    now = datetime.now()
    row = {
        "id": f"rec-{now:%Y%m%d-%H%M%S-%f}"[:-3], "fecha": now.isoformat(timespec="seconds"),
        "nick": nick, "origen": "recogida: escrita por una persona", "consentimiento": True,
        "hotel": HOTELS.get(hotel_label),
        "title": mask_pii(normalize_text(title))[0].strip(),
        "text": mask_pii(normalize_text(text))[0],
    }  # fmt: skip
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, OUT.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log(f"Reseña recibida de {nick} ({row['id']})")
    return "✅ **Reseña recibida. ¡Gracias!** Puedes enviar otra.", "", ""


def build() -> gr.Blocks:
    with gr.Blocks(title="LLM de respuesta a reseñas - JR0mano") as demo:
        gr.Markdown(
            "# LLM de respuesta a reseñas de hotel\nPipeline local: clasificador mRoBERTa, RAG con "
            "la ficha del hotel, generador Qwen 27B, guardarraíles y juez Gemma 12B. Los datos de "
            "hoteles son ficticios.\n\nEstoy recogiendo reseñas para entrenar el LLM: escribe la "
            "tuya y se guardará para responderla más adelante."
        )
        hotel = gr.Dropdown([*HOTELS, NO_HOTEL], value=next(iter(HOTELS)), label="Hotel")
        nick = gr.Textbox(label="Tu nick (no tu nombre)", max_lines=1)
        title = gr.Textbox(label="Título (opcional)")
        text = gr.Textbox(label="Reseña", lines=8)
        consent = gr.Checkbox(label=CONSENT, value=False)
        go = gr.Button("Enviar reseña", variant="primary")
        status = gr.Markdown()
        go.click(submit, [nick, consent, hotel, title, text], [status, title, text])
    return demo


def main() -> None:
    import argparse
    import ctypes
    import os
    import sys

    ap = argparse.ArgumentParser()
    ap.add_argument("--auth", action="store_true", help="contraseña (DEMO_USER y DEMO_PASS)")
    ap.add_argument("--port", type=int, default=7860)
    args = ap.parse_args()
    auth = None
    if args.auth:
        user, password = os.environ.get("DEMO_USER"), os.environ.get("DEMO_PASS")
        if not (user and password):
            raise SystemExit("Con --auth hacen falta DEMO_USER y DEMO_PASS.")
        auth = (user, password)
    if sys.platform == "win32":  # como app.keep_awake (importar app cargaría el clasificador)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    build().launch(server_name="127.0.0.1", server_port=args.port, auth=auth, max_threads=4)


if __name__ == "__main__":
    main()
