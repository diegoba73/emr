"""Tests unitarios puros (sin DB) de frases de conclusión de hemograma."""
from decimal import Decimal

from laboratorio.conclusion_hemograma import (
    _frase_anemia_morfologia,
    _frase_plaquetas,
    _frase_rdw,
)


def test_frase_anemia_normocitica_normocromica():
    frase = _frase_anemia_morfologia(
        Decimal("7.3"),
        "bajo",
        Decimal("92.8"),
        Decimal("33.2"),
    )
    assert frase == "Anemia normocítica normocrómica"


def test_frase_microcitica_hipocromica():
    frase = _frase_anemia_morfologia(
        Decimal("9.0"),
        "bajo",
        Decimal("72"),
        Decimal("28"),
    )
    assert frase == "Anemia microcítica hipocrómica"


def test_frase_trombocitopenia_leve_y_anisocitosis():
    assert _frase_plaquetas(Decimal("120000"), "bajo") == "trombocitopenia leve"
    assert _frase_rdw("alto") == "anisocitosis"
