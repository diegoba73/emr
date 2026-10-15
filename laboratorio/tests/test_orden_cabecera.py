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
from historias_clinicas.models import Consulta, HistoriaClinica
from laboratorio.orden_cabecera import (
    diagnostico_orden_display,
    diagnostico_para_impresion,
    fecha_extraccion_de_resultado_display,
    fecha_extraccion_display,
    fecha_solicitud_display,
    fechas_extraccion_distintas_en_orden,
    formatear_fecha_extraccion,
    lineas_extraccion_timeline,
    lineas_fechas_orden_timeline,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Atencion


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

    def test_fecha_solicitud_display(self):
        txt = fecha_solicitud_display(self.sol)
        self.assertEqual(txt, formatear_fecha_extraccion(self.sol.fecha_solicitud))

    def test_fecha_extraccion_por_resultado_y_muestras_distintas(self):
        tm_orina = TipoMuestra.objects.create(
            codigo=f"ORI{uuid.uuid4().hex[:5]}", nombre="Orina", activo=True
        )
        te_orina = TipoExamen.objects.create(
            codigo=f"URI{uuid.uuid4().hex[:5]}",
            nombre="Orina completa",
            tipo_muestra_requerida=tm_orina,
            precio=1,
            activo=True,
        )
        self.sol.tipos_examen.add(te_orina)
        res_sangre = self.sol.resultados.get(tipo_examen=self.te)
        res_orina = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=te_orina, valor_obtenido=""
        )

        m_sangre = crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        m_orina = crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=tm_orina.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        t_sangre = timezone.now() - timedelta(hours=3)
        t_orina = timezone.now() - timedelta(hours=1)
        type(m_sangre).objects.filter(pk=m_sangre.pk).update(fecha_toma=t_sangre)
        type(m_orina).objects.filter(pk=m_orina.pk).update(fecha_toma=t_orina)
        m_sangre.refresh_from_db()
        m_orina.refresh_from_db()

        self.assertTrue(
            fechas_extraccion_distintas_en_orden(
                self.sol, muestras=[m_sangre, m_orina]
            )
        )
        self.assertEqual(
            fecha_extraccion_de_resultado_display(
                res_sangre, muestras=[m_sangre, m_orina]
            ),
            formatear_fecha_extraccion(t_sangre),
        )
        self.assertEqual(
            fecha_extraccion_de_resultado_display(
                res_orina, muestras=[m_sangre, m_orina]
            ),
            formatear_fecha_extraccion(t_orina),
        )
        lineas = lineas_extraccion_timeline(
            self.sol, muestras=[m_sangre, m_orina]
        )
        self.assertEqual(len(lineas), 2)
        self.assertTrue(any("sangre" in ln.lower() or "orina" in ln.lower() for ln in lineas))
        fechas_tl = lineas_fechas_orden_timeline(
            self.sol, muestras=[m_sangre, m_orina]
        )
        self.assertTrue(fechas_tl[0].startswith("Solicitud:"))
        self.assertEqual(len(fechas_tl), 3)

    def test_lineas_extraccion_solo_un_material(self):
        m = crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        tomada = timezone.now() - timedelta(hours=1)
        type(m).objects.filter(pk=m.pk).update(fecha_toma=tomada)
        m.refresh_from_db()
        lineas = lineas_extraccion_timeline(self.sol, muestras=[m])
        self.assertEqual(len(lineas), 1)
        self.assertTrue(lineas[0].startswith("Extracción:"))
        self.assertNotIn("sangre", lineas[0].lower().split(":", 1)[0])

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
        self.assertEqual(diagnostico_para_impresion(self.sol), dx)

    def test_diagnostico_guardia_desde_motivo_atencion(self):
        suf = uuid.uuid4().hex[:6]
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        medico = Medico.objects.create(
            nombre="Ana",
            apellido="Guardia",
            matricula=f"MG-{suf}",
            especialidad=esp,
        )
        atencion = Atencion.objects.create(
            paciente=self.paciente,
            medico_principal=medico,
            contexto_atencion=Atencion.ContextoAtencion.GUARDIA,
            tipo_atencion=Atencion.ContextoAtencion.GUARDIA,
            observaciones_generales="Dolor precordial irradiado",
        )
        hc, _ = HistoriaClinica.objects.get_or_create(paciente=self.paciente)
        consulta = Consulta.objects.create(
            historia_clinica=hc,
            medico=medico,
            atencion=atencion,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle="Guardia cardiológica",
        )
        self.sol.consulta_hc = consulta
        self.sol.origen_solicitud = "GUARDIA"
        self.sol.save(update_fields=["consulta_hc", "origen_solicitud"])
        # Sin internación activa: el paciente de setUp no está internado.
        dx = diagnostico_orden_display(self.sol)
        self.assertEqual(dx, "Dolor precordial irradiado")
        self.assertEqual(diagnostico_para_impresion(self.sol), dx)

    def test_diagnostico_ambulatorio_consulta_presuntivo(self):
        suf = uuid.uuid4().hex[:6]
        esp = Especialidad.objects.create(nombre=f"EspA {suf}")
        medico = Medico.objects.create(
            nombre="Luis",
            apellido="Amb",
            matricula=f"MA-{suf}",
            especialidad=esp,
        )
        hc, _ = HistoriaClinica.objects.get_or_create(paciente=self.paciente)
        consulta = Consulta.objects.create(
            historia_clinica=hc,
            medico=medico,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle="Control",
            diagnostico_presuntivo="Dislipidemia mixta",
        )
        self.sol.consulta_hc = consulta
        self.sol.origen_solicitud = "AMBULATORIO_CEHTA"
        self.sol.save(update_fields=["consulta_hc", "origen_solicitud"])
        self.assertEqual(diagnostico_orden_display(self.sol), "Dislipidemia mixta")
        self.assertEqual(diagnostico_para_impresion(self.sol), "Dislipidemia mixta")
