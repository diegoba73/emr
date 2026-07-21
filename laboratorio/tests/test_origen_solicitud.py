"""Tests de inferencia de origen clínico LIMS."""
from django.test import TestCase
from django.utils import timezone

from historias_clinicas.models import Consulta, HistoriaClinica
from internacion.models import Cama, Internacion, Sector
from laboratorio.origen_solicitud import (
    AMBULATORIO_CEHTA,
    AMBULATORIO_ICPL,
    EXTERNO_CEHTA,
    EXTERNO_ICPL,
    GUARDIA,
    INTERNACION_UCE,
    INTERNACION_UCO,
    es_origen_ambulatorio_externo,
    inferir_origen_solicitud,
    label_origen_solicitud,
    procedencia_display_externo,
)
from laboratorio.models import SolicitudExamen
from laboratorio.procedencia_display import resolver_procedencia_solicitud
from pacientes.models import Paciente
from turnos.models import Recurso, Turno


class TestInferirOrigenSolicitud(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            nombre='Juan',
            apellido='Pérez',
            dni='30111222',
            fecha_nacimiento='1980-01-01',
        )
        self.hc = HistoriaClinica.objects.create(paciente=self.paciente)

    def test_ambulatorio_cehta_desde_recurso(self):
        recurso = Recurso.objects.create(
            nombre='Consultorio CEHTA 1',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        )
        turno = Turno.objects.create(
            paciente=self.paciente,
            recurso=recurso,
            fecha_hora_inicio=timezone.now(),
            estado=Turno.Estado.REALIZADO,
        )
        consulta = Consulta.objects.create(
            historia_clinica=self.hc,
            turno=turno,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Control',
        )
        origen = inferir_origen_solicitud(
            paciente_id=self.paciente.pk,
            consulta_hc=consulta,
        )
        self.assertEqual(origen, AMBULATORIO_CEHTA)

    def test_ambulatorio_icpl_desde_recurso(self):
        recurso = Recurso.objects.create(
            nombre='Consultorio ICPL 1',
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        )
        turno = Turno.objects.create(
            paciente=self.paciente,
            recurso=recurso,
            fecha_hora_inicio=timezone.now(),
            estado=Turno.Estado.REALIZADO,
        )
        consulta = Consulta.objects.create(
            historia_clinica=self.hc,
            turno=turno,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Control',
        )
        self.assertEqual(
            inferir_origen_solicitud(paciente_id=self.paciente.pk, consulta_hc=consulta),
            AMBULATORIO_ICPL,
        )

    def test_guardia_desde_atencion_walk_in_sin_turno(self):
        from medicos.models import Especialidad, Medico
        from historias_clinicas.services import ensure_consulta_hc_desde_atencion
        from turnos.services import AtencionService

        esp, _ = Especialidad.objects.get_or_create(nombre='Cardio-guard-walk')
        medico = Medico.objects.create(
            matricula='M-GW-001',
            nombre='Laura',
            apellido='Guardia',
            especialidad=esp,
        )
        outcome = AtencionService.iniciar_atencion_guardia(
            paciente_id=self.paciente.pk,
            medico_id=medico.pk,
            motivo_consulta='Dolor torácico',
        )
        consulta = ensure_consulta_hc_desde_atencion(outcome.atencion)
        self.assertEqual(
            inferir_origen_solicitud(paciente_id=self.paciente.pk, consulta_hc=consulta),
            GUARDIA,
        )
        from laboratorio.models import SolicitudExamen

        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            consulta_hc=consulta,
            origen_solicitud=GUARDIA,
        )
        proc = resolver_procedencia_solicitud(solicitud)
        self.assertEqual(proc['procedencia_tipo'], 'GUARDIA')
        self.assertIn('ICPL', proc['procedencia_display'])

    def test_guardia_desde_nombre_recurso(self):
        recurso = Recurso.objects.create(
            nombre='Guardia cardiológica ICPL',
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        )
        turno = Turno.objects.create(
            paciente=self.paciente,
            recurso=recurso,
            fecha_hora_inicio=timezone.now(),
            estado=Turno.Estado.REALIZADO,
        )
        consulta = Consulta.objects.create(
            historia_clinica=self.hc,
            turno=turno,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Dolor torácico',
        )
        self.assertEqual(
            inferir_origen_solicitud(paciente_id=self.paciente.pk, consulta_hc=consulta),
            GUARDIA,
        )

    def test_internacion_uco_prioriza_sobre_consulta(self):
        sector = Sector.objects.create(nombre='UCO-test')
        cama = Cama.objects.create(nombre='C1', sector=sector)
        Internacion.objects.create(paciente=self.paciente, cama=cama, activo=True)
        recurso = Recurso.objects.create(
            nombre='Consultorio CEHTA 2',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        )
        turno = Turno.objects.create(
            paciente=self.paciente,
            recurso=recurso,
            fecha_hora_inicio=timezone.now(),
            estado=Turno.Estado.REALIZADO,
        )
        consulta = Consulta.objects.create(
            historia_clinica=self.hc,
            turno=turno,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Interconsulta',
        )
        self.assertEqual(
            inferir_origen_solicitud(paciente_id=self.paciente.pk, consulta_hc=consulta),
            INTERNACION_UCO,
        )

    def test_internacion_uce(self):
        sector = Sector.objects.create(nombre='UCE-test')
        cama = Cama.objects.create(nombre='C2', sector=sector)
        Internacion.objects.create(paciente=self.paciente, cama=cama, activo=True)
        self.assertEqual(
            inferir_origen_solicitud(paciente_id=self.paciente.pk),
            INTERNACION_UCE,
        )

    def test_label_origen(self):
        self.assertEqual(label_origen_solicitud(AMBULATORIO_ICPL), 'Ambulatorio — ICPL')
        self.assertEqual(label_origen_solicitud(EXTERNO_CEHTA), 'Ambulatorio externo — CEHTA')
        self.assertEqual(label_origen_solicitud(EXTERNO_ICPL), 'Ambulatorio externo — ICPL')

    def test_origen_externo_explicito_sin_consulta(self):
        self.assertEqual(
            inferir_origen_solicitud(
                paciente_id=self.paciente.pk,
                origen_explicito=EXTERNO_ICPL,
            ),
            EXTERNO_ICPL,
        )

    def test_origen_externo_no_inferido_desde_consulta(self):
        recurso = Recurso.objects.create(
            nombre='Consultorio CEHTA 1',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        )
        turno = Turno.objects.create(
            paciente=self.paciente,
            recurso=recurso,
            fecha_hora_inicio=timezone.now(),
            estado=Turno.Estado.REALIZADO,
        )
        consulta = Consulta.objects.create(
            historia_clinica=self.hc,
            turno=turno,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Control',
        )
        self.assertEqual(
            inferir_origen_solicitud(
                paciente_id=self.paciente.pk,
                consulta_hc=consulta,
            ),
            AMBULATORIO_CEHTA,
        )

    def test_procedencia_display_externo_cehta(self):
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud=EXTERNO_CEHTA,
            medico_externo_nombre='Dr. García',
        )
        self.assertTrue(es_origen_ambulatorio_externo(solicitud.origen_solicitud))
        self.assertEqual(
            procedencia_display_externo(solicitud),
            'Receta externa — presentada en CEHTA · Dr. García',
        )
        proc = resolver_procedencia_solicitud(solicitud)
        self.assertIn('Receta externa', proc['procedencia_display'])
        self.assertIn('Dr. García', proc['procedencia_display'])

    def test_procedencia_display_externo_icpl_sin_medico(self):
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud=EXTERNO_ICPL,
        )
        self.assertEqual(
            procedencia_display_externo(solicitud),
            'Receta externa — presentada en ICPL',
        )
