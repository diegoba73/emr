"""API: ensayos recientes de internación (sugerencia al crear pedido)."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.origen_solicitud import INTERNACION_UCO
from laboratorio.sugerencia_seguimiento_internacion import ensayos_recientes_internacion
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class EnsayosRecientesInternacionTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.paciente = Paciente.objects.create(
            dni="66778899", nombre="Seg", apellido="Interno"
        )
        tm = TipoMuestra.objects.create(codigo="TM_SI", nombre="Sangre SI", activo=True)
        self.te_trop = TipoExamen.objects.create(
            codigo="TROP_SI",
            nombre="Troponina SI",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            unidad_default="ng/L",
            precio=1,
            activo=True,
        )
        self.te_glu = TipoExamen.objects.create(
            codigo="GLU_SI",
            nombre="Glucosa SI",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            unidad_default="mg/dL",
            precio=1,
            activo=True,
        )
        esp = Especialidad.objects.create(nombre="Clin SI")
        self.user_med = User.objects.create_user(
            username="med_si",
            email="med-si@t.com",
            password="x",
            rol="medico",
            is_staff=True,
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="Seg",
            matricula="M-SI",
            especialidad=esp,
            user=self.user_med,
        )
        self.user_lab = User.objects.create_user(
            username="lab_si",
            email="lab-si@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_pac = User.objects.create_user(
            username="pac_si",
            email="pac-si@t.com",
            password="x",
            rol="paciente",
        )

    def _orden(
        self,
        *,
        te,
        origen: str,
        dias: int,
        estado: str = "FINALIZADO",
        numero: str | None = None,
    ):
        fecha = timezone.localdate() - timedelta(days=dias)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud=origen,
            estado="PENDIENTE",
            fecha_programada_toma=fecha,
            numero=numero,
        )
        sol.tipos_examen.add(te)
        SolicitudExamen.objects.filter(pk=sol.pk).update(
            estado=estado,
            fecha_solicitud=timezone.now() - timedelta(days=dias),
        )
        sol.refresh_from_db()
        return sol

    def test_servicio_solo_internacion_ultima_semana(self):
        self._orden(
            te=self.te_trop,
            origen=INTERNACION_UCO,
            dias=2,
            numero="LAB-SI-TROP",
        )
        self._orden(
            te=self.te_glu,
            origen="AMBULATORIO_CEHTA",
            dias=1,
            numero="LAB-SI-GLU-AMB",
        )
        self._orden(
            te=self.te_glu,
            origen=INTERNACION_UCO,
            dias=10,
            numero="LAB-SI-GLU-OLD",
        )

        data = ensayos_recientes_internacion(self.paciente.pk, dias=7)
        self.assertEqual(data["dias"], 7)
        codigos = {e["codigo"] for e in data["examenes"]}
        self.assertIn("TROP_SI", codigos)
        self.assertNotIn("GLU_SI", codigos)
        trop = next(e for e in data["examenes"] if e["codigo"] == "TROP_SI")
        self.assertEqual(trop["orden_numero"], "LAB-SI-TROP")

    def test_servicio_incluye_mismo_dia(self):
        """Pedidos de hoy (mismo día del pedido en curso) también cuentan."""
        self._orden(
            te=self.te_trop,
            origen=INTERNACION_UCO,
            dias=0,
            numero="LAB-SI-HOY",
        )
        data = ensayos_recientes_internacion(
            self.paciente.pk, dias=7, fecha_hasta=timezone.localdate()
        )
        codigos = {e["codigo"] for e in data["examenes"]}
        self.assertIn("TROP_SI", codigos)
        self.assertEqual(data["fecha_hasta"], timezone.localdate().isoformat())

    def test_servicio_excluye_cancelado(self):
        self._orden(
            te=self.te_trop,
            origen=INTERNACION_UCO,
            dias=1,
            estado="CANCELADO",
            numero="LAB-SI-CAN",
        )
        data = ensayos_recientes_internacion(self.paciente.pk, dias=7)
        self.assertEqual(data["examenes"], [])

    def test_api_medico_ok(self):
        self._orden(te=self.te_trop, origen=INTERNACION_UCO, dias=1, numero="LAB-SI-1")
        self.client.force_authenticate(user=self.user_med)
        r = self.client.get(
            f"/api/lab/pacientes/{self.paciente.pk}/ensayos-recientes-internacion/"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(r.data["dias"], 7)
        self.assertEqual(len(r.data["examenes"]), 1)
        self.assertEqual(r.data["examenes"][0]["codigo"], "TROP_SI")

    def test_api_lab_ok(self):
        self._orden(te=self.te_trop, origen=INTERNACION_UCO, dias=1)
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.get(
            f"/api/lab/pacientes/{self.paciente.pk}/ensayos-recientes-internacion/?dias=7"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["examenes"]), 1)

    def test_api_paciente_ajeno_403(self):
        self._orden(te=self.te_trop, origen=INTERNACION_UCO, dias=1)
        self.client.force_authenticate(user=self.user_pac)
        r = self.client.get(
            f"/api/lab/pacientes/{self.paciente.pk}/ensayos-recientes-internacion/"
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_paciente_inexistente_404(self):
        self.client.force_authenticate(user=self.user_med)
        r = self.client.get(
            "/api/lab/pacientes/99999999/ensayos-recientes-internacion/"
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_sin_auth_401(self):
        r = self.client.get(
            f"/api/lab/pacientes/{self.paciente.pk}/ensayos-recientes-internacion/"
        )
        self.assertIn(
            r.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
