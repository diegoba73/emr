"""
Tests para el proceso de admisión (ingreso) de pacientes al módulo de Internación.
"""
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from internacion.models import Sector, Cama, Internacion
from internacion.tests.helpers import unique_suffix
from pacientes.models import Paciente

User = get_user_model()


class AdmisionAPITestCase(APITestCase):
    """Tests para el proceso de admisión de pacientes"""

    def setUp(self):
        suffix = unique_suffix()

        self.user_medico = User.objects.create_user(
            username=f'medico-adm-{suffix}',
            password='testpass123',
            email=f'medico-adm-{suffix}@test.com',
            rol='medico',
        )

        self.sector_uco = Sector.objects.create(nombre=f'UCO-adm-{suffix}')
        self.sector_uce = Sector.objects.create(nombre=f'UCE-adm-{suffix}')

        self.cama_disponible = Cama.objects.create(
            nombre=f'Cama-disp-{suffix}',
            sector=self.sector_uco,
            estado='DISPONIBLE',
            aislada=False,
        )

        # La internación activa debe crearse sobre cama DISPONIBLE; el modelo la marca OCUPADA.
        self.cama_ocupada = Cama.objects.create(
            nombre=f'Cama-ocup-{suffix}',
            sector=self.sector_uco,
            estado='DISPONIBLE',
            aislada=False,
        )

        self.paciente_libre = Paciente.objects.create(
            nombre='Juan',
            apellido='Pérez',
            dni=f'12345678-{suffix}',
            fecha_nacimiento='1990-01-01',
            sexo='M',
            telefono='1234567890',
            email=f'juan-{suffix}@test.com',
        )

        self.paciente_internado = Paciente.objects.create(
            nombre='María',
            apellido='González',
            dni=f'87654321-{suffix}',
            fecha_nacimiento='1985-05-15',
            sexo='F',
            telefono='0987654321',
            email=f'maria-{suffix}@test.com',
        )

        self.internacion_activa = Internacion.objects.create(
            paciente=self.paciente_internado,
            cama=self.cama_ocupada,
            diagnostico_ingreso='Diagnóstico de prueba',
            activo=True,
        )
        self.cama_ocupada.refresh_from_db()
        self.assertEqual(self.cama_ocupada.estado, 'OCUPADA')

    def test_admitir_paciente_libre_en_cama_disponible(self):
        """Happy path: paciente libre en cama disponible → 201 y cama OCUPADA."""
        self.client.force_authenticate(user=self.user_medico)

        data = {
            'paciente': self.paciente_libre.id,
            'cama': self.cama_disponible.id,
            'diagnostico_ingreso': 'Paciente con diagnóstico de prueba',
        }

        response = self.client.post('/api/internacion/internaciones/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        internacion = Internacion.objects.get(paciente=self.paciente_libre, activo=True)
        self.assertIsNotNone(internacion)
        self.assertEqual(internacion.cama, self.cama_disponible)

        self.cama_disponible.refresh_from_db()
        self.assertEqual(self.cama_disponible.estado, 'OCUPADA')

    def test_admitir_en_cama_ocupada_falla(self):
        """Intentar admitir en cama ocupada → 400."""
        self.client.force_authenticate(user=self.user_medico)

        data = {
            'paciente': self.paciente_libre.id,
            'cama': self.cama_ocupada.id,
            'diagnostico_ingreso': 'Intento de ingreso en cama ocupada',
        }

        response = self.client.post('/api/internacion/internaciones/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cama', response.data)
        self.assertIn('no está disponible', str(response.data['cama']))

        self.assertFalse(
            Internacion.objects.filter(
                paciente=self.paciente_libre,
                cama=self.cama_ocupada,
                activo=True,
            ).exists()
        )

    def test_admitir_paciente_ya_internado_falla(self):
        """Paciente ya internado → 400."""
        self.client.force_authenticate(user=self.user_medico)

        cama_nueva = Cama.objects.create(
            nombre=f'Cama-nueva-{unique_suffix()}',
            sector=self.sector_uce,
            estado='DISPONIBLE',
            aislada=False,
        )

        data = {
            'paciente': self.paciente_internado.id,
            'cama': cama_nueva.id,
            'diagnostico_ingreso': 'Intento de doble internación',
        }

        response = self.client.post('/api/internacion/internaciones/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('paciente', response.data)
        self.assertIn('ya está internado', str(response.data['paciente']))

        internaciones_activas = Internacion.objects.filter(
            paciente=self.paciente_internado,
            activo=True,
        )
        self.assertEqual(internaciones_activas.count(), 1)
        self.assertEqual(internaciones_activas.first().cama, self.cama_ocupada)

    def test_admitir_sin_diagnostico_falla(self):
        """Admitir sin diagnóstico → 400."""
        self.client.force_authenticate(user=self.user_medico)

        data = {
            'paciente': self.paciente_libre.id,
            'cama': self.cama_disponible.id,
        }

        response = self.client.post('/api/internacion/internaciones/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('diagnostico', str(response.data))

    def test_admitir_con_diagnostico_cie_exitoso(self):
        """Admitir con diagnóstico CIE-10 → 201."""
        from catalogos.models import DiagnosticoCIE10

        suffix = unique_suffix()
        diagnostico_cie = DiagnosticoCIE10.objects.create(
            codigo=f'A00.0-{suffix}',
            descripcion='Cólera debido a Vibrio cholerae 01, biotipo cholerae',
            categoria='Enfermedades infecciosas',
            capitulo='I',
            enfermedad='Cólera',
        )

        self.client.force_authenticate(user=self.user_medico)

        data = {
            'paciente': self.paciente_libre.id,
            'cama': self.cama_disponible.id,
            'diagnostico_cie_id': diagnostico_cie.id,
        }

        response = self.client.post('/api/internacion/internaciones/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        internacion = Internacion.objects.get(paciente=self.paciente_libre, activo=True)
        self.assertEqual(internacion.diagnostico_cie, diagnostico_cie)
