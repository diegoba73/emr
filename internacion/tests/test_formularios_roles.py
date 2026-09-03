"""Lectura de HC por rol internación; escritura médico / enfermería / kinesiólogo."""
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from internacion.models import Cama, Internacion, Sector
from internacion.tests.helpers import unique_suffix
from pacientes.models import Paciente

User = get_user_model()


class FormulariosHcRolesTestCase(APITestCase):
    def setUp(self):
        suffix = unique_suffix()
        self.medico = User.objects.create_user(
            username=f'med-hc-{suffix}', password='x', email=f'med-hc-{suffix}@t.com', rol='medico',
        )
        self.enfermera = User.objects.create_user(
            username=f'enf-hc-{suffix}', password='x', email=f'enf-hc-{suffix}@t.com', rol='enfermeria',
        )
        self.kine = User.objects.create_user(
            username=f'kine-hc-{suffix}', password='x', email=f'kine-hc-{suffix}@t.com', rol='kinesiologo',
        )
        self.secretaria = User.objects.create_user(
            username=f'sec-hc-{suffix}', password='x', email=f'sec-hc-{suffix}@t.com', rol='secretaria',
        )
        self.paciente = Paciente.objects.create(nombre='Luis', apellido='Paz', dni=f'HC-{suffix}')
        self.sector = Sector.objects.create(nombre=f'UCE-hc-{suffix}')
        self.cama = Cama.objects.create(nombre=f'C-hc-{suffix}', sector=self.sector, estado='DISPONIBLE')
        self.internacion = Internacion.objects.create(
            paciente=self.paciente,
            cama=self.cama,
            diagnostico_ingreso='Neumonía',
            activo=True,
        )
        self.base = f'/api/internacion/internaciones/{self.internacion.id}'

    def test_kinesiologo_lista_internacion(self):
        self.client.force_authenticate(user=self.kine)
        response = self.client.get(f'{self.base}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['diagnostico_ingreso'], 'Neumonía')

    def test_medico_carga_indicacion_y_otros_leen(self):
        self.client.force_authenticate(user=self.medico)
        created = self.client.post(
            f'{self.base}/indicaciones-medicas/',
            {'indicaciones': 'O2 2 L/min', 'hidratacion': 'Vía oral'},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.enfermera)
        listed = self.client.get(f'{self.base}/indicaciones-medicas/')
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        rows = listed.data['results'] if isinstance(listed.data, dict) else listed.data
        self.assertEqual(rows[0]['indicaciones'], 'O2 2 L/min')

        self.client.force_authenticate(user=self.enfermera)
        denied = self.client.post(
            f'{self.base}/indicaciones-medicas/',
            {'indicaciones': 'no'},
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_enfermeria_carga_control_medico_no(self):
        self.client.force_authenticate(user=self.medico)
        denied = self.client.post(
            f'{self.base}/controles-enfermeria/',
            {'turno': 'MANANA', 'tension_arterial': '120/80'},
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.enfermera)
        created = self.client.post(
            f'{self.base}/controles-enfermeria/',
            {'turno': 'MANANA', 'tension_arterial': '120/80', 'glucemia': 110},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.kine)
        listed = self.client.get(f'{self.base}/controles-enfermeria/')
        self.assertEqual(listed.status_code, status.HTTP_200_OK)

    def test_kine_carga_hoja_propia_secretaria_no(self):
        self.client.force_authenticate(user=self.kine)
        created = self.client.post(
            f'{self.base}/kinesiologia/',
            {'evolucion': 'Buena tolerancia a kinesio respiratoria', 'plan': '2 sesiones/día'},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.secretaria)
        listed = self.client.get(f'{self.base}/kinesiologia/')
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        denied = self.client.post(
            f'{self.base}/kinesiologia/',
            {'evolucion': 'no'},
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_solo_medico_edita_anamnesis_ingreso(self):
        self.client.force_authenticate(user=self.enfermera)
        denied = self.client.patch(
            f'{self.base}/',
            {'anamnesis_ingreso': 'no debería'},
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.medico)
        ok = self.client.patch(
            f'{self.base}/',
            {'anamnesis_ingreso': 'Disnea de 48 hs'},
            format='json',
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(ok.data['anamnesis_ingreso'], 'Disnea de 48 hs')

    def test_enfermeria_no_inicia_evolucion_diaria(self):
        self.client.force_authenticate(user=self.enfermera)
        response = self.client.post(f'{self.base}/iniciar-evolucion/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
