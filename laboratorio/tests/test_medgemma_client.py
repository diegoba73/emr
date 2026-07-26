"""Tests unitarios del cliente MedGemma (sin red)."""
from laboratorio.medgemma_client import intentar_conclusion_medgemma, medgemma_habilitado


def test_medgemma_deshabilitado_por_defecto(settings):
    settings.MEDGEMMA_ENABLED = False
    assert medgemma_habilitado() is False
    assert intentar_conclusion_medgemma(None) is None
