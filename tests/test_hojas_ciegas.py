import importlib.util
import json
import sys

from caso_uso_llm.paths import ROOT

SCRIPTS = ROOT / "scripts"


def _load(name: str):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_la_hoja_de_relevancia_no_lleva_las_etiquetas_de_claude():
    rows = _load("relevancia_vista").rows()
    assert len(rows) == 30
    assert all(set(r) == {"id", "texto"} and r["texto"] for r in rows)


def test_las_semillas_van_sin_etiquetas_y_con_ids_opacos():
    rows, mapping = _load("calibracion_vista").seed_rows()
    assert len(rows) == len(mapping) == 10
    assert all(set(r) == {"id", "reseña", "respuesta"} for r in rows)
    assert all(r["id"].startswith("s") and "v1" not in json.dumps(r["id"]) for r in rows)
