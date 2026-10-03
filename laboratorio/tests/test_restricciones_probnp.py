"""Bloqueo de frecuencia PROBNP (obra social, 31 días)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.restricciones_frecuencia import (
    paciente_tiene_probnp_reciente,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class TestRestriccionProbnpFrecuencia(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="adm_probnp",
            email="adm-probnp@t.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.medico_user = User.objects.create_user(
            username="med_probnp",
            email="med-probnp@t.com",
            password="x",
            rol="medico",
        )
        self.lab = User.objects.create_user(
            username="lab_probnp",
            email="lab-probnp@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.bio = User.objects.create_user(
            username="bio_probnp",
            email="bio-probnp@t.com",
            password="x",
            rol="bioquimico",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni="9012001", nombre="P", apellido="Probnp"
        )
        esp = Especialidad.objects.create(nombre="Esp Probnp")
        self.medico = Medico.objects.create(
            user=self.medico_user,
            nombre="Dr",
            apellido="Probnp",
            matricula="M-PBNP",
            especialidad=esp,
        )
        tm = TipoMuestra.objects.create(codigo="TM_PBNP", nombre="Sangre PBNP", activo=True)
        self.probnp, _ = TipoExamen.objects.get_or_create(
            codigo="PROBNP",
            defaults={
                "nombre": "Pro-BNP",
                "unidad_default": "pg/mL",
                "tipo_muestra_requerida": tm,
                "precio": 1,
                "activo": True,
            },
        )
        self.glu = TipoExamen.objects.create(
            codigo="GLU_PBNP",
            nombre="Glucosa PBNP",
            unidad_default="mg/dL",
            tipo_muestra_requerida=tm,
            precio=1,
            activo=True,
        )

    def _orden_con_probnp(self, *, dias_atras=0):
        """
        Pedido histórico con PROBNP.

        Usa fecha_programada_toma distinta de hoy para que el create de hoy
        no lo fusione (buscar_orden_abierta).
        """
        dias = dias_atras or 1
        fecha_toma = timezone.localdate() - timedelta(days=dias)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            fecha_programada_toma=fecha_toma,
        )
        sol.tipos_examen.add(self.probnp)
        ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=self.probnp, valor_obtenido=""
        )
        if dias_atras:
            SolicitudExamen.objects.filter(pk=sol.pk).update(
                fecha_solicitud=timezone.now() - timedelta(days=dias_atras)
            )
            sol.refresh_from_db()
        return sol

    def _crear(self, user, examenes_ids):
        self.client.force_authenticate(user=user)
        return self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.paciente.pk,
                "medico_id": self.medico.pk,
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "examenes_ids": examenes_ids,
                "paneles_ids": [],
                "fecha_programada_toma": timezone.localdate().isoformat(),
            },
            format="json",
        )

    def test_helper_detecta_pedido_reciente(self):
        self._orden_con_probnp(dias_atras=10)
        self.assertTrue(paciente_tiene_probnp_reciente(self.paciente.pk))

    def test_helper_ignora_pedido_viejo(self):
        self._orden_con_probnp(dias_atras=40)
        self.assertFalse(paciente_tiene_probnp_reciente(self.paciente.pk))

    def test_medico_bloqueado_si_reciente(self):
        self._orden_con_probnp(dias_atras=5)
        r = self._crear(self.medico_user, [self.probnp.pk])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        body = str(r.data)
        self.assertIn("proBNP", body)
        self.assertIn("Obra Social", body)

    def test_admin_puede_si_reciente(self):
        self._orden_con_probnp(dias_atras=5)
        r = self._crear(self.admin, [self.probnp.pk])
        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), r.data)

    def test_laboratorio_puede_si_reciente(self):
        self._orden_con_probnp(dias_atras=5)
        r = self._crear(self.lab, [self.probnp.pk])
        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), r.data)

    def test_bioquimico_puede_si_reciente(self):
        self._orden_con_probnp(dias_atras=5)
        r = self._crear(self.bio, [self.probnp.pk])
        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), r.data)

    def test_medico_ok_sin_pedido_previo(self):
        r = self._crear(self.medico_user, [self.probnp.pk])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

    def test_medico_ok_si_mas_de_31_dias(self):
        self._orden_con_probnp(dias_atras=40)
        r = self._crear(self.medico_user, [self.probnp.pk])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

    def test_medico_puede_pedir_otro_examen_con_probnp_reciente(self):
        self._orden_con_probnp(dias_atras=5)
        r = self._crear(self.medico_user, [self.glu.pk])
        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), r.data)

    def test_agregar_examenes_bloquea_medico(self):
        abierta = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            fecha_programada_toma=timezone.localdate(),
        )
        abierta.tipos_examen.add(self.glu)
        ResultadoExamen.objects.create(
            solicitud=abierta, tipo_examen=self.glu, valor_obtenido=""
        )
        self._orden_con_probnp(dias_atras=3)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.post(
            f"/api/lab/solicitudes/{abierta.pk}/agregar-examenes/",
            {"examenes_ids": [self.probnp.pk], "paneles_ids": []},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("proBNP", str(r.data.get("detail") or r.data))

    def test_agregar_examenes_laboratorio_ok(self):
        abierta = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            fecha_programada_toma=timezone.localdate(),
        )
        abierta.tipos_examen.add(self.glu)
        ResultadoExamen.objects.create(
            solicitud=abierta, tipo_examen=self.glu, valor_obtenido=""
        )
        self._orden_con_probnp(dias_atras=3)
        self.client.force_authenticate(user=self.lab)
        r = self.client.post(
            f"/api/lab/solicitudes/{abierta.pk}/agregar-examenes/",
            {"examenes_ids": [self.probnp.pk], "paneles_ids": []},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

    def test_endpoint_restricciones_medico_bloqueado(self):
        self._orden_con_probnp(dias_atras=2)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.get(
            "/api/lab/solicitudes/restricciones-ensayos/",
            {"paciente_id": self.paciente.pk},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["PROBNP"]["bloqueado"])
        self.assertIn("proBNP", r.data["PROBNP"]["mensaje"])

    def test_endpoint_restricciones_laboratorio_libre(self):
        self._orden_con_probnp(dias_atras=2)
        self.client.force_authenticate(user=self.lab)
        r = self.client.get(
            "/api/lab/solicitudes/restricciones-ensayos/",
            {"paciente_id": self.paciente.pk},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["PROBNP"]["bloqueado"])
