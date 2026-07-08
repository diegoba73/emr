"""Tests de orden de grupos en informe PDF."""
from __future__ import annotations

import uuid

import pytest
from django.test import TestCase

from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.orden_grupos_informe import (
    PANEL_HEMOGRAMA,
    aplicar_orden_grupos,
    construir_grupos_informe,
    grupo_key_panel,
    ordenar_grupos_por_defecto,
)
from pacientes.models import Paciente


@pytest.mark.django_db
class TestOrdenGruposInforme(TestCase):
    def setUp(self):
        tag = uuid.uuid4().hex[:6]
        self.tm_sangre = TipoMuestra.objects.create(codigo=f"S{tag}", nombre="Sangre", activo=True)
        self.tm_orina = TipoMuestra.objects.create(codigo=f"O{tag}", nombre="Orina", activo=True)

        self.te_glu = TipoExamen.objects.create(
            codigo=f"GLU{tag}",
            nombre="Glucemia",
            tipo_muestra_requerida=self.tm_sangre,
            precio=1,
            activo=True,
        )
        self.te_wbc = TipoExamen.objects.create(
            codigo=f"WBC{tag}",
            nombre="Leucocitos",
            tipo_muestra_requerida=self.tm_sangre,
            precio=1,
            activo=True,
        )
        self.te_ph = TipoExamen.objects.create(
            codigo=f"PHU{tag}",
            nombre="pH orina",
            tipo_muestra_requerida=self.tm_orina,
            precio=1,
            activo=True,
        )

        self.panel_hemo = PanelExamen.objects.create(
            codigo=PANEL_HEMOGRAMA,
            nombre="Hemograma",
            activo=True,
        )
        self.panel_hemo.tipos_examen.add(self.te_wbc)

        self.panel_iono = PanelExamen.objects.create(
            codigo=f"PAN_IONO{tag}",
            nombre="Ionograma",
            activo=True,
        )
        self.panel_iono.tipos_examen.add(self.te_glu)

        self.panel_orina = PanelExamen.objects.create(
            codigo="PAN_ORI",
            nombre="Orina completa",
            activo=True,
        )
        self.panel_orina.tipos_examen.add(self.te_ph)

        self.paciente = Paciente.objects.create(dni=f"D{tag}", nombre="Ana", apellido="Test")
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        self.sol.paneles.add(self.panel_iono, self.panel_hemo, self.panel_orina)

        self.r_hemo = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te_wbc, valor_obtenido="5"
        )
        self.r_iono = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te_glu, valor_obtenido="90"
        )
        self.r_orina = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te_ph, valor_obtenido="6"
        )

    def test_orden_defecto_hemo_primero_orina_ultima(self):
        resultados = list(self.sol.resultados.select_related("tipo_examen").all())
        grupos = ordenar_grupos_por_defecto(construir_grupos_informe(self.sol, resultados))
        keys = [g.key for g in grupos]
        self.assertEqual(keys[0], grupo_key_panel(self.panel_hemo.pk))
        self.assertEqual(keys[-1], grupo_key_panel(self.panel_orina.pk))

    def test_orden_custom_persistido(self):
        resultados = list(self.sol.resultados.select_related("tipo_examen").all())
        specs = construir_grupos_informe(self.sol, resultados)
        custom = [
            grupo_key_panel(self.panel_orina.pk),
            grupo_key_panel(self.panel_iono.pk),
            grupo_key_panel(self.panel_hemo.pk),
        ]
        ordered = aplicar_orden_grupos(specs, custom)
        self.assertEqual([g.key for g in ordered], custom)
