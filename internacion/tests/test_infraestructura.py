"""
Tests para la gestión de infraestructura (Sectores y Camas) del módulo de Internación.
"""
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from internacion.models import Sector, Cama

User = get_user_model()


class InfraestructuraAPITestCase(APITestCase):
    """Tests para la API de infraestructura (Sectores y Camas)"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear usuarios con diferentes roles
        self.user_enfermeria = User.objects.create_user(
            username='enfermeria1',
            password='testpass123',
            email='enfermeria@test.com',
            rol='enfermeria'
        )
        
        self.user_medico = User.objects.create_user(
            username='medico1',
            password='testpass123',
            email='medico@test.com',
            rol='medico'
        )
        
        self.user_admin = User.objects.create_user(
            username='admin1',
            password='testpass123',
            email='admin@test.com',
            rol='admin',
            is_staff=True,
            is_superuser=True
        )
        
        self.user_paciente = User.objects.create_user(
            username='paciente1',
            password='testpass123',
            email='paciente@test.com',
            rol='paciente'
        )
        
        # Crear un sector de prueba
        self.sector_uco = Sector.objects.create(nombre='UCO')
        self.sector_uce = Sector.objects.create(nombre='UCE')
        
        # Crear una cama de prueba
        self.cama_disponible = Cama.objects.create(
            nombre='Cama 1',
            sector=self.sector_uco,
            estado='DISPONIBLE',
            aislada=False
        )
        
        self.cama_ocupada = Cama.objects.create(
            nombre='Cama 2',
            sector=self.sector_uco,
            estado='OCUPADA',
            aislada=False
        )
    
    def test_enfermeria_puede_crear_cama(self):
        """
        Test 1: Usuario con rol 'enfermeria' PUEDE crear una Cama (Status 201)
        """
        self.client.force_authenticate(user=self.user_enfermeria)
        
        data = {
            'nombre': 'Cama Test Enfermeria',
            'sector': self.sector_uco.id,
            'estado': 'DISPONIBLE',
            'aislada': False
        }
        
        response = self.client.post('/api/internacion/camas/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cama.objects.count(), 3)  # 2 iniciales + 1 nueva
        self.assertEqual(Cama.objects.get(nombre='Cama Test Enfermeria').sector, self.sector_uco)
    
    def test_paciente_no_puede_crear_cama(self):
        """
        Test 2: Usuario con rol 'paciente' NO PUEDE crear una Cama (Status 403)
        """
        self.client.force_authenticate(user=self.user_paciente)
        
        data = {
            'nombre': 'Cama Test Paciente',
            'sector': self.sector_uco.id,
            'estado': 'DISPONIBLE',
            'aislada': False
        }
        
        response = self.client.post('/api/internacion/camas/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Cama.objects.count(), 2)  # No se creó ninguna cama
    
    def test_medico_puede_crear_cama(self):
        """Test adicional: Médico puede crear cama"""
        self.client.force_authenticate(user=self.user_medico)
        
        data = {
            'nombre': 'Cama Test Medico',
            'sector': self.sector_uce.id,
            'estado': 'DISPONIBLE',
            'aislada': True
        }
        
        response = self.client.post('/api/internacion/camas/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cama_creada = Cama.objects.get(nombre='Cama Test Medico')
        self.assertEqual(cama_creada.sector, self.sector_uce)
        self.assertTrue(cama_creada.aislada)
    
    def test_admin_puede_crear_cama(self):
        """Test adicional: Admin puede crear cama"""
        self.client.force_authenticate(user=self.user_admin)
        
        data = {
            'nombre': 'Cama Test Admin',
            'sector': self.sector_uco.id,
            'estado': 'DISPONIBLE',
            'aislada': False
        }
        
        response = self.client.post('/api/internacion/camas/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_eliminar_cama_ocupada_falla(self):
        """
        Test 3: Intento de borrar cama ocupada falla (Status 400)
        """
        self.client.force_authenticate(user=self.user_admin)
        
        # Intentar eliminar cama ocupada
        response = self.client.delete(f'/api/internacion/camas/{self.cama_ocupada.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertIn('No se puede eliminar una cama activa/ocupada', str(response.data['estado']))
        # Verificar que la cama no fue eliminada
        self.assertTrue(Cama.objects.filter(id=self.cama_ocupada.id).exists())
    
    def test_eliminar_cama_disponible_exitoso(self):
        """Test adicional: Eliminar cama disponible es exitoso"""
        self.client.force_authenticate(user=self.user_admin)
        
        # Eliminar cama disponible
        response = self.client.delete(f'/api/internacion/camas/{self.cama_disponible.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verificar que la cama fue eliminada
        self.assertFalse(Cama.objects.filter(id=self.cama_disponible.id).exists())
    
    def test_enfermeria_puede_crear_sector(self):
        """Test adicional: Enfermería puede crear sector"""
        self.client.force_authenticate(user=self.user_enfermeria)
        
        data = {
            'nombre': 'Sector Test'
        }
        
        response = self.client.post('/api/internacion/sectores/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Sector.objects.count(), 3)  # 2 iniciales + 1 nuevo
        self.assertTrue(Sector.objects.filter(nombre='Sector Test').exists())
    
    def test_paciente_no_puede_crear_sector(self):
        """Test adicional: Paciente no puede crear sector"""
        self.client.force_authenticate(user=self.user_paciente)
        
        data = {
            'nombre': 'Sector Test Paciente'
        }
        
        response = self.client.post('/api/internacion/sectores/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Sector.objects.count(), 2)  # No se creó ningún sector
    
    def test_eliminar_cama_en_limpieza_falla(self):
        """Test adicional: Eliminar cama en limpieza falla"""
        cama_limpieza = Cama.objects.create(
            nombre='Cama Limpieza',
            sector=self.sector_uco,
            estado='LIMPIEZA',
            aislada=False
        )
        
        self.client.force_authenticate(user=self.user_admin)
        
        response = self.client.delete(f'/api/internacion/camas/{cama_limpieza.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
    
    def test_eliminar_cama_en_mantenimiento_falla(self):
        """Test adicional: Eliminar cama en mantenimiento falla"""
        cama_mantenimiento = Cama.objects.create(
            nombre='Cama Mantenimiento',
            sector=self.sector_uco,
            estado='MANTENIMIENTO',
            aislada=False
        )
        
        self.client.force_authenticate(user=self.user_admin)
        
        response = self.client.delete(f'/api/internacion/camas/{cama_mantenimiento.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)



























