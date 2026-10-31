from caso_uso_llm.evals.variedad import measure, normalize, opening
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


def test_regresion_comparte_la_misma_particion():
    assert first_sentence(REPLY) == "Gracias por compartir su experiencia."
