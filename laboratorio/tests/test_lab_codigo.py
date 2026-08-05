"""Tests — numeración LAB unificada y resolve por código."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.lab_codigo import (
    CodigoKind,
    format_tubo,
    next_protocolo,
    parse_codigo,
    resolver_entidad,
)
from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import LabProtocoloCounter, Muestra
from laboratorio.models_microbiologia import EstudioMicrobiologia
from laboratorio.muestra_estado import crear_muestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestLabCodigoNumeracion(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_cod_{self.suf}",
            email=f"lc{self.suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.esp = Especialidad.objects.create(nombre=f"Esp {self.suf}")
        self.med_user = User.objects.create_user(
            username=f"med_cod_{self.suf}",
            email=f"mc{self.suf}@t.com",
            password="x",
            rol="medico",
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="X",
            matricula=f"M{self.suf}",
            especialidad=self.esp,
            user=self.med_user,
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_cod_{self.suf}",
            email=f"pc{self.suf}@t.com",
            password="x",
            rol="paciente",
        )
        self.paciente = Paciente.objects.create(
            dni=f"D{self.suf}", nombre="P", apellido="X", user=self.pac_u
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"TM{self.suf}", nombre="Sangre", activo=True
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{self.suf}",
            nombre="Glu",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def test_parse_protocolo_y_tubo(self):
        p = parse_codigo("lab-2026-00042")
        self.assertEqual(p.kind, CodigoKind.PROTOCOLO)
        self.assertEqual(p.seq, 42)
        t = parse_codigo("LAB-2026-00042-01")
        self.assertEqual(t.kind, CodigoKind.TUBO)
        self.assertEqual(t.tubo_n, 1)

    def test_secuencia_compartida_lab_y_micro(self):
        LabProtocoloCounter.objects.all().delete()
        a = next_protocolo(year=2099)
        b = next_protocolo(year=2099)
        self.assertTrue(a.startswith("LAB-2099-"))
        self.assertNotEqual(a, b)
        n1 = int(a.split("-")[-1])
        n2 = int(b.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.tipos_examen.add(self.te)
        self.assertTrue(sol.numero.startswith("LAB-"))

        est = EstudioMicrobiologia.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            tipo_estudio="CULTIVO_RUTINA",
            estado="PENDIENTE",
        )
        self.assertTrue(est.numero.startswith("LAB-"))
        self.assertNotEqual(sol.numero, est.numero)

    def test_tubo_codigo_hijo_del_protocolo(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.tipos_examen.add(self.te)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        self.assertTrue(m.codigo_barra.startswith(f"{sol.numero}-"))
        parsed = parse_codigo(m.codigo_barra)
        self.assertEqual(parsed.kind, CodigoKind.TUBO)

    def test_micro_codigo_barra_igual_numero(self):
        est = EstudioMicrobiologia.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            tipo_estudio="CULTIVO_RUTINA",
            estado="PENDIENTE",
        )
        est.ensure_codigo_barra()
        est.save(update_fields=["codigo_barra", "updated_at"])
        self.assertEqual(est.codigo_barra, est.numero)
        self.assertTrue(est.codigo_barra.startswith("LAB-"))

    def test_api_codigos_por_codigo_y_recibir(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.tipos_examen.add(self.te)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        est = EstudioMicrobiologia.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            tipo_estudio="CULTIVO_RUTINA",
            estado="PENDIENTE",
        )
        est.ensure_codigo_barra()
        est.save(update_fields=["codigo_barra", "numero", "updated_at"])

        self.client.force_authenticate(self.lab)
        r_tubo = self.client.get(f"/api/lab/codigos/por-codigo/{m.codigo_barra}/")
        self.assertEqual(r_tubo.status_code, status.HTTP_200_OK, r_tubo.content)
        self.assertEqual(r_tubo.json()["tipo"], "tubo")
        self.assertEqual(r_tubo.json()["muestra"]["id"], m.pk)

        r_micro = self.client.get(f"/api/lab/codigos/por-codigo/{est.codigo_barra}/")
        self.assertEqual(r_micro.status_code, status.HTTP_200_OK, r_micro.content)
        self.assertEqual(r_micro.json()["tipo"], "micro")

        # Protocolo de orden clínica sin sufijo → hint
        r_hint = self.client.get(f"/api/lab/codigos/por-codigo/{sol.numero}/")
        self.assertEqual(r_hint.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r_hint.json().get("code"), "need_tubo_suffix")

        with self.captureOnCommitCallbacks(execute=True):
            r_recv = self.client.post(
                "/api/lab/codigos/recibir-por-codigo/",
                {"codigo_barra": est.codigo_barra},
                format="json",
            )
        self.assertEqual(r_recv.status_code, status.HTTP_200_OK, r_recv.content)
        self.assertEqual(r_recv.json()["tipo"], "micro")
        self.assertEqual(r_recv.json()["estudio"]["estado"], "RECIBIDO")

    def test_legacy_mue_y_micb_siguen_resolviendo(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            numero="LAB-2098-00001",
        )
        m = Muestra(
            solicitud=sol,
            paciente=self.paciente,
            tipo_muestra=self.tm,
            codigo_barra="MUE-2098-000001",
            estado="PENDIENTE_TOMA",
        )
        m.save()
        est = EstudioMicrobiologia.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            tipo_estudio="CULTIVO_RUTINA",
            estado="PENDIENTE",
            numero="MIC-2098-000001",
            codigo_barra="MICB-2098-000001",
        )
        r1 = resolver_entidad("MUE-2098-000001")
        self.assertEqual(r1.tipo, "tubo")
        r2 = resolver_entidad("MICB-2098-000001")
        self.assertEqual(r2.tipo, "micro")
        self.assertEqual(format_tubo("LAB-2098-00001", 1), "LAB-2098-00001-01")
