"""Tests de evoluciones clínicas durante internación."""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from internacion.models import Sector, Cama, Internacion
from internacion.services import InternacionClinicalService, InternacionClinicalError
from internacion.tests.helpers import unique_suffix
from medicos.models import Medico, Especialidad
from pacientes.models import Paciente
from turnos.models import Atencion, EvolucionInternacion

User = get_user_model()


class EvolucionInternacionTestCase(APITestCase):
    def setUp(self):
        suffix = unique_suffix()
        self.user = User.objects.create_user(
            username=f'med-int-{suffix}',
            password='testpass123',
            email=f'med-int-{suffix}@test.com',
            rol='medico',
        )
        esp, _ = Especialidad.objects.get_or_create(nombre=f'Cardio-{suffix}')
        self.medico = Medico.objects.create(
            matricula=f'MI-{suffix}',
            nombre='Carlos',
            apellido='Med',
            especialidad=esp,
            user=self.user,
        )
        self.paciente = Paciente.objects.create(
            dni=f'PI-{suffix}',
            nombre='Pedro',
            apellido='Lopez',
        )
        self.sector = Sector.objects.create(nombre=f'UCO-evo-{suffix}')
        self.cama = Cama.objects.create(
            nombre=f'C-evo-{suffix}',
            sector=self.sector,
            estado='DISPONIBLE',
        )
        self.internacion = Internacion.objects.create(
            paciente=self.paciente,
            cama=self.cama,
            medico=self.medico,
            diagnostico_ingreso='Insuficiencia cardíaca',
            activo=True,
        )

    def test_iniciar_evolucion_diaria_crea_atencion_y_registro(self):
        outcome = InternacionClinicalService.iniciar_evolucion_internacion(
            self.internacion,
            medico=self.medico,
        )
        self.assertEqual(outcome.atencion.contexto_atencion, Atencion.ContextoAtencion.INTERNACION)
        self.assertEqual(outcome.atencion.internacion_id, self.internacion.pk)
        self.assertIsNone(outcome.atencion.turno_id)
        self.assertEqual(
            outcome.evolucion.tipo_evolucion,
            EvolucionInternacion.TipoEvolucion.EVOLUCION_DIARIA,
        )

    def test_iniciar_evolucion_diaria_reutiliza_la_de_hoy(self):
        first = InternacionClinicalService.iniciar_evolucion_internacion(
            self.internacion,
            medico=self.medico,
        )
        second = InternacionClinicalService.iniciar_evolucion_internacion(
            self.internacion,
            medico=self.medico,
        )
        self.assertTrue(first.created_new)
        self.assertFalse(second.created_new)
        self.assertEqual(first.atencion.pk, second.atencion.pk)
        self.assertEqual(
            EvolucionInternacion.objects.filter(
                atencion__internacion=self.internacion,
                tipo_evolucion=EvolucionInternacion.TipoEvolucion.EVOLUCION_DIARIA,
            ).count(),
            1,
        )

    def test_interconsulta_sin_limite_diario(self):
        InternacionClinicalService.iniciar_evolucion_internacion(
            self.internacion,
            medico=self.medico,
        )
        outcome = InternacionClinicalService.iniciar_evolucion_internacion(
            self.internacion,
            medico=self.medico,
            tipo_evolucion=EvolucionInternacion.TipoEvolucion.INTERCONSULTA,
        )
        self.assertEqual(
            outcome.evolucion.tipo_evolucion,
            EvolucionInternacion.TipoEvolucion.INTERCONSULTA,
        )

    def test_api_iniciar_evolucion(self):
        self.client.force_authenticate(user=self.user)
        url = f'/api/internacion/internaciones/{self.internacion.pk}/iniciar-evolucion/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['contexto_atencion'], 'INTERNACION')
        self.assertIn('evolucion_internacion', response.data)
        second = self.client.post(url, {}, format='json')
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data['id'], response.data['id'])

    def test_api_evoluciones_lista_por_internacion(self):
        InternacionClinicalService.iniciar_evolucion_internacion(
            self.internacion,
            medico=self.medico,
        )
        self.client.force_authenticate(user=self.user)
        url = f'/api/internacion/internaciones/{self.internacion.pk}/evoluciones/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['evolucion_diaria_hoy'])
        self.assertEqual(len(response.data['atenciones']), 1)

    def test_no_evolucion_en_internacion_inactiva(self):
        self.internacion.fecha_alta = timezone.now()
        self.internacion.save()
        with self.assertRaises(InternacionClinicalError):
            InternacionClinicalService.iniciar_evolucion_internacion(
                self.internacion,
                medico=self.medico,
            )

    def test_numero_internacion_autogenerado(self):
        self.assertTrue(self.internacion.numero_internacion)
        self.assertTrue(self.internacion.numero_internacion.startswith('INT-'))

    def test_filtro_atenciones_por_contexto(self):
        InternacionClinicalService.iniciar_evolucion_internacion(
            self.internacion,
            medico=self.medico,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            '/api/atenciones/',
            {'paciente': self.paciente.pk, 'contexto_atencion': 'INTERNACION'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['contexto_atencion'], 'INTERNACION')

    def test_api_contexto_revista_incluye_labs_estudios_y_soap(self):
        from estudios.models import EstudioComplementario, TipoEstudioComplementario
        from laboratorio.models import TipoMuestra, TipoExamen, SolicitudExamen, ResultadoExamen
        from laboratorio.origen_solicitud import AMBULATORIO_CEHTA, INTERNACION_UCO

        outcome = InternacionClinicalService.iniciar_evolucion_internacion(
            self.internacion,
            medico=self.medico,
        )
        outcome.evolucion.analisis = 'Mejora clínica'
        outcome.evolucion.save(update_fields=['analisis'])

        suffix = unique_suffix()
        tipo_muestra = TipoMuestra.objects.create(
            codigo=f'SNG{suffix}'[:20],
            nombre='Sangre',
        )
        tipo_examen = TipoExamen.objects.create(
            codigo=f'GLU{suffix}'[:20],
            nombre='Glucosa',
            tipo_muestra_requerida=tipo_muestra,
            precio=10,
            activo=True,
        )
        solicitud = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud=INTERNACION_UCO,
            estado='FINALIZADO',
        )
        solicitud.tipos_examen.add(tipo_examen)
        ResultadoExamen.objects.create(
            solicitud=solicitud,
            tipo_examen=tipo_examen,
            valor_obtenido='110',
            unidad='mg/dL',
        )
        ambulatoria = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud=AMBULATORIO_CEHTA,
            estado='FINALIZADO',
        )
        ambulatoria.tipos_examen.add(tipo_examen)
        tipo_est = TipoEstudioComplementario.objects.create(
            nombre=f'RX torax {suffix}',
            modalidad=TipoEstudioComplementario.Modalidad.IMAGEN_RX,
        )
        EstudioComplementario.objects.create(
            paciente=self.paciente,
            tipo_estudio=tipo_est,
            modalidad=tipo_est.modalidad,
            estado=EstudioComplementario.Estado.SOLICITADO,
            medico_solicitante=self.medico,
        )

        self.client.force_authenticate(user=self.user)
        url = f'/api/internacion/internaciones/{self.internacion.pk}/contexto-revista/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['paciente_id'], self.paciente.pk)
        self.assertIsNotNone(response.data['evolucion_hoy'])
        self.assertEqual(response.data['evolucion_hoy']['analisis'], 'Mejora clínica')
        self.assertEqual(len(response.data['laboratorio']), 1)
        self.assertEqual(response.data['laboratorio'][0]['id'], solicitud.pk)
        self.assertTrue(response.data['laboratorio'][0]['es_de_hoy'])
        self.assertEqual(len(response.data['estudios']), 1)
