"""Modo recogida: guarda la reseña enmascarada y el pipeline la lee después (sin modelos)."""

import json

import pytest

pytest.importorskip("gradio")


def test_submit_guarda_y_pipeline_lee(tmp_path, monkeypatch):
    from caso_uso_llm import pipeline, recoger

    out = tmp_path / "recogidas.jsonl"
    monkeypatch.setattr(recoger, "OUT", out)
    monkeypatch.delenv("DEMO_KILL", raising=False)
    status, title, text = recoger.submit("ana_23", True, next(iter(recoger.HOTELS)), "Bien",
                                         "Escríbanme a ana@correo.es, todo bien.")  # fmt: skip
    assert "recibida" in status and title == text == ""
    row = json.loads(out.read_text(encoding="utf-8"))
    assert "ana@correo.es" not in row["text"] and row["nick"] == "ana_23" and row["hotel"]
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    (item,) = pipeline.read_jsonl("recogidas.jsonl")
    assert item["meta"] == {"grupo": "recogida", "nick": "ana_23"} and item["id"] == row["id"]


def test_submit_exige_nick_y_consentimiento():
    import gradio as gr

    from caso_uso_llm import recoger

    with pytest.raises(gr.Error):
        recoger.submit("x", True, recoger.NO_HOTEL, "", "texto")
    with pytest.raises(gr.Error):
        recoger.submit("ana", False, recoger.NO_HOTEL, "", "texto")
