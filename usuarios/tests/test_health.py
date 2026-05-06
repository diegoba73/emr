"""
Tests para el endpoint de health check.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse


class HealthCheckTestCase(TestCase):
    """
    Tests para verificar que el endpoint de health check funciona correctamente.
    """
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        self.health_url = '/api/health/'
    
    def test_health_check_returns_200(self):
        """
        Verifica que el endpoint /api/health/ responde con status 200.
        """
        response = self.client.get(self.health_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_health_check_response_structure(self):
        """
        Verifica que la respuesta del health check tiene la estructura correcta.
        """
        response = self.client.get(self.health_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar estructura de la respuesta
        self.assertIn('status', data)
        self.assertIn('service', data)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['service'], 'EMR-API')
    
    def test_health_check_no_authentication_required(self):
        """
        Verifica que el endpoint de health check no requiere autenticación.
        """
        # Hacer request sin autenticación
        response = self.client.get(self.health_url)
        
        # Debe responder 200 sin necesidad de autenticación
        self.assertEqual(response.status_code, 200)
    
    def test_health_check_allows_options(self):
        """
        Verifica que el endpoint permite requests OPTIONS (CORS preflight).
        """
        response = self.client.options(self.health_url)
        
        # OPTIONS debe responder 200
        self.assertEqual(response.status_code, 200)









