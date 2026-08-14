"""Secretaría: ve internación; no ingresa, no edita infra ni da alta."""
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from catalogos.models import DiagnosticoCIE10
from internacion.models import Sector, Cama, Internacion
from internacion.tests.helpers import unique_cie10_code, unique_suffix
from pacientes.models import Paciente

User = get_user_model()


class SecretariaInternacionAccesoTestCase(APITestCase):
    def setUp(self):
        suffix = unique_suffix()
        self.secretaria = User.objects.create_user(
            username=f'sec-int-{suffix}',
            password='x',
            email=f'sec-int-{suffix}@test.com',
            rol='secretaria',
        )
        self.paciente_rol = User.objects.create_user(
            username=f'pac-int-{suffix}',
            password='x',
            email=f'pac-int-{suffix}@test.com',
            rol='paciente',
        )
        self.paciente = Paciente.objects.create(
            nombre='Ana',
            apellido='Ruiz',
            dni=f'SEC-{suffix}',
        )
        self.sector = Sector.objects.create(nombre=f'UCO-sec-{suffix}')
        self.cama = Cama.objects.create(
            nombre=f'C-sec-{suffix}',
            sector=self.sector,
            estado='DISPONIBLE',
        )
        self.cie = DiagnosticoCIE10.objects.create(
            codigo=unique_cie10_code('I'),
            descripcion='Infarto agudo de miocardio',
            categoria='Cardiología',
            capitulo='IX',
            enfermedad='IAM',
        )
        self.internacion = Internacion.objects.create(
            paciente=self.paciente,
            cama=self.cama,
            diagnostico_cie=self.cie,
            diagnostico_ingreso='IAM anterior',
            activo=True,
        )

    def test_secretaria_lista_camas_con_diagnostico(self):
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.get('/api/internacion/camas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results'] if isinstance(response.data, dict) else response.data
        ocupada = next(c for c in payload if c['id'] == self.cama.id)
        diagnostico = ocupada['internacion_actual']['diagnostico']
        self.assertIn(self.cie.codigo, diagnostico)
        self.assertIn('Infarto', diagnostico)

    def test_secretaria_ve_diagnostico_en_detalle(self):
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.get(f'/api/internacion/internaciones/{self.internacion.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['diagnostico_cie']['codigo'], self.cie.codigo)
        self.assertEqual(response.data['diagnostico_ingreso'], 'IAM anterior')

    def test_secretaria_puede_buscar_cie10(self):
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.get('/api/diagnosticos-cie10/buscar/', {'q': self.cie.codigo[:2]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_secretaria_no_crea_cama(self):
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.post(
            '/api/internacion/camas/',
            {
                'nombre': f'C-bloqueada-{unique_suffix()}',
                'sector_id': self.sector.id,
                'estado': 'DISPONIBLE',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_secretaria_no_inicia_evolucion(self):
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.post(
            f'/api/internacion/internaciones/{self.internacion.id}/iniciar-evolucion/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_secretaria_lista_evoluciones(self):
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.get(
            f'/api/internacion/internaciones/{self.internacion.id}/evoluciones/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_secretaria_no_ingresa_paciente(self):
        cama_libre = Cama.objects.create(
            nombre=f'C-libre-{unique_suffix()}',
            sector=self.sector,
            estado='DISPONIBLE',
        )
        paciente_libre = Paciente.objects.create(
            nombre='Luis',
            apellido='Sosa',
            dni=f'SEC-IN-{unique_suffix()}',
        )
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.post(
            '/api/internacion/internaciones/',
            {
                'paciente': paciente_libre.id,
                'cama': cama_libre.id,
                'diagnostico_ingreso': 'Intento de ingreso',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_secretaria_no_da_alta(self):
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.post(
            f'/api/internacion/internaciones/{self.internacion.id}/alta/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enfermeria_puede_ingresar_no_da_alta(self):
        enfermeria = User.objects.create_user(
            username=f'enf-int-{unique_suffix()}',
            password='x',
            email=f'enf-int-{unique_suffix()}@test.com',
            rol='enfermeria',
        )
        cama_libre = Cama.objects.create(
            nombre=f'C-enf-{unique_suffix()}',
            sector=self.sector,
            estado='DISPONIBLE',
        )
        paciente_libre = Paciente.objects.create(
            nombre='Nora',
            apellido='Vega',
            dni=f'ENF-IN-{unique_suffix()}',
        )
        self.client.force_authenticate(user=enfermeria)
        ingresar = self.client.post(
            '/api/internacion/internaciones/',
            {
                'paciente': paciente_libre.id,
                'cama': cama_libre.id,
                'diagnostico_ingreso': 'Ingreso de enfermería',
            },
            format='json',
        )
        self.assertEqual(ingresar.status_code, status.HTTP_201_CREATED)
        alta = self.client.post(
            f'/api/internacion/internaciones/{self.internacion.id}/alta/'
        )
        self.assertEqual(alta.status_code, status.HTTP_403_FORBIDDEN)

    def test_medico_puede_dar_alta(self):
        medico = User.objects.create_user(
            username=f'med-int-{unique_suffix()}',
            password='x',
            email=f'med-int-{unique_suffix()}@test.com',
            rol='medico',
        )
        self.client.force_authenticate(user=medico)
        response = self.client.post(
            f'/api/internacion/internaciones/{self.internacion.id}/alta/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.internacion.refresh_from_db()
        self.assertFalse(self.internacion.activo)

    def test_paciente_no_lista_camas(self):
        self.client.force_authenticate(user=self.paciente_rol)
        response = self.client.get('/api/internacion/camas/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
