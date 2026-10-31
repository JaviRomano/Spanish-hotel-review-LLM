from caso_uso_llm.evals.variedad import (
    measure,
    normalize,
    opening,
    shared_details,
    unique_pairs,
)
from caso_uso_llm.generate.aperturas import strip_opening
from caso_uso_llm.rag.regresion import first_sentence

REPLY = "Estimado cliente:\n\nGracias por compartir su experiencia. Nos alegra.\n\nEl equipo"


def test_separa_saludo_y_primera_frase():
    assert opening(REPLY) == ("Estimado cliente:", "Gracias por compartir su experiencia.")


def test_una_respuesta_sin_saludo_no_pierde_su_primera_frase():
    assert opening("Agradecemos su visita. Vuelva pronto.") == ("", "Agradecemos su visita.")


def test_solo_mayusculas_y_puntuacion_no_cuentan_como_apertura_distinta():
    assert normalize("¡Gracias, por compartir!") == normalize("gracias por compartir")


def test_mide_la_tanda_entera():
    replies = [
        REPLY,
        REPLY.replace("Gracias", "Muchas gracias"),
        "Estimado cliente:\n\nGracias por escribirnos. Bien.",
        "Hola:\n\nLamentamos lo ocurrido. Bien.",
    ]
    m = measure(replies)
    assert (m["n"], m["saludo_top_n"], m["saludos_distintos"]) == (4, 3, 2)
    assert (m["frases_distintas"], m["gracias_por"], m["gracias_por_compartir"]) == (4, 3, 2)
    assert (m["inicio_top"], m["inicio_top_n"]) == ("gracias por compartir su", 1)


def test_los_pares_no_cuentan_el_saludo_y_uno_repetido_no_es_unico():
    replies = ["Estimado cliente:\n\nNos alegra mucho.", "Hola:\n\nNos alegra poco."]
    assert unique_pairs(replies) == (2, 3)


def test_un_par_repetido_dentro_de_una_respuesta_sigue_siendo_unico():
    assert unique_pairs(["uno dos uno dos"]) == (2, 2)


def test_cuenta_los_detalles_de_la_propia_resena_por_su_raiz():
    reply = "Estimado cliente:\n\nSentimos lo del desayuno frío y el ruido."
    assert shared_details(reply, "Desayunos fríos") == 1


def test_el_saludo_y_las_formulas_no_son_un_detalle():
    reply = "Estimado cliente:\n\nGracias por compartir su experiencia."
    assert shared_details(reply, "Estimado equipo: gran experiencia, quiero compartir.") == 0


def test_mide_los_detalles_solo_si_hay_resenas():
    assert measure([REPLY])["con_detalle"] == 0
    assert (
        measure(["A:\n\nEl desayuno y la piscina."], ["desayuno, piscina"])["con_dos_detalles"] == 1
    )


def test_regresion_comparte_la_misma_particion():
    assert first_sentence(REPLY) == "Gracias por compartir su experiencia."


def test_quita_saludo_y_agradecimiento_generico():
    assert strip_opening(REPLY) == "Nos alegra.\n\nEl equipo"


def test_conserva_un_agradecimiento_con_contenido():
    reply = "Estimado cliente:\n\nGracias por compartir su experiencia en el spa. Nos alegra."
    assert strip_opening(reply) == "Gracias por compartir su experiencia en el spa. Nos alegra."


def test_sin_saludo_ni_agradecimiento_no_cambia():
    assert strip_opening("Lamentamos lo ocurrido. Lo revisaremos.") == (
        "Lamentamos lo ocurrido. Lo revisaremos."
    )
