"""Equivalencia de extremo a extremo del juez asíncrono (Bloque 2): generate_stage + judge_stage
sobre los 54 casos de la demostración, con la caché de resultados, frente al destino y los motivos
que daba `run()` ANTES de partirlo en dos fases.

La referencia (tests/data/destinos_run_d6b55fc.json) se obtuvo ejecutando el `run()` del commit
d6b55fc con estas mismas cachés. No se compara con results/pipeline_cola.json: la cola se generó
el 2026-10-23, antes de los guardarraíles de la Fase 9 y del cambio de kb/ de limpieza, y ya no
refleja el pipeline actual (42 de 54 casos cambian de respuesta o de motivos).

Necesita los pesos de mRoBERTa y Ollama (require_gpu carga los modelos aunque todas las
respuestas salgan de la caché): solo en local, se salta en CI. Tarda unos minutos.
"""

import json
import urllib.request
from pathlib import Path

import pytest

REFERENCE = Path(__file__).parent / "data" / "destinos_run_d6b55fc.json"
# Cambios deliberados posteriores a la referencia: id -> por qué. Solo pueden cambiar estos.
# - Antitrampa en el modelo base (2026-10-29): la inyección de prompt se detecta como trampa
#   (respuesta irónica; sigue yendo a revisión, con ese único motivo).
EXPECTED_CHANGES = {"adv-inyeccion": "trampa"}
# - Accidente o riesgo legal (2026-10-30): motivo nuevo cuando la reseña lo menciona. Solo se
#   añade ese motivo; el destino y el resto de motivos no cambian.
INCIDENT = "accidente o riesgo legal"


def _ollama() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=2)
        return True
    except OSError:
        return False


def _weights() -> bool:
    try:
        from caso_uso_llm.classify.finetune import SEEDS, Config, model_dir
    except ImportError:  # sin torch
        return False
    return all((model_dir(Config(), "A", s) / "model.safetensors").exists() for s in SEEDS)


@pytest.mark.skipif(not (_weights() and _ollama()), reason="sin pesos de mRoBERTa u Ollama")
def test_dos_fases_dan_el_mismo_destino_y_motivos_que_run_antes_del_bloque_2():
    from caso_uso_llm.generate import run as gen
    from caso_uso_llm.pipeline import PENDING, PUBLISH, QUEUE, generate_stage, judge_stage

    calls = []
    real_chat = gen.chat
    gen.chat = lambda *a, **k: calls.append(1) or real_chat(*a, **k)  # debe salir todo de la caché
    try:
        cola = json.loads(QUEUE.read_text(encoding="utf-8"))
        items = [{k: c[k] for k in ("id", "hotel", "text", "meta") if k in c}
                 | {"title": c.get("title", "")} for c in cola]  # fmt: skip
        out = generate_stage(items)
        assert all(it["decision"] != PUBLISH for it in out)  # nada publicable antes del juez
        assert sum(it["decision"] == PENDING for it in out) > 0
        out = judge_stage(out)
    finally:
        gen.chat = real_chat
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    assert calls == [], "alguna llamada al generador no salió de la caché: la referencia no vale"
    for ref, it in zip(reference, out, strict=True):
        assert ref["id"] == it["id"]
        if it["id"] in EXPECTED_CHANGES:
            assert it.get("genuina") is False and it["decision"] == ref["decision"], it["id"]
            continue
        reasons = [r for r in it["reasons"] if r != INCIDENT]
        assert (INCIDENT in it["reasons"]) == bool(it["checks"].get("incidente")), it["id"]
        assert (it["decision"], reasons) == (ref["decision"], ref["reasons"]), it["id"]
