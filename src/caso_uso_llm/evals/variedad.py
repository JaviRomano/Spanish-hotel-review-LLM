"""Variedad de las aperturas en una ejecución: comprobación determinista, sin modelos.

Convierte en cifras lo repetitivas que son las respuestas de una tanda: saludos, frases de apertura
distintas (la primera frase tras el saludo, completa y normalizada) y cuántas abren dando las
gracias. Una respuesta suelta puede estar bien y el conjunto delatar una plantilla, así que esto se
mide sobre la ejecución entera, no por respuesta. Informa, no decide.

Uso: uv run just variedad                       # results/pipeline_cola.json -> reports/phase9_variedad.md
     uv run just variedad data/live/salida.json  # otra ejecución: solo por consola, no escribe informe
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from caso_uso_llm.paths import RESULTS, ROOT

SALUDO = re.compile(r"^\s*(?:Estimad[oa]s?|Hola|Buenas|Saludos)\b", re.IGNORECASE)
GRACIAS = re.compile(r"^(?:muchas )?gracias por\b")
COMPARTIR = re.compile(r"^(?:muchas )?gracias por compartir\b")
DEFAULT = RESULTS / "pipeline_cola.json"
REPORT = ROOT / "reports" / "phase9_variedad.md"
TOP = 10
START_WORDS = 4  # el inicio: delata fórmulas que cambian solo al final de la frase


def opening(response: str) -> tuple[str, str]:
    """(saludo, primera frase tras el saludo); el saludo va vacío si la respuesta no lo tiene."""
    lines = [x.strip() for x in response.strip().splitlines() if x.strip()]
    greeting = ""
    if lines and SALUDO.match(lines[0]) and len(lines) > 1:
        greeting, lines = lines[0], lines[1:]
    return greeting, re.split(r"(?<=[.!?])\s", lines[0])[0] if lines else ""


def normalize(sentence: str) -> str:
    """Sin mayúsculas ni puntuación: dos frases que solo difieren en eso son la misma apertura."""
    return " ".join(re.sub(r"[^\w\s]", " ", sentence.casefold()).split())


def measure(responses: list[str]) -> dict:
    pairs = [opening(r) for r in responses]
    greetings = Counter(g for g, _ in pairs)
    firsts = Counter(normalize(f) for _, f in pairs)
    starts = Counter(" ".join(f.split()[:START_WORDS]) for f in firsts.elements())
    top_start, top_start_n = starts.most_common(1)[0] if starts else ("", 0)
    top_greeting, top_greeting_n = greetings.most_common(1)[0] if greetings else ("", 0)
    return {
        "n": len(responses),
        "saludo_top": top_greeting,
        "saludo_top_n": top_greeting_n,
        "saludos_distintos": len(greetings),
        "frases_distintas": len(firsts),
        "inicio_top": top_start,
        "inicio_top_n": top_start_n,
        "gracias_por": sum(n for f, n in firsts.items() if GRACIAS.match(f)),
        "gracias_por_compartir": sum(n for f, n in firsts.items() if COMPARTIR.match(f)),
        "top": firsts.most_common(TOP),
    }


def read_responses(path: Path) -> list[str]:
    return [it["response"] for it in json.loads(path.read_text(encoding="utf-8"))
            if it.get("response")]  # fmt: skip


def write_report(m: dict, source: Path) -> None:
    n = m["n"]
    L = [
        "# Fase 9 · Variedad de las aperturas",
        "",
        f"Generado por `uv run just variedad` a partir de `{source.relative_to(ROOT).as_posix()}`, sin "
        "modelos. La primera frase es la que sigue al saludo, completa, sin mayúsculas ni puntuación. "
        "No editar a mano.",
        "",
        "| Medida | Valor |",
        "|---|---|",
        f"| Respuestas | {n} |",
        f"| Saludo más repetido (`{m['saludo_top']}`) | {m['saludo_top_n']} de {n} |",
        f"| Saludos distintos | {m['saludos_distintos']} |",
        f"| Primeras frases distintas | {m['frases_distintas']} de {n} |",
        f"| Inicio más repetido («{m['inicio_top']}…») | {m['inicio_top_n']} de {n} |",
        f"| Abren con «gracias por…» | {m['gracias_por']} de {n} ({m['gracias_por'] / n:.0%}) |",
        f"| Abren con «gracias por compartir…» | {m['gracias_por_compartir']} de {n} "
        f"({m['gracias_por_compartir'] / n:.0%}) |",
        "",
        f"## Primeras frases más repetidas (hasta {TOP})",
        "",
        "| Veces | Frase |",
        "|---|---|",
        *[f"| {count} | {sentence or '(vacía)'} |" for sentence, count in m["top"]],
        "",
    ]
    REPORT.write_text("\n".join(L), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ruta", nargs="?", type=Path, default=DEFAULT)
    source = parser.parse_args().ruta.resolve()
    m = measure(read_responses(source))
    if source == DEFAULT:  # otras ejecuciones pueden traer reseñas de terceros: nada se versiona
        write_report(m, source)
    print({k: v for k, v in m.items() if k != "top"})


if __name__ == "__main__":
    main()
