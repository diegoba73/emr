"""Listado bandeja: pedido_adicional en batch (sin N+1 por fila)."""
from __future__ import annotations

from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from laboratorio.listado_bandeja_prefetch import warm_listado_bandeja_context
from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.serializers import SolicitudExamenListSerializer
from medicos.models import Medico
from pacientes.models import Paciente
from usuarios.models import User


class ListadoBandejaPrefetchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="lab_list_pref", password="x", rol="laboratorio"
        )
        cls.medico = Medico.objects.create(
            nombre="Ana", apellido="Lab", matricula="MP-LIST-1"
        )
        tm = TipoMuestra.objects.create(
            codigo="SUERO_LIST_PREF",
            nombre="Suero pref",
            color_tubo="Rojo",
            activo=True,
        )
        cls.te = TipoExamen.objects.create(
            codigo="GLU_LIST_PREF",
            nombre="Glucemia pref",
            tipo_muestra_requerida=tm,
            activo=True,
        )
        hoy = timezone.localdate()
        cls.sols = []
        for i in range(12):
            pac = Paciente.objects.create(
                dni=f"7700{i:04d}",
                nombre=f"P{i}",
                apellido="Prefetch",
            )
            sol = SolicitudExamen.objects.create(
                paciente=pac,
                medico_interno=cls.medico,
                origen_solicitud="AMBULATORIO_CEHTA",
                estado="PENDIENTE",
                material_pedido="SANGRE",
                fecha_programada_toma=hoy,
                observaciones="test_listado_bandeja_prefetch",
            )
            sol.tipos_examen.set([cls.te])
            cls.sols.append(sol)

    def test_pedido_adicional_batch_pocas_queries(self):
        factory = APIRequestFactory()
        request = factory.get("/api/lab/solicitudes/")
        request.user = self.user
        qs = (
            SolicitudExamen.objects.filter(
                observaciones="test_listado_bandeja_prefetch"
            )
            .select_related("paciente", "medico_interno", "consulta_hc__turno__recurso")
            .prefetch_related(
                "muestras__tipo_contenedor",
                "muestras__tipo_muestra",
                "tipos_examen__tipo_muestra_requerida",
                "paneles__tipos_examen__tipo_muestra_requerida",
            )
        )
        with CaptureQueriesContext(connection) as ctx:
            ser = SolicitudExamenListSerializer(
                qs, many=True, context={"request": request}
            )
            data = ser.data
        self.assertEqual(len(data), 12)
        # Sin batch serían ~1–2 queries extra por fila abierta (≥12).
        # Con batch: prefetch base + 1 candidatos pedido_adicional (+ internación opcional).
        self.assertLess(
            len(ctx.captured_queries),
            25,
            msg=f"Demasiadas queries ({len(ctx.captured_queries)}): listado no batchéó bien",
        )
        self.assertTrue(all("pedido_adicional" in row for row in data))
        self.assertFalse(any(row["pedido_adicional"] for row in data))

    def test_warm_marca_pedido_adicional_si_hay_bloqueada(self):
        abierta = self.sols[0]
        # Otra orden del mismo paciente en curso
        SolicitudExamen.objects.create(
            paciente=abierta.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
            material_pedido="ORINA",
            fecha_programada_toma=timezone.localdate(),
            observaciones="test_listado_bandeja_prefetch_bloquea",
        )
        ctx: dict = {}
        warm_listado_bandeja_context([abierta], ctx)
        self.assertTrue(ctx["pedido_adicional_by_id"][abierta.pk])
