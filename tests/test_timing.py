"""Medición de latencia: desactivada no hace nada y, activada, no toca la caché de resultados."""

import json
from types import SimpleNamespace

import pytest

from caso_uso_llm import timing
from caso_uso_llm.generate.run import Cache, NoCache


@pytest.fixture(autouse=True)
def _off():
    timing.enable(None)
    yield
    timing.enable(None)


def resp(**ns):
    return SimpleNamespace(**ns)


def test_desactivada_no_hace_nada_ni_crea_ficheros(tmp_path):
    timing.begin("x")
    with timing.stage("analisis"):
        timing.record_ollama(resp(total_duration=10**9), "chat", "m")
    assert timing.end() is None
    assert list(tmp_path.iterdir()) == []


def test_registra_etapas_y_pasa_los_nanosegundos_a_segundos(tmp_path):
    out = tmp_path / "lat.jsonl"
    timing.enable(out, after_stage=lambda: ["modelo-a"])
    timing.begin("r1", rep=0)
    with timing.stage("analisis"):
        timing.record_ollama(
            resp(total_duration=3 * 10**9, load_duration=2 * 10**9, prompt_eval_duration=5 * 10**8,
                 eval_duration=4 * 10**8, prompt_eval_count=100, eval_count=50),
            "chat", "m",
        )  # fmt: skip
    rec = timing.end(total_s=3.1)
    call = rec["llamadas"][0]
    assert (call["etapa"], call["load"], call["prompt_eval"], call["eval"]) == (
        "analisis", 2.0, 0.5, 0.4)  # fmt: skip
    assert call["prompt_eval_count"] == 100 and call["cached"] is False
    assert rec["etapas"][0]["etapa"] == "analisis" and rec["etapas"][0]["despues"] == ["modelo-a"]
    assert json.loads(out.read_text(encoding="utf-8"))["total_s"] == 3.1


def test_un_acierto_de_cache_queda_marcado(tmp_path):
    path = tmp_path / "cache.jsonl"
    cache = Cache(path)
    cache.get_or_call({"a": 1}, lambda: "v")
    timing.enable(tmp_path / "lat.jsonl")
    timing.begin("r1")
    with timing.stage("juez"):
        assert Cache(path).get_or_call({"a": 1}, lambda: "otro") == "v"
    assert timing.end()["llamadas"] == [{"etapa": "juez", "tipo": "llm", "cached": True}]


def test_sin_cache_siempre_llama_y_no_escribe(tmp_path):
    calls = []
    cache = NoCache()
    for _ in range(2):
        assert cache.get_or_call({"a": 1}, lambda: calls.append(1) or "v") == "v"
    assert len(calls) == 2
    assert list(tmp_path.iterdir()) == []


def test_embeddings_sin_persistir_no_escriben_en_disco(tmp_path, monkeypatch):
    import ollama

    from caso_uso_llm.rag import retrieve

    monkeypatch.setattr(retrieve, "DATA_INTERIM", tmp_path)
    monkeypatch.setattr(
        ollama, "embed", lambda **k: resp(embeddings=[[1.0, 0.0]] * len(k["input"]))
    )
    emb = retrieve.Embedder(persist=False)
    emb(["consulta"])
    assert not (tmp_path / "embeddings_bge-m3.jsonl").exists()
    emb.forget(["consulta"])
    assert emb.cache == {}


def test_la_muestra_tiene_tres_publicables_y_tres_a_revision():
    from caso_uso_llm.latency import PUB, REV, SAMPLE, build_sample

    if not SAMPLE.exists():
        pytest.skip("sin muestra")
    items = json.loads(SAMPLE.read_text(encoding="utf-8"))["items"]
    assert [it["decision_cola"] for it in items] == [PUB, REV] * 3
    assert [it["id"] for it in items] == [it["id"] for it in build_sample()]


def test_la_precarga_sin_metricas_cuenta_como_carga():
    from caso_uso_llm.latency import split_review

    meta = {"generador": "gen", "juez": "juez"}
    rec = {
        "total_s": 40.0,
        "etapas": [{"etapa": "carga_generador", "s": 20.0}, {"etapa": "analisis", "s": 19.0}],
        "llamadas": [
            {"etapa": "carga_generador", "modelo": "gen", "cached": False, "load": 0.0,
             "prompt_eval": 0.0, "eval": 0.0},
            {"etapa": "analisis", "modelo": "gen", "cached": False, "load": 15.0,
             "prompt_eval": 1.0, "eval": 3.0},
        ],
    }  # fmt: skip
    assert split_review(rec, meta) == {
        "total": 40.0,
        "carga": 35.0,
        "inferencia": 4.0,
        "resto": 1.0,
    }
