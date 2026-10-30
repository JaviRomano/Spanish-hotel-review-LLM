import json

import pytest

from caso_uso_llm.formulario import MAX_REVIEWS, MAX_TEXT, parse_row

HOTELS = {"h01", "h02"}
STAMP = "31/10/2026 12:30:05"


def _raw(**kw) -> str:
    doc = {"consentimiento": True, "nick": "ana.g", "contacto": "linkedin.com/in/ana",
           "resenas": [{"hotel": "h01", "title": "Bien", "text": "Buena estancia."}]}  # fmt: skip
    return json.dumps(doc | kw, ensure_ascii=False)


def test_una_peticion_valida_da_el_formato_de_recoger():
    reviews, contact = parse_row(STAMP, _raw(), HOTELS)
    assert contact == "linkedin.com/in/ana"
    r = reviews[0]
    assert r["id"].startswith("form-") and r["fecha"] == "2026-10-31T12:30:05"
    assert (r["hotel"], r["title"], r["text"]) == ("h01", "Bien", "Buena estancia.")
    assert "contacto" not in r  # el contacto no debe llegar nunca a los modelos


def test_el_id_es_estable_para_que_reimportar_no_duplique():
    assert (
        parse_row(STAMP, _raw(), HOTELS)[0][0]["id"] == parse_row(STAMP, _raw(), HOTELS)[0][0]["id"]
    )


def test_varias_resenas_y_hotel_opcional():
    resenas = [{"text": "Una."}, {"hotel": "", "text": "Otra."}, {"hotel": "h02", "text": "Más."}]
    reviews, _ = parse_row(STAMP, _raw(resenas=resenas), HOTELS)
    assert [r["hotel"] for r in reviews] == [None, None, "h02"]
    assert len({r["id"] for r in reviews}) == 3


def test_enmascara_datos_personales_como_recoger():
    text = "Llamadme al 600 123 456 o escribid a ana@example.com, por favor."
    r = parse_row(STAMP, _raw(resenas=[{"text": text}]), HOTELS)[0][0]
    assert "600 123 456" not in r["text"] and "ana@example.com" not in r["text"]


@pytest.mark.parametrize(
    "raw",
    [
        "esto no es json",
        '["una lista"]',
        _raw(consentimiento=False),
        _raw(nick="x"),
        _raw(nick="con espacios y más"),
        _raw(resenas=[]),
        _raw(resenas="texto"),
        _raw(resenas=[{"text": "ok"}] * (MAX_REVIEWS + 1)),
        _raw(resenas=[{"text": "   "}]),
        _raw(resenas=[{"text": "x" * (MAX_TEXT + 1)}]),
        _raw(resenas=[{"hotel": "h99", "text": "ok"}]),
        _raw(resenas=["no es un objeto"]),
    ],
)
def test_rechaza_lo_que_no_es_una_peticion_valida(raw):
    with pytest.raises(ValueError):
        parse_row(STAMP, raw, HOTELS)
