"""API y servicio: últimos resultados por paciente (pedido médico)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from laboratorio.analisis_longitudinal import ultimos_resultados_paciente
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class UltimosResultadosPacienteTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.paciente = Paciente.objects.create(
            dni="55667788", nombre="Hist", apellido="Pedido"
        )
        tm = TipoMuestra.objects.create(codigo="TM_UR", nombre="Sangre UR", activo=True)
        self.te_hgb = TipoExamen.objects.create(
            codigo="HGB_UR",
            nombre="Hemoglobina UR",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            unidad_default="g/dL",
            precio=1,
            activo=True,
        )
        self.te_glu = TipoExamen.objects.create(
            codigo="GLU_UR",
            nombre="Glucosa UR",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            unidad_default="mg/dL",
            precio=1,
            activo=True,
        )
        self.te_crea = TipoExamen.objects.create(
            codigo="CREA_UR",
            nombre="Creatinina UR",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            unidad_default="mg/dL",
            precio=1,
            activo=True,
        )
        esp = Especialidad.objects.create(nombre="Clin UR")
        self.user_med = User.objects.create_user(
            username="med_ur",
            email="med-ur@t.com",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="Hist",
            matricula="M-UR",
            especialidad=esp,
            user=self.user_med,
        )
        self.user_lab = User.objects.create_user(
            username="lab_ur",
            email="lab-ur@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_pac = User.objects.create_user(
            username="pac_ur",
            email="pac-ur@t.com",
            password="x",
            rol="paciente",
        )

    def _orden_finalizada(self, *, te, valor: str, num: Decimal, dias: int, paciente=None):
        px = paciente or self.paciente
        fecha = timezone.now() - timedelta(days=dias)
        sol = SolicitudExamen.objects.create(
            paciente=px,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=te,
            valor_obtenido=valor,
            valor_numerico=num,
            unidad=te.unidad_default,
            fecha_validacion=fecha,
        )
        SolicitudExamen.objects.filter(pk=sol.pk).update(
            fecha_solicitud=fecha, estado="FINALIZADO"
        )
        sol.refresh_from_db()
        return sol

    def test_servicio_ventana_7d_y_anterior_fuera(self):
        # Anterior fuera de ventana: sigue sirviendo para comparación.
        self._orden_finalizada(te=self.te_hgb, valor="13", num=Decimal("13"), dias=40)
        self._orden_finalizada(te=self.te_hgb, valor="15", num=Decimal("15"), dias=5)
        # Fuera de 7 días: no aparece como fila propia.
        self._orden_finalizada(te=self.te_glu, valor="95", num=Decimal("95"), dias=10)
        # Dentro: creatinina reciente.
        self._orden_finalizada(te=self.te_crea, valor="1.1", num=Decimal("1.1"), dias=1)
        # Orden en proceso no debe aparecer
        sol_abierta = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        ResultadoExamen.objects.create(
            solicitud=sol_abierta,
            tipo_examen=self.te_glu,
            valor_obtenido="200",
            valor_numerico=Decimal("200"),
            fecha_validacion=timezone.now(),
        )

        data = ultimos_resultados_paciente(self.paciente.pk, dias=7)
        self.assertEqual(data["paciente_id"], self.paciente.pk)
        self.assertEqual(data["dias"], 7)
        by_code = {i["tipo_examen_codigo"]: i for i in data["items"]}
        self.assertIn("HGB_UR", by_code)
        self.assertIn("CREA_UR", by_code)
        self.assertNotIn("GLU_UR", by_code)
        self.assertEqual(by_code["HGB_UR"]["valor"], "15")
        self.assertEqual(by_code["HGB_UR"]["valor_anterior"], "13")
        self.assertEqual(by_code["HGB_UR"]["tendencia"], "sube")
        self.assertEqual(by_code["CREA_UR"]["valor"], "1.1")

    def test_servicio_incluye_mismo_dia(self):
        self._orden_finalizada(te=self.te_crea, valor="0.9", num=Decimal("0.9"), dias=0)
        data = ultimos_resultados_paciente(self.paciente.pk, dias=7)
        codigos = {i["tipo_examen_codigo"] for i in data["items"]}
        self.assertIn("CREA_UR", codigos)

    def test_api_medico_ok(self):
        self._orden_finalizada(te=self.te_hgb, valor="14", num=Decimal("14"), dias=2)
        self.client.force_authenticate(user=self.user_med)
        r = self.client.get(
            f"/api/lab/pacientes/{self.paciente.pk}/ultimos-resultados/"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(r.data["total"], 1)
        self.assertEqual(r.data["dias"], 7)
        self.assertEqual(r.data["items"][0]["valor"], "14")

    def test_api_lab_ok(self):
        self._orden_finalizada(te=self.te_glu, valor="100", num=Decimal("100"), dias=1)
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.get(
            f"/api/lab/pacientes/{self.paciente.pk}/ultimos-resultados/?dias=7&limit=10"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["limit"], 10)
        self.assertEqual(r.data["total"], 1)

    def test_api_paciente_ajeno_403(self):
        self._orden_finalizada(te=self.te_hgb, valor="14", num=Decimal("14"), dias=1)
        self.client.force_authenticate(user=self.user_pac)
        r = self.client.get(
            f"/api/lab/pacientes/{self.paciente.pk}/ultimos-resultados/"
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_paciente_inexistente_404(self):
        self.client.force_authenticate(user=self.user_med)
        r = self.client.get("/api/lab/pacientes/99999999/ultimos-resultados/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_sin_auth_401(self):
        r = self.client.get(
            f"/api/lab/pacientes/{self.paciente.pk}/ultimos-resultados/"
        )
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
