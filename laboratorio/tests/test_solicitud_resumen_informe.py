"""Tests del resumen de orden para vistas nested (HC / revista)."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from laboratorio.models import (
    PanelExamen,
    ResultadoExamen,
    SolicitudExamen,
    TipoExamen,
    TipoMuestra,
)
from laboratorio.solicitud_resumen_informe import (
    paneles_resumen_solicitud,
    resultado_resumen_informe,
)
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestSolicitudResumenInforme(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            dni='RESINF-001',
            nombre='Resumen',
            apellido='Informe',
        )
        self.tm = TipoMuestra.objects.create(codigo='SNG-RINF', nombre='Sangre', activo=True)
        self.te_a = TipoExamen.objects.create(
            codigo='GLU-RINF',
            nombre='Glucosa',
            tipo_muestra_requerida=self.tm,
            activo=True,
        )
        self.te_b = TipoExamen.objects.create(
            codigo='UREA-RINF',
            nombre='Urea',
            tipo_muestra_requerida=self.tm,
            activo=True,
        )
        self.panel = PanelExamen.objects.create(
            codigo='PAN_RINF',
            nombre='Panel resumen',
            activo=True,
        )
        self.panel.tipos_examen.add(self.te_a, self.te_b)
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud='AMBULATORIO_CEHTA',
            orden_grupos_informe=[f'panel-{self.panel.id}'],
        )
        self.sol.paneles.add(self.panel)
        self.sol.tipos_examen.add(self.te_a, self.te_b)
        self.res_a = ResultadoExamen.objects.create(
            solicitud=self.sol,
            tipo_examen=self.te_a,
            valor_obtenido='95',
        )

    def test_paneles_resumen_incluye_ids_ordenados(self):
        resumen = paneles_resumen_solicitud(self.sol)
        assert len(resumen) == 1
        assert resumen[0]['id'] == self.panel.id
        assert resumen[0]['codigo'] == 'PAN_RINF'
        assert set(resumen[0]['tipos_examen_ids']) == {self.te_a.id, self.te_b.id}

    def test_resultado_resumen_campos_agrupacion(self):
        data = resultado_resumen_informe(self.res_a)
        assert data['id'] == self.res_a.id
        assert data['tipo_examen'] == self.te_a.id
        assert data['tipo_examen_codigo'] == 'GLU-RINF'
        assert data['tipo_examen_muestra_codigo'] == 'SNG-RINF'
        assert data['valor_obtenido'] == '95'
        assert data['examen'] == 'Glucosa'
        assert data['valor'] == '95'
