"""Fase 0: ficha de ingreso HC (cabecera, alergias, medicación habitual)."""
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from internacion.models import Cama, Internacion, MedicacionHabitualInternacion, Sector
from internacion.tests.helpers import unique_suffix
from pacientes.models import Paciente

User = get_user_model()


class Fase0IngresoHcTestCase(APITestCase):
    def setUp(self):
        suffix = unique_suffix()
        self.medico = User.objects.create_user(
            username=f'med-f0-{suffix}', password='x', email=f'med-f0-{suffix}@t.com', rol='medico',
        )
        self.enfermera = User.objects.create_user(
            username=f'enf-f0-{suffix}', password='x', email=f'enf-f0-{suffix}@t.com', rol='enfermeria',
        )
        self.kine = User.objects.create_user(
            username=f'kine-f0-{suffix}', password='x', email=f'kine-f0-{suffix}@t.com', rol='kinesiologo',
        )
        self.paciente = Paciente.objects.create(
            nombre='Marta',
            apellido='Sol',
            dni=f'F0-{suffix}',
            obra_social='PAMI',
        )
        self.sector = Sector.objects.create(nombre=f'UCO-f0-{suffix}')
        self.cama = Cama.objects.create(nombre=f'C-f0-{suffix}', sector=self.sector, estado='DISPONIBLE')
        self.internacion = Internacion.objects.create(
            paciente=self.paciente,
            cama=self.cama,
            diagnostico_ingreso='SCA',
            activo=True,
        )
        self.base = f'/api/internacion/internaciones/{self.internacion.id}'

    def test_kine_lee_cabecera(self):
        self.client.force_authenticate(user=self.kine)
        response = self.client.get(f'{self.base}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cab = response.data['paciente_cabecera']
        self.assertEqual(cab['dni'], self.paciente.dni)
        self.assertEqual(cab['obra_social'], 'PAMI')
        self.assertEqual(cab['cama'], self.cama.nombre)

    def test_medico_carga_ingreso_y_enfermeria_no(self):
        self.client.force_authenticate(user=self.enfermera)
        denied = self.client.patch(
            f'{self.base}/',
            {'motivo_ingreso': 'no debería', 'tiene_alergias': True},
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.medico)
        ok = self.client.patch(
            f'{self.base}/',
            {
                'motivo_ingreso': 'Dolor precordial',
                'anamnesis_ingreso': 'Inicio hace 2 horas',
                'tiene_alergias': True,
                'alergias': 'Penicilina',
                'plan_estudio_tratamiento': 'ECG + enzimas',
                'estado_civil': 'casada',
                'familiar_nombre': 'Juan Sol',
                'familiar_telefono': '2804123456',
            },
            format='json',
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(ok.data['motivo_ingreso'], 'Dolor precordial')
        self.assertTrue(ok.data['tiene_alergias'])
        self.assertEqual(ok.data['alergias'], 'Penicilina')
        self.assertEqual(ok.data['paciente_cabecera']['familiar_nombre'], 'Juan Sol')
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.estado_civil, 'casada')
        self.assertEqual(self.paciente.familiar_telefono, '2804123456')

    def test_medicacion_habitual_solo_medico_escribe(self):
        self.client.force_authenticate(user=self.enfermera)
        denied = self.client.post(
            f'{self.base}/medicaciones-habituales/',
            {'medicamento': 'Enalapril', 'dosis_mg_dia': '10'},
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.medico)
        created = self.client.post(
            f'{self.base}/medicaciones-habituales/',
            {'medicamento': 'Enalapril', 'dosis_mg_dia': '10'},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.internacion.refresh_from_db()
        self.assertIn('Enalapril', self.internacion.medicacion_habitual)
        self.assertEqual(MedicacionHabitualInternacion.objects.filter(internacion=self.internacion).count(), 1)

        self.client.force_authenticate(user=self.kine)
        listed = self.client.get(f'{self.base}/medicaciones-habituales/')
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        rows = listed.data['results'] if isinstance(listed.data, dict) else listed.data
        self.assertEqual(rows[0]['medicamento'], 'Enalapril')
