"""Fecha de extracción y diagnóstico de cabecera de orden LIMS."""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from catalogos.models import DiagnosticoCIE10
from internacion.models import Cama, Internacion, Sector
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.muestra_estado import crear_muestra
from laboratorio.orden_cabecera import (
    diagnostico_orden_display,
    fecha_extraccion_display,
    formatear_fecha_extraccion,
)
from pacientes.models import Paciente


class TestOrdenCabecera(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.paciente = Paciente.objects.create(
            dni=f"9{suf[:7]}",
            nombre="Luis",
            apellido="Cabecera",
            antecedentes_personales="HTA crónica",
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"TM{suf}", nombre="Sangre", activo=True
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{suf}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            fecha_programada_toma=timezone.localdate(),
        )
        self.sol.tipos_examen.add(self.te)
        ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te, valor_obtenido=""
        )

    def test_fecha_fallback_programada(self):
        txt = fecha_extraccion_display(self.sol)
        self.assertEqual(txt, formatear_fecha_extraccion(self.sol.fecha_programada_toma))

    def test_fecha_desde_muestra(self):
        m = crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        tomada = timezone.now() - timedelta(hours=2)
        type(m).objects.filter(pk=m.pk).update(fecha_toma=tomada)
        self.sol.refresh_from_db()
        txt = fecha_extraccion_display(self.sol)
        self.assertIn(formatear_fecha_extraccion(tomada), txt)

    def test_diagnostico_ambulatorio_antecedentes(self):
        self.assertEqual(diagnostico_orden_display(self.sol), "HTA crónica")

    def test_diagnostico_internacion_desde_cama(self):
        suf = uuid.uuid4().hex[:6]
        sector = Sector.objects.create(nombre=f"Sec {suf}", activo=True)
        cama = Cama.objects.create(
            nombre=f"C{suf}", sector=sector, estado="DISPONIBLE", activo=True
        )
        cie = DiagnosticoCIE10.objects.create(
            codigo=f"J{suf[:3]}",
            descripcion="Neumonía prueba",
            categoria="Respiratorio",
        )
        internacion = Internacion.objects.create(
            paciente=self.paciente,
            cama=cama,
            activo=True,
            diagnostico_cie=cie,
            diagnostico_ingreso="texto libre ignorado si hay CIE",
        )
        Internacion.objects.filter(pk=internacion.pk).update(
            fecha_ingreso=self.sol.fecha_solicitud - timedelta(hours=1)
        )
        dx = diagnostico_orden_display(self.sol)
        self.assertIn("Neumonía prueba", dx)
        self.assertIn(cie.codigo, dx)
