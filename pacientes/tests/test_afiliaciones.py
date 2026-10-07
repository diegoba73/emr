"""Afiliaciones multi-OS y sync con campos legacy del paciente."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from pacientes.afiliaciones import (
    normalizar_snapshot_os,
    upsert_afiliacion,
)
from pacientes.models import Paciente, PacienteAfiliacion
from laboratorio.obra_social import obra_social_efectiva
from laboratorio.models import SolicitudExamen
from medicos.models import Especialidad, Medico

User = get_user_model()


class TestPacienteAfiliacionHelpers(TestCase):
    def test_upsert_y_sync_principal(self):
        p = Paciente.objects.create(dni="OS-AF-1", nombre="A", apellido="B")
        a1 = upsert_afiliacion(p, obra_social="OSDE", numero_afiliado="11", marcar_principal=True)
        self.assertTrue(a1.es_principal)
        p.refresh_from_db()
        self.assertEqual(p.obra_social, "OSDE")
        self.assertEqual(p.numero_afiliado, "11")

        a2 = upsert_afiliacion(p, obra_social="PAMI", numero_afiliado="22", marcar_principal=True)
        self.assertTrue(a2.es_principal)
        a1.refresh_from_db()
        self.assertFalse(a1.es_principal)
        p.refresh_from_db()
        self.assertEqual(p.obra_social, "PAMI")

    def test_snapshot_vacio(self):
        self.assertEqual(normalizar_snapshot_os("", "x"), ("", ""))
        self.assertEqual(normalizar_snapshot_os("  osde ", " 1 "), ("OSDE", "1"))


class TestObraSocialEfectiva(TestCase):
    def test_fallback_paciente_si_orden_sin_snapshot(self):
        p = Paciente.objects.create(
            dni="OS-EF-1", nombre="A", apellido="B", obra_social="SEROS", numero_afiliado="9"
        )
        esp = Especialidad.objects.create(nombre="Esp OS ef")
        med = Medico.objects.create(
            nombre="M", apellido="E", matricula="M-OSEF", especialidad=esp
        )
        sol = SolicitudExamen.objects.create(
            paciente=p, medico_interno=med, origen_solicitud="AMBULATORIO_ICPL"
        )
        os_txt, afil = obra_social_efectiva(sol)
        self.assertEqual(os_txt, "SEROS")
        self.assertEqual(afil, "9")

    def test_snapshot_gana_sobre_paciente(self):
        p = Paciente.objects.create(
            dni="OS-EF-2", nombre="A", apellido="B", obra_social="SEROS", numero_afiliado="9"
        )
        esp = Especialidad.objects.create(nombre="Esp OS ef2")
        med = Medico.objects.create(
            nombre="M", apellido="E2", matricula="M-OSEF2", especialidad=esp
        )
        sol = SolicitudExamen.objects.create(
            paciente=p,
            medico_interno=med,
            origen_solicitud="AMBULATORIO_ICPL",
            obra_social_orden="OSDE",
            afiliado_orden="100",
        )
        os_txt, afil = obra_social_efectiva(sol)
        self.assertEqual(os_txt, "OSDE")
        self.assertEqual(afil, "100")


class TestAfiliacionesApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="adm_afil",
            email="adm-afil@t.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.lab = User.objects.create_user(
            username="lab_afil",
            email="lab-afil@t.com",
            password="x",
            rol="laboratorio",
        )
        self.paciente = Paciente.objects.create(
            dni="OS-API-1", nombre="P", apellido="A", obra_social="OSDE", numero_afiliado="1"
        )
        upsert_afiliacion(
            self.paciente, obra_social="OSDE", numero_afiliado="1", marcar_principal=True
        )

    def test_lab_puede_crear_segunda_afiliacion(self):
        self.client.force_authenticate(user=self.lab)
        r = self.client.post(
            f"/api/pacientes/{self.paciente.pk}/afiliaciones/crear/",
            {"obra_social": "PAMI", "numero_afiliado": "99", "es_principal": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(PacienteAfiliacion.objects.filter(paciente=self.paciente, activo=True).count(), 2)

    def test_marcar_principal_sync_paciente(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(
            f"/api/pacientes/{self.paciente.pk}/afiliaciones/crear/",
            {"obra_social": "PAMI", "numero_afiliado": "77", "es_principal": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.obra_social, "PAMI")
        self.assertEqual(self.paciente.numero_afiliado, "77")


class TestCreateSolicitudConSnapshotOs(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="adm_os_snap",
            email="adm-os-snap@t.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni="OS-SNAP-1", nombre="P", apellido="S", obra_social="SEROS"
        )
        from laboratorio.models import TipoExamen, TipoMuestra

        tm = TipoMuestra.objects.create(codigo="TM_OSS", nombre="S", activo=True)
        self.te = TipoExamen.objects.create(
            codigo="OSS_A",
            nombre="A",
            unidad_default="u",
            tipo_muestra_requerida=tm,
            precio=1,
            activo=True,
            requiere_muestra=False,
        )

    def test_create_con_obra_social_guarda_snapshot(self):
        self.client.force_authenticate(user=self.admin)
        from django.utils import timezone

        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.paciente.pk,
                "examenes_ids": [self.te.pk],
                "fecha_programada_toma": str(timezone.localdate()),
                "origen_solicitud": "AMBULATORIO_ICPL",
                "obra_social": "osde",
                "numero_afiliado": "55",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        sol = SolicitudExamen.objects.get(pk=r.data["id"])
        self.assertEqual(sol.obra_social_orden, "OSDE")
        self.assertEqual(sol.afiliado_orden, "55")
        self.assertEqual(r.data.get("obra_social_efectiva"), "OSDE")
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.obra_social, "OSDE")
