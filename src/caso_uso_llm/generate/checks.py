"""Comprobaciones deterministas de la Fase 4 (una por regla de la guía de estilo).

Son detectores baratos y explicables, no un juicio de calidad: marcan señales (una palabra de
compensación, un tuteo) que el juez LLM de la Fase 6 tendrá que confirmar. Falsos positivos
conocidos: "gratuito" citando al cliente, "pa" en "Pa-" de un nombre propio.
"""

import re

from caso_uso_llm.data.normalize import dedup_key

# Sin tildes: se comparan con dedup_key(), que las quita.
_STOP = frozenset(
    (
        "para", "pero", "como", "cuando", "donde", "desde", "hasta", "sobre", "entre", "aunque",
        "porque", "mucho", "mucha", "muchos", "muchas", "todo", "toda", "todos", "todas", "este",
        "esta", "estos", "estas", "habia", "hemos", "estaba", "estaban", "hotel", "habitacion",
        "habitaciones", "bien", "nada", "algo", "siempre", "tambien", "gracias", "estancia",
    )
)  # fmt: skip

# Promesa = verbo de compromiso + algo que se da o se devuelve. Mencionar "reembolso" para
# derivar al canal privado ("respecto a su solicitud de reembolso, le invitamos a contactar")
# NO es una promesa: así responde la guía de estilo (regla 4).
_COMMIT = (
    r"(?:le|les)\s+(?:devolveremos|reembolsaremos|compensaremos|regalaremos|abonaremos|"
    r"ofrecemos|ofreceremos|haremos|aplicaremos|invitamos\s+a\s+(?:una|un|disfrutar))|"
    r"procederemos\s+(?:a|al)|recibirá|tendrá\s+derecho"
)
_GOODS = (
    r"reembols\w*|devoluci\w*|dinero|importe|descuent\w*|compensaci\w*|noche\w*\s+gratis|"
    r"gratis|gratuit\w*|regalo\w*|cortes[ií]a|vale\b|bono\b|upgrade|mejora\s+de\s+habitaci"
)
PROMISE = re.compile(rf"\b(?:{_COMMIT})\b(?:\W+\w+){{0,6}}?\W+(?:{_GOODS})", re.IGNORECASE)
LIABILITY = re.compile(
    r"(culpa nuestra|nuestra culpa|asumimos (?:toda )?(?:la )?responsabilidad|"
    r"reconocemos (?:nuestro|el|un) error|fue un error nuestro|negligencia)",
    re.IGNORECASE,
)
TUTEO = re.compile(r"\b(tu|tus|contigo|te esperamos|gracias por compartir tu)\b", re.IGNORECASE)
DIALECT = re.compile(r"\b(mu|pa|to|toa|na|verdá|usté|quillo|illo|pisha)\b", re.IGNORECASE)
SIGNATURE = re.compile(r"El equipo del hotel\.?\s*$")
# Regla sin_plazos (spec.py): plazos o acciones dadas por hechas.
PLAZO = re.compile(
    r"\b(inmediatamente|de inmediato|en (?:los|las) pr[oó]xim[oa]s (?:d[ií]as|horas|semanas)|"
    r"ya (?:hemos|est[aá]n?|ha sido)\s+\w+|hemos (?:solucionado|arreglado|reparado|corregido|instalado))\b",
    re.IGNORECASE,
)


def quote_in_review(quote: str, review: str) -> bool:
    """La cita aparece en la reseña (ignorando mayúsculas, tildes y signos)."""
    q = dedup_key(quote)
    return bool(q) and q in dedup_key(review)


def content_words(text: str) -> set[str]:
    return {w[:5] for w in dedup_key(text).split() if len(w) >= 5 and w not in _STOP}


def mentions_aspect(response: str, aspects: list[dict]) -> bool:
    """Aproximación: la respuesta comparte alguna palabra con contenido (por su raíz de 5 letras)
    con la cita de algún aspecto. No detecta paráfrasis sin palabras en común."""
    resp = content_words(response)
    return any(content_words(a["cita"]) & resp for a in aspects)


def word_count(text: str) -> int:
    return len(text.split())


def run_checks(response: str, aspects: list[dict], extra_forbidden: list[str] = ()) -> dict:
    """Todas las comprobaciones de una respuesta. `extra_forbidden`: patrones propios de un caso
    adversarial (p. ej. confirmar un spa gratuito que nadie ha comprobado)."""
    n = word_count(response)
    forbidden_hits = [p for p in extra_forbidden if re.search(p, response, re.IGNORECASE)]
    return {
        "words": n,
        "length_ok": 50 <= n <= 130,
        "mentions_aspect": mentions_aspect(response, aspects),
        "promise": bool(PROMISE.search(response)),
        "liability": bool(LIABILITY.search(response)),
        "tuteo": bool(TUTEO.search(response)),
        "dialect": bool(DIALECT.search(response)),
        "signature_ok": bool(SIGNATURE.search(response.strip())),
        "plazo": bool(PLAZO.search(response)),
        "case_forbidden": forbidden_hits,
    }


# Nombres de personas (guardarraíl, Fase 9). El enmascarado de datos personales (R14) solo cubre
# nombres con tratamiento o cargo; los nombres sueltos («soy Andrés», «una tal Lucía») llegan al
# modelo. Mientras no haya NER, una respuesta que use un nombre de la reseña va a revisión.
_NAME = r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)"
NAME_IN_REVIEW = re.compile(
    rf"\b(?:soy|me llamo|mi nombre es|una tal|un tal|la chica|el chico|recepcionista|camarer[oa])"
    rf",?\s+{_NAME}"
)
SELF_NAME = re.compile(rf"\b(?:soy|me llamo|mi nombre es),?\s+{_NAME}")
# Saludo personalizado en la primera línea: «Estimado Andrés:», «Hola, Andrés:». Solo dentro de esa
# línea: «Hola:» seguido de un salto de línea (el saludo de v9) no captura la palabra siguiente.
SALUTATION = re.compile(
    r"^[ \t]*(?:Estimad[oa]s?|Hola|Buenas|Saludos)[ \t]*,?[ \t]+([^\s:,]+)", re.IGNORECASE
)
GENERIC_SALUTATION = {"cliente", "clienta", "clientes", "huésped", "huéspedes", "señor", "señora"}


def person_names(response: str, review: str) -> list[str]:
    """Nombres de persona en la respuesta: los que la reseña presenta como tales, o un saludo
    personalizado («Estimado Andrés:») en vez de genérico. El nombre que da el propio cliente se
    admite en el saludo y solo ahí (Javier, 2026-10-31); el del personal nunca."""
    m = SALUTATION.match(response)
    rest = response[m.end() :] if m else response
    own = {n.split()[0] for n in SELF_NAME.findall(review)}
    found = [
        n
        for n in NAME_IN_REVIEW.findall(review)
        if re.search(rf"\b{re.escape(n)}\b", rest if n.split()[0] in own else response)
    ]
    if m and m.group(1).lower() not in GENERIC_SALUTATION and m.group(1) not in own | set(found):
        found.append(m.group(1))
    return found


# Estancia que no hubo (Fase 9, ahr-ahr-2775): el juez no la detecta; esta regla sí.
NO_STAY = re.compile(
    r"\b(cancel[ée]\w*|cancelamos|cancelar la reserva|anul[ée]\w*|íbamos a alojarnos|"
    r"no (?:llegamos|pudimos) (?:a )?(?:ir|llegar|alojarnos)|no nos (?:llegamos a )?alojamos|"
    r"nunca llegamos)\b",
    re.IGNORECASE,
)
STAY = re.compile(r"\bsu (?:estancia|visita|experiencia en (?:el|nuestro) hotel)\b", re.IGNORECASE)


def presupposed_stay(response: str, review: str) -> bool:
    """La reseña dice que el cliente no llegó a alojarse y la respuesta habla de «su estancia»."""
    return bool(NO_STAY.search(review) and STAY.search(response))


# Higiene (Fase 9, decisión de Javier): la respuesta no debe transmitir que pudo haber un problema
# de higiene u olores. Cualquier término de este tipo manda la respuesta a revisión.
HYGIENE = re.compile(
    r"\b(ol[oí]a\w*|olor(?:es)?|huel[ea]\w*|mal olor|sucio\w*|sucia\w*|suciedad|pelos?|cucarachas?|"
    r"chinches?|insectos?|bichos?|moho|humedad|manchas?|mugre|hongos?|coliflor\w*)\b",
    re.IGNORECASE,
)


def hygiene_terms(response: str) -> list[str]:
    return sorted({m.group(0).lower() for m in HYGIENE.finditer(response)})


# Accidente o riesgo legal (2026-10-30, auditoría de la demo): lo decide la RESEÑA, no la
# respuesta. Antes iban a revisión solo por ser negativas; una reseña positiva o neutral que
# contara una caída se habría publicado sin que nadie la viera. Sin «ahog-» suelto: «camareros
# ahogados de trabajo» (ahr-ahr-12719).
INCIDENT = re.compile(
    r"\b(accidente\w*|me ca[ií]|se ca(?:y[oó]|yeron)|ca[ií]da\w*|resbal\w+|lesi[oó]n\w*|"
    r"lesionad\w+|herid[ao]s?|esguince\w*|fractur\w+|urgencias|hospital\w*|ambulancia|"
    r"intoxicaci\w+|quemadur\w+|se ahog\w+|denunci\w+|abogad\w+|demand\w+|juzgado\w*|"
    r"tribunal\w*|hoja de reclamaciones|reclamaci[oó]n (?:en|a|ante) consumo|indemnizaci\w+|"
    r"daños y perjuicios|reclamar (?:los )?daños|responsabilidad civil)\b",
    re.IGNORECASE,
)


def incident_terms(review: str) -> list[str]:
    """Términos de accidente, lesión o reclamación legal en la reseña."""
    return sorted({m.group(0).lower() for m in INCIDENT.finditer(review)})


_STOP = frozenset(
    [
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "a",
        "en",
        "y",
        "o",
        "que",
        "por",
        "para",
        "con",
        "sin",
        "su",
        "sus",
        "se",
        "lo",
        "le",
        "les",
        "nos",
        "muy",
        "mas",
        "más",
        "es",
        "fue",
        "era",
        "como",
        "pero",
        "ya",
        "me",
        "mi",
    ]
)


def copied_from_review(response: str, review: str, n: int = 4) -> list[str]:
    """Secuencias de n palabras copiadas de la reseña con al menos dos palabras con contenido
    (Fase 9: «el desayuno, la limpieza y las instalaciones», «las vistas a la Alhambra»)."""
    tok = lambda t: re.findall(r"\w+", t.lower())  # noqa: E731
    review_grams = {tuple(g) for g in _ngrams(tok(review), n)}
    found = []
    for g in _ngrams(tok(response), n):
        if tuple(g) in review_grams and sum(w not in _STOP and len(w) > 3 for w in g) >= 2:
            found.append(" ".join(g))
    return list(dict.fromkeys(found))


def _ngrams(words: list[str], n: int) -> list[list[str]]:
    return [words[i : i + n] for i in range(len(words) - n + 1)]


# «Revisaremos lo ocurrido para entender cómo se produjo…»: la finalidad da a entender un fallo y
# el juez la suspende como admisión de culpa. v9 lo prohíbe en el prompt y el modelo no obedece
# (reports/phase9_regresion.md), así que v9 la recorta aquí: la frase termina tras lo que se revisa.
# Solo tras un verbo «revisar» en futuro y dentro de la misma frase; el resto del texto no cambia.
PURPOSE = re.compile(
    r"(\b(?:revisaremos|revisará|revisarán|vamos a revisar)\b[^.!?\n]*?)"
    r"\s*,?\s+(?:para|con el fin de|a fin de|con el objetivo de|y así)\b[^.!?\n]*([.!?])",
    re.IGNORECASE,
)


def trim_purpose(response: str) -> tuple[str, list[str]]:
    """Quita la finalidad tras «revisaremos…»; devuelve el texto y los fragmentos quitados."""
    removed = [m.group(0)[len(m.group(1)) : -1].strip() for m in PURPOSE.finditer(response)]
    return PURPOSE.sub(r"\1\2", response), removed
