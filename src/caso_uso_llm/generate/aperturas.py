"""Variante de apertura: quita el saludo y el agradecimiento genérico, sin generar nada nuevo.

En v6 casi todas las respuestas abren igual («Estimado cliente:» y «Gracias por compartir su
experiencia.»), y esa repetición se nota al ver varias seguidas (`just variedad`). La primera frase
con contenido ya es la siguiente, así que basta con recortar. Solo se quita un agradecimiento que no
dice nada de la reseña: «Gracias por compartir su experiencia en el spa» se queda.

En prueba: el pipeline no lo usa hasta que lo apruebe la valoración humana (`variante_aperturas.py`).

Uso: uv run python scripts/variante_aperturas.py
"""

import re

from caso_uso_llm.evals.variedad import normalize, opening

GENERIC_THANKS = re.compile(
    r"^(?:muchas )?gracias por (?:escribirnos"
    r"|compartir su (?:experiencia|opinión)(?: con nosotros)?"
    r"|tomarse el tiempo de compartir su experiencia(?: con nosotros)?)$"
)


def strip_opening(response: str) -> str:
    greeting, first = opening(response)
    body = response.strip()[len(greeting) :].lstrip()
    if not GENERIC_THANKS.match(normalize(first)):
        return body
    rest = body[len(first) :].lstrip()
    return rest[0].upper() + rest[1:] if rest else body
