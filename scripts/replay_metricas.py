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


def headline(f: dict, repo: str) -> str:
    cases = t(" y ", " and ").join(f"<code>{c}</code>" for c in JUDGE_MISSES)
    if _english:
        return (f"Of the {f['low']} real 1 to 3★ reviews in the test, {f['low_pub'] or 'none'} was "
                f"published without review, and that is by design (<a href=\"{repo}/blob/main/{COLA}\">data</a>). "
                f"The judge let {len(JUDGE_MISSES)} implicit admissions of fault through ({cases}): these "
                "are cases flagged by reading the replies, not a rate.")  # fmt: skip
    return (f"De las {f['low']} reseñas reales de 1 a 3★ de la prueba, {f['low_pub'] or 'ninguna'} se "
            f"publicó sin revisión, y es así por diseño (<a href=\"{repo}/blob/main/{COLA}\">datos</a>). "
            f"El juez dejó pasar {len(JUDGE_MISSES)} admisiones implícitas de culpa ({cases}): son "
            "casos señalados al leer las respuestas, no una tasa.")  # fmt: skip


def rebuilt(f: dict, repo: str) -> str:
    report = (
        f"{repo}/blob/main/reports/data_report.md#5-reproducción-de-la-fuga-del-proyecto-original"
    )
    if _english:
        return (f"<strong>Why I rebuilt it:</strong> {f['leak']}% of the first version's test set was "
                f"literally in train (<a href=\"{report}\">reproduction</a>), so that F1 is worthless. On "
                f"clean data, the classifier reaches a macro F1 of {num(f['coah']['f1_macro'], 3)} on the "
                f"test set and {num(f['ahr']['f1_macro'], 3)} on {miles(f['ahr']['n'])} unseen reviews.")  # fmt: skip
    return (f"<strong>Por qué lo rehíce:</strong> el {f['leak'].replace('.', ',')} % del test de la "
            f"primera versión estaba literalmente en train (<a href=\"{report}\">reproducción</a>), "
            f"así que aquel F1 no sirve. Con los datos limpios, el clasificador saca un F1 macro de "
            f"{num(f['coah']['f1_macro'], 3)} en el test y de {num(f['ahr']['f1_macro'], 3)} en "
            f"{miles(f['ahr']['n'])} reseñas que no vio.")  # fmt: skip


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
