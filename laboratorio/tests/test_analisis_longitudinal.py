"""
Tests del análisis longitudinal (referencia + historial del paciente).
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from laboratorio.analisis_longitudinal import (
    analizar_resultado,
    analizar_solicitud,
    buscar_resultado_historico,
)
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestAnalisisLongitudinalServicio:
    def setup_method(self):
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo="SNGAL", nombre="Sangre", activo=True
        )
        self.tipo_hgb = TipoExamen.objects.create(
            codigo="HGB_AL",
            nombre="Hemoglobina",
            tipo_muestra_requerida=self.tipo_muestra,
            tipo_resultado="NUMERICO",
            unidad_default="g/dL",
            rango_min=Decimal("12"),
            rango_max=Decimal("16"),
            valor_critico_min=Decimal("7"),
            rango_referencia_texto="12-16 g/dL",
            precio=1,
            activo=True,
        )
        self.tipo_glu = TipoExamen.objects.create(
            codigo="GLU_AL",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tipo_muestra,
            tipo_resultado="NUMERICO",
            unidad_default="mg/dL",
            rango_min=Decimal("70"),
            rango_max=Decimal("110"),
            rango_referencia_texto="70-110 mg/dL",
            precio=1,
            activo=True,
        )
        self.paciente = Paciente.objects.create(
            dni="11223344", nombre="Pac", apellido="Long"
        )

    def _crear_orden_finalizada(self, *, hgb_valor: str, hgb_num: Decimal, dias_atras: int = 30):
        fecha = timezone.now() - timedelta(days=dias_atras)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="FINALIZADO",
        )
        SolicitudExamen.objects.filter(pk=sol.pk).update(fecha_solicitud=fecha)
        sol.refresh_from_db()
        res = ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_hgb,
            valor_obtenido=hgb_valor,
            valor_numerico=hgb_num,
            unidad="g/dL",
            rango_min_snapshot=Decimal("12"),
            rango_max_snapshot=Decimal("16"),
            rango_referencia_snapshot="12-16 g/dL",
            valor_critico_min_snapshot=Decimal("7"),
            es_patologico=hgb_num < Decimal("12") or hgb_num > Decimal("16"),
            es_critico=hgb_num <= Decimal("7"),
            fecha_validacion=fecha,
        )
        return sol, res

    def test_sin_historial_previo(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        res = ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_hgb,
            valor_obtenido="14",
            valor_numerico=Decimal("14"),
            unidad="g/dL",
            rango_min_snapshot=Decimal("12"),
            rango_max_snapshot=Decimal("16"),
            rango_referencia_snapshot="12-16 g/dL",
        )
        item = analizar_resultado(res)
        assert item is not None
        assert item["historial"]["tiene_historial"] is False
        assert item["historial"]["variacion"] == "sin_historial"
        assert item["referencia"]["en_rango"] is True

    def test_cambio_brusco_vs_historial(self):
        self._crear_orden_finalizada(hgb_valor="13.2", hgb_num=Decimal("13.2"), dias_atras=60)
        sol_actual = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        res_actual = ResultadoExamen.objects.create(
            solicitud=sol_actual,
            tipo_examen=self.tipo_hgb,
            valor_obtenido="7.3",
            valor_numerico=Decimal("7.3"),
            unidad="g/dL",
            rango_min_snapshot=Decimal("12"),
            rango_max_snapshot=Decimal("16"),
            rango_referencia_snapshot="12-16 g/dL",
            valor_critico_min_snapshot=Decimal("7"),
            es_patologico=True,
            es_critico=True,
        )
        item = analizar_resultado(res_actual)
        assert item is not None
        assert item["historial"]["tiene_historial"] is True
        assert item["historial"]["variacion"] == "brusca"
        assert item["referencia"]["es_critico"] is True
        assert any("cambio brusco" in a.lower() for a in item["alertas"])

    def test_variacion_estable(self):
        self._crear_orden_finalizada(hgb_valor="14.0", hgb_num=Decimal("14.0"), dias_atras=10)
        sol_actual = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        res_actual = ResultadoExamen.objects.create(
            solicitud=sol_actual,
            tipo_examen=self.tipo_hgb,
            valor_obtenido="14.5",
            valor_numerico=Decimal("14.5"),
            unidad="g/dL",
            rango_min_snapshot=Decimal("12"),
            rango_max_snapshot=Decimal("16"),
            rango_referencia_snapshot="12-16 g/dL",
        )
        item = analizar_resultado(res_actual)
        assert item["historial"]["variacion"] == "estable"
        assert not any("brusco" in a.lower() for a in item["alertas"])

    def test_buscar_historico_excluye_orden_actual(self):
        sol_ant, _ = self._crear_orden_finalizada(
            hgb_valor="13", hgb_num=Decimal("13"), dias_atras=20
        )
        hist = buscar_resultado_historico(
            paciente_id=self.paciente.pk,
            tipo_examen_id=self.tipo_hgb.pk,
            excluir_solicitud_id=sol_ant.pk,
            antes_de=timezone.now(),
        )
        assert hist is None

    def test_analizar_solicitud_multiples_resultados(self):
        self._crear_orden_finalizada(hgb_valor="13", hgb_num=Decimal("13"), dias_atras=15)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_hgb, self.tipo_glu)
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_hgb,
            valor_obtenido="7.3",
            valor_numerico=Decimal("7.3"),
            unidad="g/dL",
            rango_min_snapshot=Decimal("12"),
            rango_max_snapshot=Decimal("16"),
            es_patologico=True,
        )
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_glu,
            valor_obtenido="95",
            valor_numerico=Decimal("95"),
            unidad="mg/dL",
            rango_min_snapshot=Decimal("70"),
            rango_max_snapshot=Decimal("110"),
        )
        data = analizar_solicitud(sol)
        assert data["total_analizados"] == 2
        assert data["total_con_historial"] == 1
        assert data["total_cambios_significativos"] >= 1
        assert len(data["resumen_alertas"]) >= 1


@pytest.mark.django_db
class TestAnalisisLongitudinalAPI(APITestCase):
    def setUp(self):
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo="SNGAPI", nombre="Sangre", activo=True
        )
        self.tipo_hgb = TipoExamen.objects.create(
            codigo="HGB_API",
            nombre="Hemoglobina",
            tipo_muestra_requerida=self.tipo_muestra,
            tipo_resultado="NUMERICO",
            unidad_default="g/dL",
            rango_min=Decimal("12"),
            rango_max=Decimal("16"),
            rango_referencia_texto="12-16 g/dL",
            precio=1,
            activo=True,
        )
        self.paciente = Paciente.objects.create(
            dni="99881122", nombre="Api", apellido="Long"
        )
        esp = Especialidad.objects.create(nombre="Clínica AL")
        self.user_lab = User.objects.create_user(
            username="lab_al",
            email="lab-al@test.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_med = User.objects.create_user(
            username="med_al",
            email="med-al@test.com",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="AL",
            matricula="M-AL",
            especialidad=esp,
            user=self.user_med,
        )
        self.client.force_authenticate(user=self.user_lab)

    def test_endpoint_orden_pendiente_falla(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        r = self.client.get(f"/api/lab/solicitudes/{sol.pk}/analisis-longitudinal/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_endpoint_con_historial(self):
        fecha_ant = timezone.now() - timedelta(days=40)
        sol_ant = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="FINALIZADO",
        )
        SolicitudExamen.objects.filter(pk=sol_ant.pk).update(fecha_solicitud=fecha_ant)
        ResultadoExamen.objects.create(
            solicitud=sol_ant,
            tipo_examen=self.tipo_hgb,
            valor_obtenido="13.5",
            valor_numerico=Decimal("13.5"),
            unidad="g/dL",
            fecha_validacion=fecha_ant,
        )
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_hgb,
            valor_obtenido="8.0",
            valor_numerico=Decimal("8.0"),
            unidad="g/dL",
            rango_min_snapshot=Decimal("12"),
            rango_max_snapshot=Decimal("16"),
            rango_referencia_snapshot="12-16 g/dL",
            es_patologico=True,
        )
        r = self.client.get(f"/api/lab/solicitudes/{sol.pk}/analisis-longitudinal/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["total_analizados"], 1)
        self.assertEqual(r.data["total_con_historial"], 1)
        self.assertTrue(r.data["resultados"][0]["historial"]["tiene_historial"])
        self.assertGreater(len(r.data["resumen_alertas"]), 0)

    def test_medico_puede_ver_su_orden(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_hgb,
            valor_obtenido="14",
            valor_numerico=Decimal("14"),
            unidad="g/dL",
            rango_min_snapshot=Decimal("12"),
            rango_max_snapshot=Decimal("16"),
        )
        self.client.force_authenticate(user=self.user_med)
        r = self.client.get(f"/api/lab/solicitudes/{sol.pk}/analisis-longitudinal/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
