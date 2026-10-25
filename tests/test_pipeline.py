"""Enrutado del pipeline: qué se publica sin revisión y qué va a la cola humana."""

from caso_uso_llm.evals.rubric import IDS
from caso_uso_llm.pipeline import THRESHOLD, reason_kind, route

CLEAN_CHECKS = {
    "promise": False, "liability": False, "tuteo": False, "dialect": False, "plazo": False,
    "servicio_inexistente": [], "cifra_inventada": [], "contradice": False, "importe": [],
    "nombra_fuente": False, "length_ok": True, "signature_ok": True,
}  # fmt: skip


def item(**over) -> dict:
    base = {
        "response": "Gracias por su reseña…",
        "sentiment": "positivo",
        "confidence": 0.93,
        "analysis": {"peticiones": [], "sentimiento": "positivo"},
        "checks": dict(CLEAN_CHECKS),
        "judge": {k: {"cumple": True, "evidencia": ""} for k in IDS},
    }
    return base | over


def test_positiva_segura_y_limpia_se_publica():
    assert route(item()) == []


def test_negativa_va_siempre_a_revision_aunque_todo_lo_demas_este_bien():
    assert route(
        item(sentiment="negativo", analysis={"peticiones": [], "sentimiento": "negativo"})
    ) == ["reseña negativa"]


def test_neutral_va_siempre_a_revision():
    assert route(
        item(sentiment="neutral", analysis={"peticiones": [], "sentimiento": "neutral"})
    ) == ["reseña neutral"]


def test_confianza_bajo_el_umbral_va_a_revision():
    reasons = route(item(confidence=THRESHOLD - 0.01))
    assert len(reasons) == 1 and reason_kind(reasons[0]) == f"confianza < {THRESHOLD}"


def test_peticion_del_cliente_va_a_revision():
    analysis = {"peticiones": ["reembolso"], "sentimiento": "positivo"}
    assert route(item(analysis=analysis)) == ["el cliente pide: reembolso"]


def test_cualquier_alerta_determinista_va_a_revision():
    for key, value in (("promise", True), ("importe", ["12 €"]), ("signature_ok", False)):
        checks = dict(CLEAN_CHECKS) | {key: value}
        assert route(item(checks=checks)), key


def test_un_suspenso_del_juez_va_a_revision():
    verdict = {k: {"cumple": k != "sin_premisa", "evidencia": ""} for k in IDS}
    assert route(item(judge=verdict)) == ["juez: No confirma ni niega lo que no puede comprobar"]


def test_desacuerdo_entre_clasificador_y_llm_va_a_revision():
    # p06: sarcasmo que el clasificador da por positivo con 0,93 y el LLM por negativo
    analysis = {"peticiones": [], "sentimiento": "negativo"}
    reasons = route(item(analysis=analysis))
    assert reasons == ["el clasificador (positivo) y el LLM (negativo) no coinciden"]
    assert reason_kind(reasons[0]) == "el clasificador y el LLM no coinciden"


def test_nombre_de_persona_en_la_respuesta_va_a_revision():
    checks = dict(CLEAN_CHECKS) | {"nombres": ["Andrés"]}
    assert route(item(checks=checks)) == ["nombre de una persona en la respuesta"]


def test_la_confianza_se_muestra_con_tres_decimales():
    assert route(item(confidence=0.8455)) == [f"confianza 0.846 < {THRESHOLD}"]


def test_resena_trampa_va_a_revision_solo_con_ese_motivo():
    reasons = route(item(genuina=False, motivo_trampa="perros que se presentan como huéspedes"))
    assert reasons == ["posible reseña trampa (perros que se presentan como huéspedes)"]


def test_higiene_y_copia_literal_van_a_revision():
    for key, value in (("higiene", ["olor"]), ("copia_literal", ["las vistas a la alhambra"])):
        assert route(item(checks=dict(CLEAN_CHECKS) | {key: value})), key
