"""Cifras de la página de repetición: todas salen de ficheros del repo, ninguna se escribe a mano.

Lee resultados e informes versionados, calcula los intervalos de Wilson de las proporciones y devuelve
las frases y tablas ya en HTML. Si un informe cambia de formato, falla: mejor un error que una cifra
vieja. `build_replay.py` lo usa al generar la página.
"""
# ruff: noqa: E501  (filas de tablas: partirlas las haría menos legibles)

import json
import math
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REALISTA = "results/phase3b_realista.json"
COLA = "results/pipeline_cola.json"
PROPIAS = "results/demo_propias.json"
SEMILLAS = "results/phase6_semillas.json"
CALIBRACION = "reports/phase6_calibracion.md"
CIEGAS = "reports/phase9_ciegas.md"
LATENCIA = "reports/phase9_latencia.md"
MAPA = "evals/gold/calibracion_mapa.json"
GOLD = "evals/gold/semillas_fase4.json"
Z_95 = 1.96
EN = json.loads((ROOT / "evals" / "demo" / "replay_en.json").read_text(encoding="utf-8"))["tablas"]
_english = False
# Admisiones implícitas señaladas al leer: casos, no una tasa
JUDGE_MISSES = ("p08", "rag-carteles")


def set_english(on: bool) -> None:
    global _english
    _english = on


def t(es: str, en: str) -> str:
    return en if _english else es


def cell(text: str) -> str:
    """Celda fija de una tabla, en el idioma de la página."""
    return EN.get(text, text) if _english else text


def wilson(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Intervalo de Wilson de la proporción k/n: se porta bien con n pequeño y con 0 o n aciertos."""
    p = k / n
    den = 1 + z**2 / n
    mid = (p + z**2 / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def num(x: float, digits: int) -> str:
    text = f"{x:.{digits}f}"
    return text if _english else text.replace(".", ",")


def miles(n: int) -> str:
    return f"{n:,}" if _english else f"{n:,}".replace(",", ".")


def pct(x: float, digits: int = 0) -> str:
    return f"{num(x * 100, digits)}%" if _english else f"{num(x * 100, digits)} %"


def share(k: int, n: int) -> str:
    return f"{miles(k)} {t('de', 'of')} {miles(n)} ({pct(k / n, 1 if k / n < 0.1 else 0)})"


def wilson_text(k: int, n: int) -> str:
    low, high = wilson(k, n)
    return f"{pct(low, 1)} {t('a', 'to')} {pct(high, 1)}"


def _json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _find(pattern: str, rel: str) -> tuple[str, ...]:
    m = re.search(pattern, _text(rel))
    assert m, f"{rel} no tiene el formato esperado: {pattern}"
    return m.groups()


def facts() -> dict:
    realista, cola = _json(REALISTA), _json(COLA)
    ahr, coah = realista["ahr_ood"], realista["stress"]["original"]
    real = [it for it in cola if it["meta"]["grupo"] == "AHR"]
    low = [it for it in real if it["meta"]["rating"] <= 3]
    propias = {it["id"]: it for it in _json(PROPIAS)}
    both = {it["id"]: it for it in cola} | propias
    for case in JUDGE_MISSES:
        assert all(v["cumple"] for v in both[case]["judge"].values()), f"el juez suspende {case}"
    seeds = _json(SEMILLAS)["respuestas_juez_frente_a_persona"]["v2"]
    judge_n, person_n, shared = map(int, _find(
        r"\*\*Respuesta\*\* \(suspende algún criterio\) \| (\d+) \| (\d+) \| (\d+) \|", CALIBRACION))  # fmt: skip
    win_a, win_b = map(int, _find(r"\| Preferida \| (\d+) \| (\d+) \|", CIEGAS))
    pub_a, blind_n = map(int, _find(r"\| Publicable tal cual \| (\d+)/(\d+) \|", CIEGAS))
    ties, blank = map(int, _find(r"Empates: (\d+); sin valorar: (\d+)", CIEGAS))
    p_value = _find(r"p = (\d\.\d+)", CIEGAS)[0]
    lat_n, median, p90 = _find(r"\| Todas \| (\d+) \| [\d.]+ / [\d.]+ \[[^\]]+\] \| [\d.]+ / [\d.]+ "
                               r"\[[^\]]+\] \| [^|]+ \| ([\d.]+) / ([\d.]+) ", LATENCIA)  # fmt: skip
    return {
        "n_coah": int(_find(r"variantes de `coah_test` \(n=(\d+)\)", "reports/phase3b_realista.md")[0]),
        "versiones_calibracion": len({v.split(":")[0] for v in _json(MAPA).values()}),
        "leak": _find(r"el \*\*([\d.]+)%\*\* de las", "reports/data_report.md")[0],
        "ahr": ahr, "coah": coah, "sfu": realista["sfu_hoteles"],
        "ahr_cov": ahr["coverage"]["solo_confianza"],
        "coah_cov": realista["coverage"]["solo_confianza"]["test_at_threshold"],
        "n_cola": len(cola), "n_real": len(real), "n_sint": len(cola) - len(real),
        "publicables": sum(it["decision"] == "publicable" for it in cola),
        "low": len(low), "low_pub": sum(it["decision"] == "publicable" for it in low),
        "juez_marca": judge_n, "persona_marca": person_n, "coinciden": shared,
        "n_calibracion": len(_json(MAPA)),
        "kappa": _find(r"\| No admite culpa ni responsabilidad \| 3 \| [^|]+ \| ([\d.]+) · ", CALIBRACION)[0],
        "semillas": seeds, "n_semillas": len(_json(GOLD)["items"]),
        "ciegas": {"v6": win_a, "v9": win_b, "empates": ties, "sin_valorar": blank, "n": blind_n,
                   "publicable_v6": pub_a, "p": p_value},
        "latencia": (median, p90), "n_latencia": int(lat_n),
    }  # fmt: skip


def source(rel: str, repo: str) -> str:
    return f'<a href="{repo}/blob/main/{rel}">{escape(Path(rel).name)}</a>'


def cases_intro(tour_steps: int) -> str:
    return t(f"Empieza por la guía orientativa: {tour_steps} casos, de un acierto claro al fallo que el juez no ve.",
             f"Start with the guided tour: {tour_steps} cases, from a clean success to the failure the judge misses.")  # fmt: skip


def how(f: dict, threshold: float, criteria: int) -> str:
    ahr, none = f["ahr"], t("ninguna", "none")
    neutral = num(ahr["f1_per_class"]["neutral"], 3)
    seconds = num(float(f["latencia"][0]), 0)
    if _english:
        steps = [
            ("1. Understand the review",
             "A classifier decides whether the review is negative, neutral or positive, and how confident "
             "it is. It is mRoBERTa, a model trained for Spanish that I fine-tuned on real reviews, averaged "
             f"over three seeds. On {miles(ahr['n'])} reviews it never saw in training, it reaches a macro "
             f"F1 of {num(ahr['f1_macro'], 3)}: a score from 0 to 1 that weighs all three classes equally. "
             f"The neutral class, the hardest, stays at {neutral}."),
            ("2. Find what it can say",
             "A language model writes well, but it tends to <b>make things up</b>. To limit that, it gets the hotel's full "
             "fact sheet and, through RAG, the policies and approved replies closest to this review. RAG "
             "(Retrieval-Augmented Generation) here means finding the relevant documents and handing them to "
             "the model before it writes. For "
             "policies, it combines search by keywords (BM25) and by meaning (bge-m3 embeddings)."),
            ("3. Draft and check",
             "Qwen3.6 27B, an LLM running locally, works out what the guest is talking about and drafts the "
             "reply. Two filters then check it: fixed rules (services missing from the fact sheet, "
             "compensation, people's names) and a second model, Gemma 4 12B, which I call the judge. It "
             f"comes from another family so it does not share the generator's biases: it answers yes or no "
             f"to {criteria} criteria and quotes the sentence behind each failure."),
            ("4. Decide who publishes",
             f"The gate makes the final decision. Negative and neutral reviews, doubtful ones (confidence below "
             f"{num(threshold, 2)}), traps and any accident or legal risk go to a person. Of the "
             f"{f['n_cola']} reviews in the test, {f['publicables']} pass every check. Of the {f['low']} "
             f"real 1 to 3★ reviews, {f['low_pub'] or none} was published without review. It is not "
             f"auto-publishing: it prepares drafts, at a median of {seconds} s per review on one PC."),
        ]  # fmt: skip
    else:
        steps = [
            ("1. Entender la reseña",
             "Un clasificador decide si la reseña es negativa, neutral o positiva, y con cuánta confianza. "
             "Es mRoBERTa, un modelo entrenado para español que ajusté con reseñas reales (fine-tuning), "
             f"promediando tres semillas. En {miles(ahr['n'])} reseñas que no vio al entrenar saca un F1 "
             f"macro de {num(ahr['f1_macro'], 3)}: una nota de 0 a 1 que da el mismo peso a las tres clases. "
             f"La neutral, la más difícil, se queda en {neutral}."),
            ("2. Buscar lo que se puede decir",
             "Un modelo de lenguaje redacta bien, pero tiende a <b>inventar</b>. Para limitarlo, recibe la ficha completa del "
             "hotel y, mediante RAG, las políticas y las respuestas aprobadas más parecidas a esta reseña. "
             "RAG (Retrieval-Augmented Generation) en este caso consiste en buscar los documentos pertinentes "
             "y dárselos al modelo antes de que escriba. "
             "En las políticas combina búsqueda por palabras (BM25) y por significado (embeddings de bge-m3)."),
            ("3. Redactar y revisar",
             "Qwen3.6 27B, un LLM que corre en local, identifica de qué habla el cliente y redacta el "
             "borrador. Después lo revisan dos filtros: reglas fijas (servicios que no están en la ficha, "
             "compensaciones, nombres de personas) y un segundo modelo, Gemma 4 12B, al que llamo juez. Es "
             f"de otra familia para no compartir los sesgos del generador: contesta sí o no a {criteria} "
             "criterios y cita la frase que justifica cada suspenso."),
            ("4. Decidir quién publica",
             f"La puerta toma la decisión final. Lo negativo, lo neutral, lo dudoso (confianza por debajo de "
             f"{num(threshold, 2)}), las trampas y cualquier accidente o riesgo legal pasan a una persona. "
             f"De las {f['n_cola']} reseñas de la prueba, {f['publicables']} superan todos los controles. "
             f"De las {f['low']} reales de 1 a 3★, {f['low_pub'] or none} se publicó sin revisión. No es "
             f"autopublicación: prepara borradores, con una mediana de {seconds} s por reseña en un PC."),
        ]  # fmt: skip
    return _blocks(steps, "steps pairs")


def lessons(f: dict, repo: str) -> str:
    report = (
        f"{repo}/blob/main/reports/data_report.md#5-reproducción-de-la-fuga-del-proyecto-original"
    )
    c = f["ciegas"]
    fp = f["juez_marca"] - f["coinciden"]
    cases = t(" y ", " and ").join(f'<a href="#{i}">{i}</a>' for i in JUDGE_MISSES)
    if _english:
        items = [
            ("The first figures were worthless",
             f"This project began as an earlier version that appeared to work, but the result was very poor, "
             f"so I audited it: "
             f"{f['leak']}% of the final exam (the test set) also appeared, word for word, in the training "
             f"data. The model already knew the answers. This is called data leakage "
             f"(<a href=\"{report}\">reproduction</a>). It also picked the model with that same exam and had "
             "never seen a 4★ review. I rebuilt it from scratch: duplicates removed before splitting, and a "
             "separate validation set."),
            ("More variety did not mean better replies",
             "Almost every reply opens the same way, so I tried more varied versions of the prompt, the "
             f"model's instructions. Comparing them blind, without knowing which was which, I preferred the "
             f"current one on {c['v6']} reviews and the newer one on {c['v9']}, a difference that could be "
             f"chance (p = {num(float(c['p']), 2)}). I kept the current one, and the replies are still repetitive. "
             "I will try again when I have more reviews, so as not to fit the "
             "prompt to these same cases and overfit."),
            ("An automatic evaluator has to be evaluated too",
             f"I compared the judge with my own blind labels on {f['n_calibracion']} replies. It failed "
             f"{f['juez_marca']} and I failed {f['persona_marca']}, all of them among its {f['juez_marca']}: "
             f"it missed none of mine, with {fp} false alarms. The sample is small, and reading other "
             f"replies I found implicit admissions of fault that it lets through ({cases}). So "
             "anything delicate always has to go to a person."),
        ]  # fmt: skip
    else:
        items = [
            ("Las primeras cifras no valían",
             "Este proyecto nació de una versión anterior que en apariencia funcionaba, pero el resultado era "
             "muy deficiente, de modo que la audité: el "
             f"{f['leak'].replace('.', ',')} % del examen final (el test) estaba también, letra por letra, "
             "en los datos de entrenamiento. El modelo se sabía las respuestas. Es lo que se llama fuga de "
             f"datos (<a href=\"{report}\">reproducción</a>). Además, elegía el modelo con ese mismo examen y "
             "nunca había visto una reseña de 4★. Lo rehíce desde cero: duplicados fuera antes de separar "
             "los datos y un conjunto de validación aparte."),
            ("Más variedad no significó mejores respuestas",
             "Casi todas las respuestas empiezan igual, así que probé versiones más variadas del prompt, las "
             "instrucciones que recibe el modelo. Al compararlas a ciegas, sin saber cuál era cuál, preferí "
             f"la actual en {c['v6']} reseñas y la nueva en {c['v9']}, una diferencia que podría ser azar "
             f"(p = {num(float(c['p']), 2)}). Me quedé con la actual, y las respuestas siguen siendo repetitivas. "
             "Volveré a intentarlo cuando disponga de más reseñas, para no ajustar "
             "el prompt a estos mismos casos y provocar sobreajuste."),
            ("A un evaluador automático también hay que evaluarlo",
             f"Comparé al juez con mis etiquetas, puestas a ciegas, en {f['n_calibracion']} respuestas. "
             f"Suspendió {f['juez_marca']} y yo {f['persona_marca']}, todas dentro de sus {f['juez_marca']}: "
             f"no se le escapó ninguna de las mías, con {fp} falsas alarmas. La muestra es pequeña, y al "
             f"leer otras respuestas encontré admisiones implícitas de culpa que deja pasar ({cases}). Eso "
             "obliga a que lo delicado pase siempre por una persona."),
        ]  # fmt: skip
    return _blocks(items)


def _blocks(items: list[tuple[str, str]], cls: str = "steps") -> str:
    body = "".join(f"<div><h3>{title}</h3><p>{text}</p></div>" for title, text in items)
    return f'<div class="{cls}">{body}</div>'


def result_rows(f: dict) -> list[tuple]:
    ahr, coah, sfu, c = f["ahr"], f["coah"], f["sfu"], f["ciegas"]
    cov_a, cov_c, seeds = f["ahr_cov"], f["coah_cov"], f["semillas"]
    hits = round(sfu["accuracy"] * sfu["n"])
    decided = c["v6"] + c["v9"]
    prop = lambda k, n: (share(k, n), wilson_text(k, n))  # noqa: E731
    interval = lambda v: f"{num(v[0], 3)} {t('a', 'to')} {num(v[1], 3)}"  # noqa: E731
    return [
        ("AHR, nunca usado para entrenar", ahr["n"], "F1 macro", num(ahr["f1_macro"], 3),
         interval(ahr["ci95"]), REALISTA),
        ("AHR", ahr["n"], "F1 de la clase neutral", num(ahr["f1_per_class"]["neutral"], 3), "—", REALISTA),
        ("AHR, confianza ≥ 0,85", cov_a["auto_n"], "Error", *prop(cov_a["errors_n"], cov_a["auto_n"]), REALISTA),
        ("Test limpio de COAH", f["n_coah"], "F1 macro", num(coah["f1_macro"], 3), interval(coah["ci95"]), REALISTA),
        ("COAH, confianza ≥ 0,85", cov_c["auto_n"], "Error", *prop(cov_c["errors_n"], cov_c["auto_n"]), REALISTA),
        ("SFU, otra web", sfu["n"], "Aciertos", *prop(hits, sfu["n"]), REALISTA),
        ("Calibración, rúbrica v2", f["n_calibracion"], "Precisión del juez", *prop(f["coinciden"], f["juez_marca"]), CALIBRACION),
        ("Calibración, rúbrica v2", f["n_calibracion"], "Recall del juez", *prop(f["coinciden"], f["persona_marca"]), CALIBRACION),
        ("Calibración, rúbrica v2", f["n_calibracion"], "Kappa en «no admite culpa»", num(float(f["kappa"]), 2), "—", CALIBRACION),
        ("Semillas, rúbrica v2", f["n_semillas"], "Fallos de la persona que detecta el juez",
         *prop(seeds["coinciden"], seeds["referencia"]), SEMILLAS),
        ("Cola de demostración", f["n_cola"], "Pasan todos los controles", *prop(f["publicables"], f["n_cola"]), COLA),
        ("Reales de 1 a 3★", f["low"], "Publicadas sin revisión (por diseño)", *prop(f["low_pub"], f["low"]), COLA),
        ("Comparación a ciegas, v6 y v9", decided, t(f"Prefiere v6, sin {c['empates']} empates (p = {num(float(c['p']), 2)})", f"Prefers v6, excluding {c['empates']} ties (p = {num(float(c['p']), 2)})"),
         *prop(c["v6"], decided), CIEGAS),
        ("Comparación a ciegas, v6", c["n"], "Publicable tal cual", *prop(c["publicable_v6"], c["n"]), CIEGAS),
        ("Latencia en un PC", f["n_latencia"], "Mediana hasta el veredicto",
         f"{num(float(f['latencia'][0]), 1)} s (p90 {num(float(f['latencia'][1]), 1)} s)", "—", LATENCIA),
    ]  # fmt: skip


def set_rows(f: dict, shown: int, own: int) -> list[tuple]:
    c = f["ciegas"]
    return [
        ("Test limpio de COAH", str(f["n_coah"]), "Real, TripAdvisor", "Medir el clasificador"),
        ("AHR", miles(f["ahr"]["n"]), "Real, TripAdvisor, 2021", "Medir el clasificador con reseñas que no vio"),
        ("SFU", str(f["sfu"]["n"]), "Real, ciao.es", "Medirlo con otra web"),
        ("Cola de demostración", str(f["n_cola"]), t(f"{f['n_sint']} sintéticas y {f['n_real']} reales del AHR", f"{f['n_sint']} synthetic and {f['n_real']} real from AHR"), "Sistema completo y puerta"),
        ("Comparación a ciegas", t(f"{c['n']}, valoradas {c['n'] - c['sin_valorar']}", f"{c['n']}, {c['n'] - c['sin_valorar']} rated"), "Escritas por mí", "Elegir entre versiones del prompt"),
        ("Calibración", str(f["n_calibracion"]), t(f"Respuestas de {f['versiones_calibracion']} versiones del prompt", f"Replies from {f['versiones_calibracion']} prompt versions"), "Juez frente a una persona"),
        ("Semillas", str(f["n_semillas"]), "Respuestas de las primeras versiones", "Fallos reales del generador"),
        ("Selector de esta página", str(shown), t(f"{own} escritas por mí y {shown - own} ilustrativas", f"{own} written by me and {shown - own} illustrative"), "Enseñar casos; no es una muestra"),
    ]  # fmt: skip


def matrix(cases: list[dict]) -> dict[tuple[bool, bool], list[str]]:
    """Casos con veredicto del autor, por (el juez aprueba, el autor dice que cumple)."""
    cells = {(j, a): [] for j in (True, False) for a in (True, False)}
    for c in cases:
        verdict = (c.get("valoracion") or {}).get("veredicto")
        if verdict:
            approves = all(row["cumple"] for row in c["judge"])
            cells[(approves, verdict == "cumple")].append(c["id"])
    return cells


def matrix_note(cells: dict) -> str:
    total = sum(map(len, cells.values()))
    fails = sum(len(v) for (_, ok), v in cells.items() if not ok)
    if _english:
        return (f"Only {total} cases have my verdict, with the criteria written before generating, and "
                f"{fails} fails: the matrix shows which cases they are, it does not measure the judge. Each "
                "ID opens the case in the viewer.")  # fmt: skip
    return (f"Solo {total} casos tienen mi veredicto, con el criterio escrito antes de generar, y "
            f"{fails} no cumple: la matriz enseña qué casos son, no mide al juez. Cada identificador "
            "abre el caso en el visor.")  # fmt: skip


def matrix_table(cells: dict) -> str:
    def cell(approves: bool, fine: bool) -> str:
        ids = cells[(approves, fine)]
        return (
            "<td>"
            + (
                " ".join(f'<a href="#{i}"><code>{i}</code></a>' for i in ids)
                or t("Ninguno", "None")
            )
            + "</td>"
        )

    head = (f'<tr><td></td><th scope="col">{t("Yo: cumple", "Me: passes")}</th>'
            f'<th scope="col">{t("Yo: no cumple", "Me: fails")}</th></tr>')  # fmt: skip
    rows = "".join(f'<tr><th scope="row">{name}</th>{cell(v, True)}{cell(v, False)}</tr>'
                   for name, v in ((t("El juez aprueba", "Judge approves"), True), (t("El juez suspende", "Judge fails"), False)))  # fmt: skip
    return f'<table class="data matrix"><thead>{head}</thead><tbody>{rows}</tbody></table>'


def results_table(f: dict, repo: str) -> str:
    names = (
        t("Conjunto", "Set"),
        "n",
        t("Métrica", "Metric"),
        t("Valor", "Value"),
        t("IC 95 %", "95% CI"),
        t("Origen", "Source"),
    )
    head = "<tr>" + "".join(f"<th>{x}</th>" for x in names) + "</tr>"
    body = "".join(
        f'<tr><td>{escape(cell(a))}</td><td class="n">{miles(n)}</td><td>{escape(cell(m))}</td><td>{escape(v)}</td>'
        f"<td>{escape(ci)}</td><td>{source(rel, repo)}</td></tr>"
        for a, n, m, v, ci, rel in result_rows(f)
    )
    return f'<table class="data"><thead>{head}</thead><tbody>{body}</tbody></table>'


def sets_table(f: dict, shown: int, own: int) -> str:
    names = (t("Conjunto", "Set"), t("Tamaño", "Size"), t("Origen", "Origin"), t("Uso", "Use"))
    head = "<tr>" + "".join(f"<th>{x}</th>" for x in names) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td>{escape(cell(x))}</td>" for x in row) + "</tr>"
                   for row in set_rows(f, shown, own))  # fmt: skip
    return f'<table class="data"><thead>{head}</thead><tbody>{body}</tbody></table>'
