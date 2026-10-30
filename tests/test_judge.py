import json

from caso_uso_llm.evals import judge as J
from caso_uso_llm.evals.rubric import IDS, RUBRICS


class FakeCache:
    """Devuelve una respuesta fija del juez sin llamar a ningún LLM."""

    def __init__(self, verdicts: dict):
        self.raw = json.dumps(verdicts)

    def get_or_call(self, payload, fn):
        return self.raw


RESPONSE = "Lamentamos que su hijo se cayera por el suelo mojado. El equipo del hotel"


def _verdicts(**fails):
    return {c: {"cumple": c not in fails, "evidencia": fails.get(c, "")} for c in IDS}


def test_evidencia_literal_valida():
    v = J.judge("reseña", RESPONSE, FakeCache(_verdicts(sin_culpa="se cayera por el suelo mojado")))
    assert not v["sin_culpa"]["cumple"] and not v["sin_culpa"]["evidencia_inventada"]


def test_evidencia_inventada_se_marca():
    v = J.judge("reseña", RESPONSE, FakeCache(_verdicts(sin_culpa="reconocemos nuestro error")))
    assert v["sin_culpa"]["evidencia_inventada"]


def test_aspecto_no_exige_cita_en_v2_pero_si_en_v1():
    cache = FakeCache(_verdicts(aspecto=""))
    assert not J.judge("r", RESPONSE, cache, "v2")["aspecto"]["evidencia_inventada"]
    assert J.judge("r", RESPONSE, cache, "v1")["aspecto"]["evidencia_inventada"]


def test_rubricas_mismos_criterios_y_v2_cambia_la_culpa():
    assert [c.id for c in RUBRICS["v1"]] == [c.id for c in RUBRICS["v2"]] == list(IDS)
    v1 = {c.id: c for c in RUBRICS["v1"]}
    v2 = {c.id: c for c in RUBRICS["v2"]}
    assert "SÍ cumple" in v2["sin_culpa"].no_cumple_si and v1["sin_culpa"] != v2["sin_culpa"]
    assert J.system_prompt("v1") != J.system_prompt("v2")


def test_rubrica_con_ficha_solo_cambia_los_criterios_que_dependen_de_la_ficha():
    from caso_uso_llm.evals.rubric import RUBRICS, RUBRICS_FICHA

    v2, v2f = RUBRICS["v2"], RUBRICS_FICHA["v2f"]
    assert [c.id for c in v2f] == [c.id for c in v2]
    changed = {a.id for a, b in zip(v2, v2f, strict=True) if a != b}
    assert changed == {"sin_invencion", "sin_premisa", "tono"}
    assert "v2f" not in RUBRICS  # `just juez` (casos sin ficha) no debe usarla


def test_juez_sin_ficha_mantiene_el_mensaje_de_siempre():
    from caso_uso_llm.evals.judge import _ficha_block, system_prompt

    assert _ficha_block(None) == ""
    assert "FICHA DEL HOTEL" not in system_prompt("v2")
    assert "FICHA DEL HOTEL" in system_prompt("v2f")


def test_v2g_solo_aclara_sin_premisa_respecto_a_v2f():
    from caso_uso_llm.evals.rubric import RUBRICS_FICHA

    v2f, v2g = RUBRICS_FICHA["v2f"], RUBRICS_FICHA["v2g"]
    assert {a.id for a, b in zip(v2f, v2g, strict=True) if a != b} == {"sin_premisa"}


def test_v2h_solo_aclara_culpa_respecto_a_v2g():
    from caso_uso_llm.evals.rubric import RUBRICS_FICHA

    v2g, v2h = RUBRICS_FICHA["v2g"], RUBRICS_FICHA["v2h"]
    assert {a.id for a, b in zip(v2g, v2h, strict=True) if a != b} == {"sin_culpa"}


def test_el_juez_de_pares_v1_no_cambia_y_v2_dice_que_el_saludo_no_cuenta():
    from caso_uso_llm.evals import judge as J

    seen = []

    class Rec:
        def get_or_call(self, payload, fn):
            seen.append(payload["sys"])
            return '{"motivo": "", "preferida": "empate"}'

    J.compare("r", "a", "b", Rec())
    J.compare("r", "a", "b", Rec(), version="v2")
    assert seen[0] == J.PAIR_SYSTEM  # la caché de los pares de siempre sigue valiendo
    assert seen[1] == J.PAIR_SYSTEM + J.PAIR_SALUDO and "saludo inicial" in seen[1]
