"""Tests conversión ticket analizador → valor clínico (catálogo TipoExamen)."""
import pytest
from decimal import Decimal

from laboratorio.entrada_resultados import convert_ticket_entry, format_informe_entrada
from laboratorio.sysmex_hemograma import convert_sysmex_entry, format_sysmex_informe


class _TipoExamenStub:
    def __init__(self, codigo: str, modo_entrada: str = "ESTANDAR", **kwargs):
        self.codigo = codigo
        self.modo_entrada = modo_entrada
        for k, v in kwargs.items():
            setattr(self, k, v)


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
def test_convert_ticket_entry_legacy_codigo(codigo, entry, numeric, informe):
    te = _TipoExamenStub(codigo)
    conv = convert_ticket_entry(te, entry)
    assert conv is not None
    assert conv["valor_numerico"] == numeric
    assert conv["valor_informe"] == informe


def test_convert_sysmex_entry_compat():
    conv = convert_sysmex_entry("LEU", "93")
    assert conv is not None
    assert conv["valor_numerico"] == Decimal("9300")


def test_convert_ticket_entry_from_catalog():
    te = _TipoExamenStub(
        "LEU",
        modo_entrada="TICKET_ENTERO",
        ticket_decimales=1,
        multiplicador_clinico=Decimal("1000"),
        formato_informe_entrada="absolute_int",
    )
    conv = convert_ticket_entry(te, "93")
    assert conv["valor_numerico"] == Decimal("9300")
    assert conv["valor_informe"] == "9300"


def test_valor_numerico_max_cuatro_decimales():
    te = _TipoExamenStub(
        "HEMATIES",
        modo_entrada="TICKET_ENTERO",
        ticket_decimales=2,
        multiplicador_clinico=Decimal("1.000000"),
        formato_informe_entrada="absolute_millions",
    )
    conv = convert_ticket_entry(te, "237")
    assert conv is not None
    assert conv["valor_numerico"] == Decimal("2.3700")
    assert str(conv["valor_numerico"]) == "2.3700"


def test_format_informe_decimal1():
    assert format_informe_entrada(Decimal("7.3"), "decimal1") == "7.3"
    assert format_sysmex_informe(Decimal("7.3"), "decimal1") == "7.3"
