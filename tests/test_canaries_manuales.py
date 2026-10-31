import pytest

from caso_uso_llm.evals.canaries_manuales import check, score


def _item(id_, clase="canary", origen="manual", expected=("sin_culpa",)):
    return {"id": id_, "clase": clase, "origen": origen, "expected_fail": list(expected)}


def test_cuenta_canaries_reales_y_controles():
    items = [
        _item("man-01", origen="real"),
        _item("man-02", expected=("sin_culpa", "tono")),
        _item("man-03", clase="control", expected=()),
    ]
    got = {"man-01": {"sin_culpa", "tono"}, "man-02": {"sin_culpa"}, "man-03": {"tono"}}
    s = score(items, got)
    assert (s["canaries"], s["reales"], s["controles"]) == ((1, 2), (1, 1), (0, 1))


def test_un_control_limpio_cuenta():
    assert score([_item("c", clase="control", expected=())], {"c": set()})["controles"] == (1, 1)


@pytest.mark.parametrize("item", [_item("x", expected=("no_existe",)), _item("x", expected=())])
def test_rechaza_criterios_desconocidos_o_ausentes(item):
    with pytest.raises(AssertionError):
        check([item])
