"""
Tests para el proceso de admisión (ingreso) de pacientes al módulo de Internación.
"""
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from internacion.models import Sector, Cama, Internacion
from pacientes.models import Paciente

User = get_user_model()


class AdmisionAPITestCase(APITestCase):
    """Tests para el proceso de admisión de pacientes"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear usuario con permisos
        self.user_medico = User.objects.create_user(
            username='medico1',
            password='testpass123',
            email='medico@test.com',
            rol='medico'
        )
        
        # Crear sectores
        self.sector_uco = Sector.objects.create(nombre='UCO')
        self.sector_uce = Sector.objects.create(nombre='UCE')
        
        # Crear camas
        self.cama_disponible = Cama.objects.create(
            nombre='Cama 101',
            sector=self.sector_uco,
            estado='DISPONIBLE',
            aislada=False
        )
        
        self.cama_ocupada = Cama.objects.create(
            nombre='Cama 102',
            sector=self.sector_uco,
            estado='OCUPADA',
            aislada=False
        )
        
        # Crear pacientes
        self.paciente_libre = Paciente.objects.create(
            nombre='Juan',
            apellido='Pérez',
            dni='12345678',
            fecha_nacimiento='1990-01-01',
            sexo='M',
            telefono='1234567890',
            email='juan@test.com'
        )
        
        self.paciente_internado = Paciente.objects.create(
            nombre='María',
            apellido='González',
            dni='87654321',
            fecha_nacimiento='1985-05-15',
            sexo='F',
            telefono='0987654321',
            email='maria@test.com'
        )
        
        # Crear internación activa para paciente_internado
        self.internacion_activa = Internacion.objects.create(
            paciente=self.paciente_internado,
            cama=self.cama_ocupada,
            diagnostico_ingreso='Diagnóstico de prueba',
            activo=True
        )
    
    def test_admitir_paciente_libre_en_cama_disponible(self):
        """
        Test Happy Path: Admitir paciente libre en cama disponible -> Status 201, Cama pasa a 'OCUPADA'
        """
        self.client.force_authenticate(user=self.user_medico)
        
        data = {
            'paciente': self.paciente_libre.id,
            'cama': self.cama_disponible.id,
            'diagnostico_ingreso': 'Paciente con diagnóstico de prueba'
        }
        
        response = self.client.post('/api/internacion/internaciones/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar que la internación se creó
        internacion = Internacion.objects.get(paciente=self.paciente_libre, activo=True)
        self.assertIsNotNone(internacion)
        self.assertEqual(internacion.cama, self.cama_disponible)
        
        # Verificar que la cama cambió a OCUPADA
        self.cama_disponible.refresh_from_db()
        self.assertEqual(self.cama_disponible.estado, 'OCUPADA')
    
    def test_admitir_en_cama_ocupada_falla(self):
        """
        Test Cama Ocupada: Intentar admitir en cama ocupada -> Status 400
        """
        self.client.force_authenticate(user=self.user_medico)
        
        data = {
            'paciente': self.paciente_libre.id,
            'cama': self.cama_ocupada.id,
            'diagnostico_ingreso': 'Intento de ingreso en cama ocupada'
        }
        
        response = self.client.post('/api/internacion/internaciones/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cama', response.data)
        self.assertIn('no está disponible', str(response.data['cama']))
        
        # Verificar que NO se creó la internación
        self.assertFalse(
            Internacion.objects.filter(
                paciente=self.paciente_libre,
                cama=self.cama_ocupada,
                activo=True
            ).exists()
        )
    
    def test_admitir_paciente_ya_internado_falla(self):
        """
        Test Doble Internación: Intentar admitir paciente que ya está internado -> Status 400
        """
        self.client.force_authenticate(user=self.user_medico)
        
        # Crear otra cama disponible
        cama_nueva = Cama.objects.create(
            nombre='Cama 103',
            sector=self.sector_uce,
            estado='DISPONIBLE',
            aislada=False
        )
        
        data = {
            'paciente': self.paciente_internado.id,  # Paciente que ya está internado
            'cama': cama_nueva.id,
            'diagnostico_ingreso': 'Intento de doble internación'
        }
        
        response = self.client.post('/api/internacion/internaciones/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('paciente', response.data)
        self.assertIn('ya está internado', str(response.data['paciente']))
        
        # Verificar que NO se creó una segunda internación
        internaciones_activas = Internacion.objects.filter(
            paciente=self.paciente_internado,
            activo=True
        )
        self.assertEqual(internaciones_activas.count(), 1)
        self.assertEqual(internaciones_activas.first().cama, self.cama_ocupada)
    
    def test_admitir_sin_diagnostico_falla(self):
        """Test adicional: Admitir sin diagnóstico falla"""
        self.client.force_authenticate(user=self.user_medico)
        
        data = {
            'paciente': self.paciente_libre.id,
            'cama': self.cama_disponible.id,
            # Sin diagnóstico
        }
        
        response = self.client.post('/api/internacion/internaciones/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('diagnostico', str(response.data))
    
    def test_admitir_con_diagnostico_cie_exitoso(self):
        """Test adicional: Admitir con diagnóstico CIE-10 es exitoso"""
        from catalogos.models import DiagnosticoCIE10
        
        diagnostico_cie = DiagnosticoCIE10.objects.create(
            codigo='A00.0',
            descripcion='Cólera debido a Vibrio cholerae 01, biotipo cholerae',
            categoria='Enfermedades infecciosas',
            capitulo='I',
            enfermedad='Cólera'
        )
        
        self.client.force_authenticate(user=self.user_medico)
        
        data = {
            'paciente': self.paciente_libre.id,
            'cama': self.cama_disponible.id,
            'diagnostico_cie_id': diagnostico_cie.id
        }
        
        response = self.client.post('/api/internacion/internaciones/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        internacion = Internacion.objects.get(paciente=self.paciente_libre, activo=True)
        self.assertEqual(internacion.diagnostico_cie, diagnostico_cie)



























