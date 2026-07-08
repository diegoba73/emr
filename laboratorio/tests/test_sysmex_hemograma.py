"""Tests conversión ticket Sysmex → valor clínico hemograma."""
import pytest
from decimal import Decimal

from laboratorio.sysmex_hemograma import convert_sysmex_entry, format_sysmex_informe


@pytest.mark.parametrize(
    "codigo, entry, numeric, informe",
    [
        ("LEU", "93", Decimal("9300"), "9300"),
        ("HEMATIES", "237", Decimal("2.37"), "2.370.000"),
        ("HGB", "73", Decimal("7.3"), "7.3"),
        ("RDW", "139", Decimal("13.9"), "13.9"),
        ("PLAQ", "158", Decimal("158000"), "158000"),
        ("NEUT_CAY", "70", Decimal("70"), "70"),
        ("NEUT_SEG", "698", Decimal("698"), "698"),
    ],
)
def test_convert_sysmex_entry(codigo, entry, numeric, informe):
    conv = convert_sysmex_entry(codigo, entry)
    assert conv is not None
    assert conv["valor_numerico"] == numeric
    assert conv["valor_informe"] == informe


def test_format_sysmex_informe_decimal1():
    assert format_sysmex_informe(Decimal("7.3"), "decimal1") == "7.3"
