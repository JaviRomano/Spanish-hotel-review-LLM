"""Demo con juez asíncrono (Bloque 2): el borrador se ve antes que el veredicto, nada se guarda ni
se muestra como publicable sin él, y el juez termina aunque se cierre la pestaña.

app.py carga el clasificador al importarse: solo en local (se salta sin pesos o sin gradio). Los
modelos se sustituyen por funciones falsas: no usa la GPU ni escribe en data/live.
"""

import threading

import pytest

from caso_uso_llm.evals.rubric import IDS

CLEAN_CHECKS = {
    "promise": False, "liability": False, "tuteo": False, "dialect": False, "plazo": False,
    "servicio_inexistente": [], "cifra_inventada": [], "contradice": False, "importe": [],
    "nombra_fuente": False, "length_ok": True, "signature_ok": True,
}  # fmt: skip


def _weights() -> bool:
    try:
        import gradio  # noqa: F401

        from caso_uso_llm.classify.finetune import SEEDS, Config, model_dir
    except ImportError:
        return False
    return all((model_dir(Config(), "A", s) / "model.safetensors").exists() for s in SEEDS)


pytestmark = pytest.mark.skipif(not _weights(), reason="sin pesos de mRoBERTa o sin gradio")


@pytest.fixture
def app(monkeypatch, tmp_path):
    from caso_uso_llm import app as app_module

    saved, queued = [], []
    judge_go = threading.Event()

    def fake_generate(items, *a, **k):
        it = {**items[0], "review": items[0]["text"], "sentiment": "positivo", "confidence": 0.93,
              "probs": {"negativo": 0.02, "neutral": 0.05, "positivo": 0.93}, "reasons": [],
              "analysis": {"sentimiento": "positivo", "aspectos": [], "peticiones": []},
              "response": "Gracias por su reseña.", "checks": dict(CLEAN_CHECKS), "genuina": True,
              "politicas": [], "ejemplos": [], "decision": "pendiente de juez"}  # fmt: skip
        return [it]

    def fake_judge(out, *a, **k):
        judge_go.wait(5)  # el juez tarda: la interfaz ya ha mostrado el borrador
        for it in out:
            it["judge"] = {c: {"cumple": True, "evidencia": ""} for c in IDS}
            it["decision"] = "publicable"
        return out

    # Rutas reales a una carpeta temporal: si algo se escapa de los dobles, no llega a data/live
    monkeypatch.setattr(app_module, "LIVE_LOG", tmp_path / "resenas_vivo.jsonl")
    monkeypatch.setattr(app_module, "SESSION_QUEUE", tmp_path / "cola_app.jsonl")
    monkeypatch.setattr(app_module, "DECISIONS", tmp_path / "revision_humana.jsonl")
    monkeypatch.setattr(app_module, "generate_stage", fake_generate)
    monkeypatch.setattr(app_module, "judge_stage", fake_judge)
    monkeypatch.setattr(app_module, "save_live", lambda it, nick: saved.append(it["id"]))
    monkeypatch.setattr(app_module, "_append", lambda path, it: queued.append(it["id"]))
    monkeypatch.setattr(app_module, "is_kill", lambda text: False)
    yield app_module, saved, judge_go
    # El hilo del juez tiene que acabar ANTES de deshacer los dobles: si un test falla a mitad, el
    # hilo seguiría vivo y, al despertar, llamaría a las funciones reales (pasó el 2026-10-29).
    judge_go.set()
    assert app_module._GPU.acquire(timeout=10), "el hilo del juez no terminó"
    app_module._GPU.release()


def test_primero_el_borrador_con_el_juez_pendiente_y_despues_el_veredicto(app):
    app_module, saved, judge_go = app
    gen = app_module.respond("nick_1", True, next(iter(app_module.HOTELS)), "", "Muy bien todo.")
    first = next(gen)
    assert first[3] == "Gracias por su reseña."  # borrador visible
    assert "Pendiente del juez" in first[5] and "Publicable" not in first[5]
    assert saved == []  # nada guardado antes del veredicto
    judge_go.set()
    final = next(gen)
    assert "Publicable sin revisión" in final[5]
    assert saved and not app_module._GPU.locked()


def test_si_se_cierra_la_pestana_el_juez_y_el_guardado_terminan(app):
    app_module, saved, judge_go = app
    gen = app_module.respond("nick_1", True, next(iter(app_module.HOTELS)), "", "Muy bien todo.")
    next(gen)
    gen.close()  # Gradio cancela el generador
    judge_go.set()
    assert app_module._GPU.acquire(timeout=5)  # el hilo del juez terminó y soltó la GPU
    app_module._GPU.release()
    assert len(saved) == 1


def test_no_se_aprueba_desde_la_cola_sin_veredicto(app, monkeypatch):
    import gradio as gr

    app_module, _, _ = app
    item = {"id": "x", "response": "r", "genuina": True, "reasons": ["reseña neutral"],
            "decision": "revisión humana"}  # fmt: skip
    monkeypatch.setattr(app_module, "pending", lambda: [item])
    with pytest.raises(gr.Error):
        app_module.decide("x", "r", "", "aprobada")
