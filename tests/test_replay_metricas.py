import importlib.util
import sys

import pytest

from caso_uso_llm.paths import ROOT

SCRIPTS = ROOT / "scripts"


def _load():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("replay_metricas", SCRIPTS / "replay_metricas.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()


@pytest.mark.parametrize(
    ("k", "n", "low", "high"),
    [(4, 4, 0.5101, 1.0), (0, 24, 0.0, 0.1380), (4, 7, 0.2505, 0.8418), (1, 3, 0.0615, 0.7923)],
)
def test_wilson_con_valores_conocidos(k, n, low, high):
    assert M.wilson(k, n) == pytest.approx((low, high), abs=0.0005)


def test_formato_espanol():
    assert (M.num(0.781, 3), M.miles(11414), M.pct(0.031, 1)) == ("0,781", "11.414", "3,1 %")


def test_la_tabla_lleva_la_cifra_del_fichero():
    f = M.facts()
    html = M.results_table(f, "https://repo")
    assert M.num(f["ahr"]["f1_macro"], 3) in html
    assert all((M.ROOT / row[5]).exists() for row in M.result_rows(f))


def test_una_cifra_de_la_cabecera_sale_de_la_cola():
    f = M.facts()
    assert f"{f['low']} reseñas reales" in M.headline(f, "https://repo")
