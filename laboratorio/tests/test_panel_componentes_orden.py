"""Tests de orden clínico de componentes por panel."""
from __future__ import annotations

import pytest

from laboratorio.catalogo_solicitud_papel import PANELES
from laboratorio.panel_componentes_orden import (
    PANEL_COMPONENTES_BY_CODIGO,
    ordenar_ids_por_panel,
    ordenar_resultados_por_panel,
)


class _FakeTe:
    def __init__(self, pk: int, codigo: str):
        self.id = pk
        self.codigo = codigo


class _FakeRes:
    def __init__(self, pk: int, te: _FakeTe):
        self.pk = pk
        self.tipo_examen = te
        self.tipo_examen_id = te.id


@pytest.mark.django_db
class TestPanelComponentesOrden:
    def test_hemograma_orden_canonico(self):
        assert PANEL_COMPONENTES_BY_CODIGO["PAN_HEMO"] == [
            "HEMATIES",
            "HTO",
            "HGB",
            "RDW",
            "LEU",
            "NEUT_CAY",
            "NEUT_SEG",
            "EOS",
            "BAS",
            "LINF",
            "MONO",
            "PLAQ",
        ]

    def test_ionograma_orden_canonico(self):
        assert PANEL_COMPONENTES_BY_CODIGO["PAN_IONO"] == ["NA", "K", "CL"]

    def test_ordenar_ids_por_panel(self):
        pares = [(5, "PLAQ"), (1, "HEMATIES"), (3, "HGB"), (2, "HTO")]
        assert ordenar_ids_por_panel("PAN_HEMO", pares) == [1, 2, 3, 5]

    def test_ordenar_resultados_por_panel(self):
        items = [
            _FakeRes(10, _FakeTe(3, "HGB")),
            _FakeRes(11, _FakeTe(1, "HEMATIES")),
            _FakeRes(12, _FakeTe(2, "HTO")),
        ]
        ordered = ordenar_resultados_por_panel("PAN_HEMO", items)
        assert [r.pk for r in ordered] == [11, 12, 10]

    def test_paneles_catalogo_tienen_lista_componentes(self):
        assert len(PANELES) >= 1
        for panel in PANELES:
            assert panel["componentes"]
