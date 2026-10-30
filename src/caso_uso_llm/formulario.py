"""Importa las peticiones de prueba en vivo que llegan por el formulario de la página de repetición.

La página es estática: envía cada petición a un Google Form con una sola pregunta («datos»), que
guarda el JSON completo (nick, contacto y de 1 a 5 reseñas). Las respuestas se exportan a CSV y este
módulo las convierte al JSONL de `just recoger`, con el mismo enmascarado de datos personales:

    uv run just formulario ruta/respuestas.csv
    uv run just pipeline --jsonl data/live/resenas_formulario.jsonl

Texto de terceros: la salida va siempre a data/live/ (fuera de git). El contacto se guarda aparte,
para que nunca llegue a los modelos. Importar dos veces el mismo CSV no duplica nada.
"""

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from caso_uso_llm.data.normalize import mask_pii, normalize_text
from caso_uso_llm.paths import DATA, ROOT
from caso_uso_llm.rag import kb

LIVE = DATA / "live"
OUT = LIVE / "resenas_formulario.jsonl"
CONTACTS = LIVE / "peticiones_contacto.csv"
NICK = re.compile(r"^[\w.\-]{2,30}$")  # el mismo que la app y `recoger`
MAX_REVIEWS = 5
MAX_TEXT = 2000
DATES = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S")


def _date(stamp: str) -> str | None:
    for f in DATES:
        try:
            return datetime.strptime(stamp.strip(), f).isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def parse_row(stamp: str, raw: str, hotels: set[str]) -> tuple[list[dict], str]:
    """(reseñas, contacto) de una respuesta del Form. ValueError si no es una petición válida:
    el campo es texto libre en un formulario público, así que no se da nada por bueno."""
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError("no es JSON") from e
    if not isinstance(doc, dict) or doc.get("consentimiento") is not True:
        raise ValueError("sin consentimiento")
    nick = str(doc.get("nick", "")).strip()
    if not NICK.match(nick):
        raise ValueError("nick no válido")
    reviews = doc.get("resenas")
    if not isinstance(reviews, list) or not 1 <= len(reviews) <= MAX_REVIEWS:
        raise ValueError("número de reseñas fuera de rango")
    out = []
    for i, r in enumerate(reviews):
        text = str(r.get("text", "")).strip() if isinstance(r, dict) else ""
        if not text or len(text) > MAX_TEXT:
            raise ValueError("reseña vacía o demasiado larga")
        hotel = r.get("hotel") or None
        if hotel is not None and hotel not in hotels:
            raise ValueError("hotel desconocido")
        key = f"{stamp}\n{nick}\n{i}\n{text}".encode()
        out.append({
            "id": "form-" + hashlib.sha1(key).hexdigest()[:12],
            "fecha": _date(stamp), "nick": nick,
            "origen": "formulario: escrita por una persona", "consentimiento": True,
            "hotel": hotel,
            "title": mask_pii(normalize_text(str(r.get("title", ""))))[0].strip(),
            "text": mask_pii(normalize_text(text))[0],
        })  # fmt: skip
    return out, str(doc.get("contacto", "")).strip()


def _column(header: list[str], name: str) -> int:
    for i, h in enumerate(header):
        if h.strip().lower() == name:
            return i
    raise SystemExit(f"El CSV no tiene la columna «{name}»: {header}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path, help="CSV exportado de la hoja de respuestas del Form")
    args = ap.parse_args()
    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    data_col = _column(rows[0], "datos")
    hotels = set(kb.fichas())
    seen = set()
    if OUT.exists():
        seen = {json.loads(x)["id"] for x in OUT.read_text(encoding="utf-8").splitlines() if x}
    LIVE.mkdir(parents=True, exist_ok=True)
    new, bad = 0, 0
    with OUT.open("a", encoding="utf-8", newline="\n") as out, \
            CONTACTS.open("a", encoding="utf-8", newline="") as contacts:  # fmt: skip
        writer = csv.writer(contacts, delimiter=";")
        for row in rows[1:]:
            try:
                reviews, contact = parse_row(row[0], row[data_col], hotels)
            except (ValueError, IndexError) as e:
                bad += 1
                print(f"Descartada ({row[0] if row else '?'}): {e}")
                continue
            fresh = [r for r in reviews if r["id"] not in seen]
            for r in fresh:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
                seen.add(r["id"])
            if fresh:
                writer.writerow([fresh[0]["fecha"], fresh[0]["nick"], contact, len(fresh)])
            new += len(fresh)
    print(f"{new} reseñas nuevas, {bad} respuestas descartadas -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
