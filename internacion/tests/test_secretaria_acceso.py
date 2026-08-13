"""Secretaría: diagnóstico visible al abrir la cama; sin evoluciones ni infra."""
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

    def test_secretaria_no_lista_evoluciones(self):
        self.client.force_authenticate(user=self.secretaria)
        response = self.client.get(
            f'/api/internacion/internaciones/{self.internacion.id}/evoluciones/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_paciente_no_lista_camas(self):
        self.client.force_authenticate(user=self.paciente_rol)
        response = self.client.get('/api/internacion/camas/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
