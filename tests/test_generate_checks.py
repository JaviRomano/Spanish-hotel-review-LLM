import pytest

from caso_uso_llm.generate import checks as C

REVIEW = "La habitación estaba limpísima, pero el desayuno era muy escaso y el personal, amable."


def test_cita_literal_ignora_mayusculas_tildes_y_signos():
    assert C.quote_in_review("el DESAYUNO era muy escaso", REVIEW)
    assert C.quote_in_review("habitacion estaba limpisima", REVIEW)
    assert not C.quote_in_review("el desayuno era abundante", REVIEW)  # invención
    assert not C.quote_in_review("", REVIEW)


def test_menciona_aspecto():
    aspects = [{"cita": "el desayuno era muy escaso"}]
    assert C.mentions_aspect("Lamentamos que el desayuno no estuviera a la altura.", aspects)
    assert not C.mentions_aspect("Gracias por su estancia en el hotel.", aspects)


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("Le devolveremos el dinero de inmediato.", "promise"),
        ("Le ofrecemos un descuento en su próxima visita.", "promise"),
        ("Le invitamos a una noche gratis en su próxima visita.", "promise"),
        ("Procederemos al reembolso de la estancia.", "promise"),
        ("Ha sido culpa nuestra, sin duda.", "liability"),
        ("Asumimos toda la responsabilidad de lo ocurrido.", "liability"),
        ("Gracias por compartir tu experiencia.", "tuteo"),
        ("Nos alegra que todo fuera mu bien.", "dialect"),
    ],
)
def test_alertas(text, flag):
    assert C.run_checks(text, [{"cita": "x"}])[flag]


def test_respuesta_correcta_sin_alertas():
    text = (
        "Muchas gracias por su reseña. Nos alegra que la habitación le pareciera impecable y que "
        "el personal le atendiera con amabilidad. Lamentamos que el desayuno le resultara escaso: "
        "trasladaremos su comentario al equipo de cocina para revisarlo. Esperamos tener la "
        "oportunidad de recibirle de nuevo y que su próxima estancia sea redonda en todos los "
        "sentidos.\n\nEl equipo del hotel"
    )
    c = C.run_checks(text, [{"cita": "el desayuno era muy escaso"}])
    assert c["length_ok"] and c["mentions_aspect"] and c["signature_ok"]
    assert not any(c[k] for k in ("promise", "liability", "tuteo", "dialect"))


def test_patron_prohibido_del_caso():
    c = C.run_checks(
        "El spa es gratuito para todos.", [], extra_forbidden=[r"spa (es|era) gratuito"]
    )
    assert c["case_forbidden"] == [r"spa (es|era) gratuito"]


# Falsos positivos reales del detector v1 (Fase 4, primera ejecución): no son promesas.
@pytest.mark.parametrize(
    "text",
    [
        "Respecto a su solicitud de reembolso, le invitamos a contactar con nosotros por privado.",
        "Respecto a su petición de compensación, le invitamos a contactar con reservas.",
        "Nos complace que apreciara el aparcamiento gratuito y el acceso a internet.",
        "Le ofrecemos nuestras más sinceras disculpas.",
    ],
)
def test_no_es_promesa(text):
    assert not C.run_checks(text, [{"cita": "x"}])["promise"]


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("Trasladaremos inmediatamente su comentario.", True),
        ("Ya hemos solucionado el problema del wifi.", True),
        ("Lo revisaremos en los próximos días.", True),
        ("Trasladaremos su comentario al equipo para revisarlo.", False),
    ],
)
def test_plazo(text, flag):
    assert C.run_checks(text, [{"cita": "x"}])["plazo"] is flag


def test_person_names_detecta_nombres_de_la_resena_y_saludos_personalizados():
    from caso_uso_llm.generate.checks import person_names

    review = "La recepcionista, una tal Lucía, fue maleducada. Llamadme (soy Andrés)."
    assert person_names("Estimado Andrés: Gracias por su reseña.", review) == ["Andrés"]
    assert person_names("Estimado cliente: lo trasladaremos a Lucía.", review) == ["Lucía"]
    assert person_names("Estimada clienta: Gracias por su reseña.", review) == []
    # Lugares con mayúscula no son personas: solo cuentan nombres presentados como tales
    assert person_names("Estimado cliente: disfrute de la Alhambra.", "Vistas a la Alhambra.") == []


def test_presupposed_stay_solo_si_el_cliente_no_llego_a_alojarse():
    from caso_uso_llm.generate.checks import presupposed_stay

    cancelled = "Íbamos a alojarnos un fin de semana pero cancelé la reserva y nadie me llamó."
    assert presupposed_stay("Lamentamos que su estancia no estuviera a la altura.", cancelled)
    assert not presupposed_stay("Lamentamos lo que nos describe sobre su reserva.", cancelled)
    stayed = "Pasamos tres noches; la habitación, ruidosa."
    assert not presupposed_stay("Lamentamos que su estancia no fuera tranquila.", stayed)


def test_hygiene_terms_y_copia_literal():
    from caso_uso_llm.generate.checks import copied_from_review, hygiene_terms

    assert hygiene_terms("Lamentamos el mal olor y las sábanas sucias.") == ["mal olor", "sucias"]
    assert hygiene_terms("La limpieza es una prioridad absoluta para nosotros.") == []
    review = "El desayuno, la limpieza y las instalaciones a la altura."
    assert copied_from_review(
        "Nos alegra que el desayuno, la limpieza y las instalaciones…", review
    )
    assert (
        copied_from_review("Gracias por su reseña sobre la comida.", "La comida de la casa") == []
    )
