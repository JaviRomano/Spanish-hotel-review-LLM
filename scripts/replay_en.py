"""Versión en inglés de la página de repetición (docs/en/index.html).

Mismo generador, misma plantilla y mismas cifras: aquí solo se traducen textos. Cada texto de la
plantilla tiene que aparecer exactamente: si la plantilla cambia y una traducción deja de aplicarse,
la generación falla en vez de dejar español suelto. Reseñas, respuestas y fichas siguen en español.
"""
# ruff: noqa: E501  (textos: partirlos los haría menos legibles)

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = json.loads((ROOT / "evals" / "demo" / "replay_en.json").read_text(encoding="utf-8"))

UI = [
    ('<html lang="es">', '<html lang="en">'),
    (
        'content="Cómo responde un sistema local de IA (clasificador, RAG, generador y juez) a reseñas de hotel difíciles: respuestas ya evaluadas, con sus fallos. Un proyecto de __AUTHOR__."',
        'content="How a local AI system (classifier, RAG, generator and judge) responds to difficult hotel reviews: evaluated replies, flaws included. A project by __AUTHOR__."',
    ),
    (
        '<meta property="og:url" content="__PAGE_URL__">',
        '<meta property="og:url" content="__PAGE_URL__en/">',
    ),
    (
        'content="Un sistema 100 % local redacta respuestas a reseñas de hotel, comprueba los riesgos y decide si se publican o pasan a una persona. Respuestas reales, con sus fallos."',
        'content="A fully local system drafts replies to hotel reviews, checks the risks and decides whether they are published or go to a person. Real replies, flaws included."',
    ),
    (
        'content="Título del proyecto y sus tres cifras principales"',
        'content="Project title and technical summary"',
    ),
    ('content="es_ES"', 'content="en_GB"'),
    (">Código e informes</a>", ">Code and reports</a>"),
    (">Cambiar tema</button>", ">Change theme</button>"),
    (
        "<h1>¿Cómo responde una IA a las reseñas difíciles de un hotel?</h1>",
        "<h1>How does an AI respond to a hotel's difficult reviews?</h1>",
    ),
    (
        "Un hotel recibe cientos de reseñas, y en una frase mal escrita se puede admitir una culpa que nadie ha comprobado. Este sistema interpreta la reseña, redacta la respuesta, la revisa y decide si se publica sola o pasa a una persona.",
        "A hotel receives hundreds of reviews, and one badly written sentence can admit a fault nobody has verified. This system interprets the review, drafts the reply, checks it and decides whether it is published on its own or goes to a person.",
    ),
    (
        "Trabajé años en hostelería respondiendo a incidencias de clientes y conozco lo delicado que es hacerlo bien.",
        "I spent years in hospitality handling guest complaints, and I know how delicate it is to do well.",
    ),
    (">Contacto</a>", ">Contact</a>"),
    (">Pruébalo</button>", ">Try it</button>"),
    (
        "Esta página muestra resultados ya generados. Escribe una o varias reseñas, inventadas o reales, sin datos personales. Se las paso al sistema y te envío las respuestas y justificaciones.",
        "This page shows saved results. Write one or more reviews, made up or real, without personal data. I will run them through the system and send you the replies and the reasoning. The system works in Spanish, so please write them in Spanish.",
    ),
    (">Añadir otra reseña</button>", ">Add another review</button>"),
    ("Nick (no tu nombre)", "Nickname (not your name)"),
    ("Dónde te envío el resultado", "Where should I send the result?"),
    ('placeholder="email"', 'placeholder="email"'),
    (">No rellenar</label>", ">Leave empty</label>"),
    (
        "Acepto que mis reseñas y mi contacto se envíen a través de Google Forms y se guarden para evaluar y mejorar el sistema y enviarme el resultado. No se publicarán. No incluyas datos personales en las reseñas.",
        "I agree that my reviews and contact details are sent through Google Forms and kept to evaluate and improve the system and to send me the result. They will not be published. Do not include personal data in the reviews.",
    ),
    (">Enviar reseñas</button>", ">Send reviews</button>"),
    (
        'aria-label="En esta página"><a href="#casos">Ver los casos</a><a href="#como">Cómo funciona</a><a href="#aprendido">Qué aprendí</a><a href="#limites">Qué falta</a><a href="#evidencia">Evidencia</a>',
        'aria-label="On this page"><a href="#casos">See the cases</a><a href="#como">How it works</a><a href="#aprendido">What I learned</a><a href="#limites">What is missing</a><a href="#evidencia">Evidence</a>',
    ),
    ("<summary>Para revisores técnicos</summary>", "<summary>For technical reviewers</summary>"),
    (
        ">Evaluación fuera de distribución</a>: el clasificador medido con reseñas que no vio, no solo con el test limpio.",
        ">Out-of-distribution evaluation</a>: the classifier measured on reviews it never saw, not only on the clean test set.",
    ),
    (
        ">Juez frente a una persona</a>: dónde coinciden y cómo se corrigieron las etiquetas.",
        ">Judge against a person</a>: where they agree and how the labels were corrected.",
    ),
    (">Regresión</a> y <a", ">Regression</a> and <a"),
    (
        ">comparación a ciegas</a>: por qué se mantiene v6 frente a versiones posteriores.",
        ">blind comparison</a>: why v6 stays over later versions.",
    ),
    (
        ": la comprobación que impide ejecutar en CPU sin avisar, añadida tras ese incidente.",
        ": the check that prevents running on the CPU without warning, added after that incident.",
    ),
    (">Recorrido de una reseña</p>", ">Path of a review</p>"),
    (
        "<b>Llega la reseña</b><span>texto y hotel</span>",
        "<b>The review arrives</b><span>text and hotel</span>",
    ),
    (
        "<b>Clasificador</b><span>mRoBERTa (ensamble de 3 semillas) · sentimiento y confianza</span>",
        "<b>Classifier</b><span>mRoBERTa (3-seed ensemble) · sentiment and confidence</span>",
    ),
    (
        "<b>Ficha del hotel y políticas</b><span>ficha completa · RAG: políticas y respuestas aprobadas</span>",
        "<b>Hotel fact sheet and policies</b><span>full fact sheet · RAG: policies and approved replies</span>",
    ),
    (
        "<b>Borrador</b><span>Qwen3.6 27B · aspectos en JSON y respuesta</span>",
        "<b>Draft</b><span>Qwen3.6 27B · aspects as JSON and reply</span>",
    ),
    (
        "<b>Reglas y juez</b><span>Gemma 4 12B · 8 criterios con evidencia</span>",
        "<b>Rules and judge</b><span>Gemma 4 12B · 8 criteria with evidence</span>",
    ),
    (
        "<b>Puerta (decisión final)</b><span>se publica sola o pasa a una persona</span>",
        "<b>Gate (final decision)</b><span>published on its own or goes to a person</span>",
    ),
    (
        "Los modelos corren en un PC, en una sola GPU: <b>ninguna reseña pasa por un modelo externo</b>.",
        "The models run on one PC, on a single GPU: <b>no review goes through an external model</b>.",
    ),
    ('id="casos">Casos</h2>', 'id="casos">Cases</h2>'),
    ('<label for="case">Reseña</label>', '<label for="case">Review</label>'),
    ('aria-label="Anterior"', 'aria-label="Previous"'),
    ('aria-label="Siguiente"', 'aria-label="Next"'),
    (
        'id="tour" type="button">Guía orientativa</button>',
        'id="tour" type="button">Guided tour</button>',
    ),
    (">Salir de la guía</button>", ">Leave the tour</button>"),
    ('aria-label="Resumen del caso"', 'aria-label="Case summary"'),
    (
        '<span class="label">Reseña recibida</span>',
        '<span class="label">Review received (in Spanish)</span>',
    ),
    (
        '<span class="label">Respuesta generada · borrador</span>',
        '<span class="label">Generated reply · draft, in Spanish</span>',
    ),
    (
        "Subrayado: fragmentos que señalamos el juez o yo. Pasa el ratón o toca, o llega con el tabulador, para ver por qué.",
        "Highlighted: passages flagged by the judge or by me. Hover, tap or tab to them to see why.",
    ),
    (
        "<summary>Clasificador y contexto recuperado</summary>",
        "<summary>Classifier and retrieved context</summary>",
    ),
    ('id="como">Cómo funciona</h2>', 'id="como">How it works</h2>'),
    (
        'id="aprendido">Lo que aprendí por el camino</h2>',
        'id="aprendido">What I learned along the way</h2>',
    ),
    ('id="limites">Lo que no se ha probado</h2>', 'id="limites">What has not been tested</h2>'),
    (
        "<strong>Un hotel real.</strong> Las fichas de los hoteles y sus políticas son inventadas, y parte de los casos son sintéticos. Habría que verlo con la documentación de un hotel de verdad.",
        "<strong>A real hotel.</strong> The hotels' fact sheets and policies are made up, and some of the cases are synthetic. It would need testing with a real hotel's documents.",
    ),
    (
        "<strong>Si compensa.</strong> No he medido cuánto trabajo ahorra ni qué tasa de error sería aceptable en producción.",
        "<strong>Whether it pays off.</strong> I have not measured how much work it saves or what error rate would be acceptable in production.",
    ),
    (
        "<strong>Más personas.</strong> Casi toda la evaluación humana es mía, y la muestra es pequeña. Falta un segundo evaluador.",
        "<strong>More people.</strong> Almost all the human evaluation is mine, and the sample is small. It needs a second evaluator.",
    ),
    (
        "<strong>Reseñas trampa.</strong> Cuando detecta instrucciones ocultas o una broma, la respuesta es irónica a propósito (p02, adv-inyeccion, vampiros). Yo la doy por buena en contexto, pero el juez la suspende por tono. Mejora pendiente: una respuesta neutra cuando se detecta una inyección.",
        "<strong>Trap reviews.</strong> When it detects hidden instructions or a joke, the reply is deliberately ironic (p02, adv-inyeccion, vampiros). I accept it in context, but the judge fails the tone. Pending improvement: a neutral reply when an injection is detected.",
    ),
    (
        "<strong>Confianza del clasificador.</strong> Es la probabilidad media de la clase elegida en las 3 semillas del ensamble. Casi nunca pasa de 0,93, así que todavía no se puede leer como una probabilidad real de acierto.",
        "<strong>Classifier confidence.</strong> It is the mean probability of the chosen class across the ensemble's 3 seeds. It almost never exceeds 0.93, so it cannot yet be read as a true probability of being right.",
    ),
    ('id="evidencia">Evidencia</h2>', 'id="evidencia">Evidence</h2>'),
    (
        'Cada cifra de esta página sale de un fichero del repositorio. Aquí están todas, con su tamaño de muestra y su origen. Construí el proyecto con Claude Code: <a href="__REPO__#cómo-se-hizo">qué decidí yo y qué se hizo con la herramienta</a>.',
        'Every figure on this page comes from a file in the repository. Here they all are, with their sample size and source. I built the project with Claude Code: <a href="__REPO__#how-it-was-made">what I decided and what was done with the tool</a>.',
    ),
    ("<summary>Todos los resultados</summary>", "<summary>All the results</summary>"),
    (
        "Cada cifra enlaza a su fichero. Los intervalos de proporciones son de Wilson; los de F1 vienen del bootstrap de cada informe. La calibración usa la rúbrica v2, y producción usa v2g.",
        "Each figure links to its file. Intervals on proportions are Wilson intervals; those on F1 come from each report's bootstrap. Calibration used rubric v2, and production uses v2g.",
    ),
    (
        "<summary>El juez frente a mi valoración</summary>",
        "<summary>The judge against my rating</summary>",
    ),
    ("<summary>Conjuntos de evaluación</summary>", "<summary>Evaluation sets</summary>"),
    (
        "Miden cosas distintas y apenas se solapan, así que no hay una única «n» del sistema.",
        "They measure different things and barely overlap, so the system has no single “n”.",
    ),
    (
        ">repositorio</a> (código MIT). Página generada con <code>scripts/build_replay.py</code> a partir de resultados versionados. Las reseñas reales del visor proceden del corpus <a",
        ">repository</a> (MIT code). Page generated with <code>scripts/build_replay.py</code> from versioned results. The viewer's real reviews come from the <a",
    ),
    (
        "</a> (CC BY-NC 4.0), de origen TripAdvisor. Los hoteles y sus fichas son ficticios.",
        "</a> corpus (CC BY-NC 4.0), originally from TripAdvisor. The hotels and their fact sheets are fictional.",
    ),
    # Código de la página
    ('.replace(".", ",");', ";"),
    ('"Cumple lo esperado"', '"Meets expectations"'),
    ('"Cumple en parte"', '"Partly meets expectations"'),
    ('"No cumple lo esperado"', '"Does not meet expectations"'),
    ("`Reseña ${i + 1}`", "`Review ${i + 1}`"),
    ('"Sin hotel concreto"', '"No specific hotel"'),
    ('"Quitar esta reseña"', '"Remove this review"'),
    (
        'field("Título (opcional)", title), field("Reseña", text)',
        'field("Title (optional)", title), field("Review", text)',
    ),
    ('"Escribe el texto de cada reseña."', '"Write the text of each review."'),
    (
        '"El nick debe tener de 2 a 30 letras, números, punto, guion o guion bajo."',
        '"The nickname must have 2 to 30 letters, numbers, dots, hyphens or underscores."',
    ),
    ('"Indica dónde enviarte el resultado."', '"Say where to send the result."'),
    ('"Para enviar hace falta marcar la casilla."', '"You need to tick the box to send."'),
    ('"Enviado. Gracias."', '"Sent. Thank you."'),
    ('"Enviando…"', '"Sending…"'),
    (
        '"Enviado. Gracias: te escribiré al contacto que has dejado."',
        '"Sent. Thank you: I will write to the contact you left."',
    ),
    (
        '"No se ha podido enviar. Escríbeme por LinkedIn, por favor."',
        '"It could not be sent. Please write to me on LinkedIn."',
    ),
    ('"Reseñas de prueba · criterio escrito antes"', '"Test reviews · criteria written before"'),
    ('"Casos ilustrativos · nota escrita después"', '"Illustrative cases · note written after"'),
    (
        'const gate = c.decision === PUB ? "se publica sola" : "pasa a una persona";',
        'const gate = c.decision === PUB ? "published on its own" : "goes to a person";',
    ),
    ('"(sin respuesta)"', '"(no reply)"'),
    (
        '"Criterio escrito antes de generar" : "Caso ilustrativo, nota posterior"',
        '"Criteria written before generating" : "Illustrative case, note written after"',
    ),
    ('item("Mi valoración"', 'item("My rating"'),
    ('"sin valorar"', '"not rated"'),
    ('item("Juez"', 'item("Judge"'),
    ('"no se aplica"', '"not applicable"'),
    (
        'item("Puerta", pub ? pill("ok", "auto", "se publica sola") : pill("partial", "human", "pasa a una persona"))',
        'item("Gate", pub ? pill("ok", "auto", "published on its own") : pill("partial", "human", "goes to a person"))',
    ),
    (
        '"El juez no detecta este fallo: aquí decide una persona."',
        '"The judge does not detect this failure: here a person decides."',
    ),
    (
        '"En este caso el juez es más estricto que yo."',
        '"In this case the judge is stricter than I am."',
    ),
    (
        '"Escrito antes de generar" : "Nota escrita después de leer la respuesta"',
        '"Written before generating" : "Note written after reading the reply"',
    ),
    (
        '"Qué se esperaba de una buena respuesta" : "Por qué está aquí"',
        '"What a good reply should do" : "Why it is here"',
    ),
    (
        'c.hotel === "Sin ficha" ? "Hotel sin ficha"',
        'c.hotel === "No fact sheet" ? "Hotel without a fact sheet"',
    ),
    ('pub ? "Publicar" : "A revisión"', 'pub ? "Publish" : "To review"'),
    ('pub ? "sin revisión" : "pasa a una persona"', 'pub ? "without review" : "goes to a person"'),
    ('el("span", "Mi valoración", "who")', 'el("span", "My rating", "who")'),
    ('el("button", "Ver más", "more")', 'el("button", "Show more", "more")'),
    ('open ? "Ver más" : "Ver menos"', 'open ? "Show more" : "Show less"'),
    ('el("h3", "Motivos de la puerta")', 'el("h3", "Reasons from the gate")'),
    (
        '`Inspección del juez: ${total - failed} de ${total} ` : "Inspección del juez: no se aplica a una reseña trampa "',
        '`Judge inspection: ${total - failed} of ${total} ` : "Judge inspection: not applicable to a trap review "',
    ),
    (
        '"Gemma 4 12B, de otra familia que el generador"',
        '"Gemma 4 12B, a different family from the generator"',
    ),
    ('j.cumple ? "cumple" : "no cumple"', 'j.cumple ? "passes" : "fails"'),
    (
        'add("Sentimiento (mRoBERTa, media de 3 semillas)", `${c.sentiment}, confianza ${fmt(c.confidence, 3)} (umbral ${fmt(DATA.umbral, 2)}). ${probs}`)',
        'add("Sentiment (mRoBERTa, mean of 3 seeds)", `${c.sentiment}, confidence ${fmt(c.confidence, 3)} (threshold ${fmt(DATA.umbral, 2)}). ${probs}`)',
    ),
    (
        'add("Políticas recuperadas", c.politicas.join(", ") || "ninguna")',
        'add("Retrieved policies", c.politicas.join(", ") || "none")',
    ),
    (
        'add("Peticiones detectadas", c.peticiones.join(", ") || "ninguna")',
        'add("Requests detected (in Spanish)", c.peticiones.join(", ") || "none")',
    ),
    (
        'el("span", "Ficha del hotel", "label")',
        'el("span", "Hotel fact sheet (in Spanish)", "label")',
    ),
    ("`Paso ${step + 1} de ${tour.length}`", "`Step ${step + 1} of ${tour.length}`"),
]


def apply_ui(page: str) -> str:
    for es, en in UI:
        assert es in page, f"la plantilla ya no contiene: {es[:70]}"
        page = page.replace(es, en)
    return page


def reason(text: str) -> str:
    """Motivos de la puerta. Lo que escribe el modelo (peticiones, motivo de trampa) sigue en español."""
    sent = EN["sentimientos"]
    if text in EN["motivos"]:
        return EN["motivos"][text]
    if m := re.fullmatch(r"confianza ([\d.]+) < ([\d.]+)", text):
        return f"confidence {m[1]} < {m[2]}"
    if m := re.fullmatch(r"el clasificador \((\w+)\) y el LLM \((\w+)\) no coinciden", text):
        return f"classifier ({sent[m[1]]}) and LLM ({sent[m[2]]}) disagree"
    if text.startswith("el cliente pide: "):
        return "the guest asks (in Spanish): " + text.removeprefix("el cliente pide: ")
    if text.startswith("juez: "):
        return "judge: " + EN["criterios"][text.removeprefix("juez: ")]
    if m := re.fullmatch(r"posible reseña trampa \((.*)\)", text, re.DOTALL):
        return f"possible trap review (model's note, in Spanish: {m[1]})"
    raise AssertionError(f"motivo sin traducir: {text}")


def case(c: dict, highlights) -> dict:
    """Copia traducida de un caso; `highlights` recalcula los resaltados con el texto en inglés."""
    t = EN["casos"][c["id"]]
    sent = EN["sentimientos"]
    out = c | {
        "titulo": t["titulo"],
        "tipo": EN["tipos"][c["tipo"]],
        "esperado": t.get("esperado", ""),
        "nota": t.get("nota", ""),
        "hotel": "No fact sheet" if c["hotel"] == "Sin ficha" else c["hotel"],
        "sentiment": sent[c["sentiment"]],
        "probs": {sent[k]: v for k, v in c["probs"].items()},
        "reasons": [reason(r) for r in c["reasons"]],
        "politicas": [EN["politicas"][p] for p in c["politicas"]],
        "judge": [j | {"criterio": EN["criterios"][j["criterio"]]} for j in c["judge"]],
    }
    if c["valoracion"]:
        out["valoracion"] = c["valoracion"] | {"motivo": t["motivo"]}
    extra = t.get("motivo") or t.get("nota", "")
    out["highlights"] = highlights(c["id"], extra, "My rating" if c["valoracion"] else "Note")
    return out


def tour(steps: list[dict]) -> list[dict]:
    extra = EN["recorrido_extra"]
    return [s | {"ensena": extra.get(s["id"]) or EN["casos"][s["id"]]["ensena"]} for s in steps]
