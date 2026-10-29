"""Medición de latencia por etapa (Fase 9). Desactivada, no hace nada.

Se activa con `enable(ruta)` (lo hace `just latencia`) o con la variable de entorno
CASO_LATENCIA=<ruta>. Cada reseña es un registro: `begin()` lo abre, `stage()` mide el tiempo de
pared de cada paso del pipeline, `record_ollama()` guarda las métricas que devuelve Ollama
(vienen en nanosegundos; aquí, en segundos) y `end()` lo escribe como una línea del JSONL.

Una llamada que sale de la caché de resultados no mide nada: queda marcada con `cached=True`.
El registro no guarda texto de la reseña ni de la respuesta, solo ids, tiempos y modelos.
"""

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

ENV = "CASO_LATENCIA"
NS = 1e9
_FIELDS = ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration")

_path: Path | None = Path(os.environ[ENV]) if os.environ.get(ENV) else None
_record: dict | None = None
_stage: str | None = None
_after_stage = None  # función sin argumentos; su resultado se guarda en la etapa (fuera del tiempo)


def enable(path: Path | None, after_stage=None) -> None:
    """Activa la medición (escribe en `path`) o la desactiva con None.

    `after_stage`: se llama al cerrar cada etapa, después de medirla (p. ej., modelos en VRAM).
    """
    global _path, _record, _stage, _after_stage
    _path, _record, _stage, _after_stage = path, None, None, after_stage


def enabled() -> bool:
    return _path is not None


def begin(item_id: str, **meta) -> None:
    global _record
    if enabled():
        _record = {"id": item_id, **meta, "etapas": [], "llamadas": []}


@contextmanager
def stage(name: str):
    """Tiempo de pared de un paso. Las llamadas a Ollama dentro quedan asociadas a él."""
    global _stage
    if _record is None:
        yield
        return
    prev, _stage = _stage, name
    t0 = time.perf_counter()
    try:
        yield
    finally:
        entry = {"etapa": name, "s": time.perf_counter() - t0}
        if _after_stage is not None:
            entry["despues"] = _after_stage()
        _record["etapas"].append(entry)
        _stage = prev


def record_ollama(resp, kind: str, model: str) -> None:
    """Métricas de una respuesta de Ollama (chat, embed o generate)."""
    if _record is None:
        return
    call = {"etapa": _stage, "tipo": kind, "modelo": model, "cached": False}
    for f in _FIELDS:
        call[f.removesuffix("_duration")] = (getattr(resp, f, None) or 0) / NS
    call["prompt_eval_count"] = getattr(resp, "prompt_eval_count", None) or 0
    call["eval_count"] = getattr(resp, "eval_count", None) or 0
    _record["llamadas"].append(call)


def record_cache_hit(kind: str) -> None:
    if _record is not None:
        _record["llamadas"].append({"etapa": _stage, "tipo": kind, "cached": True})


def note(**fields) -> None:
    """Datos sueltos del registro abierto (p. ej., la decisión de enrutado)."""
    if _record is not None:
        _record.update(fields)


def end(**meta) -> dict | None:
    """Cierra el registro y lo añade al JSONL. Devuelve el registro (None si está desactivado)."""
    global _record
    if _record is None:
        return None
    rec, _record = {**_record, **meta}, None
    _path.parent.mkdir(parents=True, exist_ok=True)
    with _path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec
