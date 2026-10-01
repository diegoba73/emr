"""Fecha programada de toma: obligatorio al crear; pendientes filtrables por día."""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.solicitud_orden_abierta import buscar_orden_abierta
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class TestFechaProgramadaToma(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_fpt_{suf}",
            email=f"lab-fpt-{suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"7{suf[:7]}", nombre="Luis", apellido="Gómez"
        )
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        self.medico = Medico.objects.create(
            nombre="Ana", apellido="Ruiz", matricula=f"M-{suf}", especialidad=esp
        )
        tm = TipoMuestra.objects.create(codigo=f"TM{suf}", nombre="Sangre", activo=True)
        self.glu, _ = TipoExamen.objects.get_or_create(
            codigo="GLU",
            defaults={
                "nombre": "Glucemia",
                "tipo_muestra_requerida": tm,
                "precio": 1,
                "activo": True,
            },
        )
        self.hoy = timezone.localdate()
        self.manana = self.hoy + timedelta(days=1)

    def _crear(self, fecha, examenes=None):
        self.client.force_authenticate(self.lab)
        return self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.paciente.pk,
                "medico_id": self.medico.pk,
                "origen_solicitud": "INTERNACION_UCO",
                "examenes_ids": examenes or [self.glu.pk],
                "paneles_ids": [],
                "fecha_programada_toma": fecha.isoformat(),
            },
            format="json",
        )

    def test_create_exige_fecha_programada_toma(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.paciente.pk,
                "medico_id": self.medico.pk,
                "origen_solicitud": "GUARDIA",
                "examenes_ids": [self.glu.pk],
                "paneles_ids": [],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.content)
        self.assertIn("fecha_programada_toma", r.json())

    def test_create_hoy_y_manana_no_se_fusionan(self):
        r1 = self._crear(self.hoy)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.content)
        id_hoy = r1.json()["id"]
        r2 = self._crear(self.manana)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, r2.content)
        self.assertNotEqual(r2.json()["id"], id_hoy)
        self.assertFalse(r2.json().get("merged"))

    def test_merge_solo_mismo_dia_extraccion(self):
        r1 = self._crear(self.manana)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.content)
        id_manana = r1.json()["id"]
        # segundo pedido mañana → merge
        urea, _ = TipoExamen.objects.get_or_create(
            codigo="UREA",
            defaults={
                "nombre": "Uremia",
                "tipo_muestra_requerida": self.glu.tipo_muestra_requerida,
                "precio": 1,
                "activo": True,
            },
        )
        r2 = self._crear(self.manana, examenes=[urea.pk])
        self.assertIn(r2.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), r2.content)
        self.assertTrue(r2.json().get("merged"))
        self.assertEqual(r2.json()["id"], id_manana)

    def test_list_vista_extraccion_hoy_vs_programadas(self):
        self._crear(self.hoy)
        self._crear(self.manana)
        self.client.force_authenticate(self.lab)
        hoy = self.client.get(
            "/api/lab/solicitudes/",
            {"estado": "PENDIENTE", "vista_extraccion": "hoy"},
        )
        prog = self.client.get(
            "/api/lab/solicitudes/",
            {"estado": "PENDIENTE", "vista_extraccion": "programadas"},
        )
        self.assertEqual(hoy.status_code, status.HTTP_200_OK)
        self.assertEqual(prog.status_code, status.HTTP_200_OK)
        ids_hoy = {x["id"] for x in hoy.json()["results"]}
        ids_prog = {x["id"] for x in prog.json()["results"]}
        sols = list(SolicitudExamen.objects.filter(paciente=self.paciente))
        self.assertEqual(len(sols), 2)
        sol_hoy = next(s for s in sols if s.fecha_programada_toma == self.hoy)
        sol_man = next(s for s in sols if s.fecha_programada_toma == self.manana)
        self.assertIn(sol_hoy.pk, ids_hoy)
        self.assertNotIn(sol_man.pk, ids_hoy)
        self.assertIn(sol_man.pk, ids_prog)
        self.assertNotIn(sol_hoy.pk, ids_prog)

    def test_buscar_orden_abierta_filtra_por_fecha(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="INTERNACION_UCO",
            estado="PENDIENTE",
            fecha_programada_toma=self.hoy,
        )
        self.assertEqual(buscar_orden_abierta(self.paciente.pk, fecha_programada_toma=self.hoy), sol)
        self.assertIsNone(
            buscar_orden_abierta(self.paciente.pk, fecha_programada_toma=self.manana)
        )
