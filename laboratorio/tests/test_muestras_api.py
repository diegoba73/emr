"""
Tests API catálogos B0 y muestras transaccionales B1.
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import EventoMuestra, Muestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestLimsCatalogosB0API(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_b0_{self.suf}",
            email=f"lb0{self.suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_b0_{self.suf}",
            email=f"ab0{self.suf}@t.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.med = User.objects.create_user(
            username=f"med_b0_{self.suf}",
            email=f"mb0{self.suf}@t.com",
            password="x",
            rol="medico",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_b0_{self.suf}",
            email=f"pb0{self.suf}@t.com",
            password="x",
            rol="paciente",
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def test_anonimo_bloqueado_areas(self):
        r = self.client.get("/api/lab/areas/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_laboratorio_lista_areas(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/lab/areas/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_paciente_no_lista_areas(self):
        self.client.force_authenticate(self.pac_u)
        r = self.client.get("/api/lab/areas/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_crea_area_laboratorio_no(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post(
            "/api/lab/areas/",
            {"codigo": f"CL{self.suf}", "nombre": f"Clínica {self.suf}", "activo": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.client.force_authenticate(self.lab)
        suf2 = uuid.uuid4().hex[:6]
        r2 = self.client.post(
            "/api/lab/areas/",
            {"codigo": f"XX{suf2}", "nombre": f"X {suf2}", "activo": True},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_403_FORBIDDEN)

    def test_alias_laboratorio_areas(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/areas/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestLimsMuestrasB1API(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_m1_{self.suf}",
            email=f"lm1{self.suf}@t.com",
            password="pass12345",
            rol="laboratorio",
            is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_m1_{self.suf}",
            email=f"am1{self.suf}@t.com",
            password="pass12345",
            rol="admin",
            is_staff=True,
        )
        self.med = User.objects.create_user(
            username=f"med_m1_{self.suf}",
            email=f"mm1{self.suf}@t.com",
            password="pass12345",
            rol="medico",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_m1_{self.suf}",
            email=f"pm1{self.suf}@t.com",
            password="pass12345",
            rol="paciente",
        )
        self.esp = Especialidad.objects.create(nombre=f"Cardio {self.suf}")
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="Dueño",
            matricula=f"M{self.suf}",
            especialidad=self.esp,
            user=self.med,
        )
        self.paciente = Paciente.objects.create(
            dni=f"DNI{self.suf}",
            nombre="P",
            apellido="Test",
            user=self.pac_u,
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"TM{self.suf}",
            nombre="Sangre",
            activo=True,
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{self.suf}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="PENDIENTE",
        )
        self.solicitud.tipos_examen.add(self.te)
        self.client = APIClient(enforce_csrf_checks=False)

    def _crear_muestra(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/muestras-transaccionales/",
            {
                "solicitud_id": self.solicitud.pk,
                "tipo_muestra_id": self.tm.pk,
                "observaciones": "",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        return r.json()["id"]

    def test_anonimo_no_crea_muestra(self):
        r = self.client.post(
            "/api/lab/muestras-transaccionales/",
            {"solicitud_id": self.solicitud.pk, "tipo_muestra_id": self.tm.pk},
            format="json",
        )
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_laboratorio_crea_y_flujo_acciones(self):
        mid = self._crear_muestra()
        m0 = Muestra.objects.get(pk=mid)
        self.assertEqual(m0.estado, "PENDIENTE_TOMA")
        self.assertTrue(m0.codigo_barra)

        with self.captureOnCommitCallbacks(execute=True):
            r1 = self.client.post(f"/api/lab/muestras-transaccionales/{mid}/tomar/", {}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r1.json()["estado"], "TOMADA")
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, "TOMA_MUESTRA")

        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                f"/api/lab/muestras-transaccionales/{mid}/recibir/",
                {"ubicacion_actual": "R1"},
                format="json",
            )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.json()["estado"], "RECIBIDA")

        with self.captureOnCommitCallbacks(execute=True):
            r3 = self.client.post(
                f"/api/lab/muestras-transaccionales/{mid}/conservar/",
                {"ubicacion_actual": "H1"},
                format="json",
            )
        self.assertEqual(r3.status_code, status.HTTP_200_OK)

        ev = AuditEvent.objects.filter(
            entity_type=Muestra._meta.label,
            entity_id=str(mid),
            module="laboratorio",
        ).order_by("-id").first()
        self.assertIsNotNone(ev)

        self.assertGreaterEqual(EventoMuestra.objects.filter(muestra_id=mid).count(), 4)

    def test_medico_no_crea_muestra(self):
        self.client.force_authenticate(self.med)
        r = self.client.post(
            "/api/lab/muestras-transaccionales/",
            {"solicitud_id": self.solicitud.pk, "tipo_muestra_id": self.tm.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_medico_puede_ver_su_muestra_no_operar(self):
        mid = self._crear_muestra()
        self.client.force_authenticate(self.med)
        r = self.client.get(f"/api/lab/muestras-transaccionales/{mid}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r2 = self.client.post(f"/api/lab/muestras-transaccionales/{mid}/tomar/", {}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_403_FORBIDDEN)

    def test_paciente_sin_acceso_muestras(self):
        self.client.force_authenticate(self.pac_u)
        r = self.client.get("/api/lab/muestras-transaccionales/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_rechazar_sin_motivo_400(self):
        mid = self._crear_muestra()
        r = self.client.post(f"/api/lab/muestras-transaccionales/{mid}/rechazar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_recibir_rechazada(self):
        mid = self._crear_muestra()
        r0 = self.client.post(
            f"/api/lab/muestras-transaccionales/{mid}/rechazar/",
            {"motivo_rechazo": "Hemolizada"},
            format="json",
        )
        self.assertEqual(r0.status_code, status.HTTP_200_OK)
        r1 = self.client.post(f"/api/lab/muestras-transaccionales/{mid}/recibir/", {}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_estado_no_cambia(self):
        mid = self._crear_muestra()
        r = self.client.patch(
            f"/api/lab/muestras-transaccionales/{mid}/",
            {"estado": "RECIBIDA", "observaciones": "x"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        m = Muestra.objects.get(pk=mid)
        self.assertEqual(m.estado, "PENDIENTE_TOMA")
        self.assertIn("x", m.observaciones)
