"""Tests API catálogo PanelExamen (NBU del perfil)."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from laboratorio.models import PanelExamen, TipoExamen, TipoMuestra

User = get_user_model()


class TestPanelExamenCatalogApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='lab_pan',
            password='testpass123',
            rol='laboratorio',
        )
        self.client.force_authenticate(user=self.user)
        self.muestra = TipoMuestra.objects.create(codigo='SANGRE_P', nombre='Sangre panel')
        self.na = TipoExamen.objects.create(
            codigo='NA_T',
            nombre='Sodio test',
            tipo_muestra_requerida=self.muestra,
        )
        self.k = TipoExamen.objects.create(
            codigo='K_T',
            nombre='Potasio test',
            tipo_muestra_requerida=self.muestra,
        )
        self.panel = PanelExamen.objects.create(codigo='PAN_IONO_T', nombre='Ionograma test')
        self.panel.tipos_examen.set([self.na, self.k])

    def test_patch_codigo_nbu_completa_ub(self):
        url = f'/api/lab/paneles/{self.panel.pk}/'
        r = self.client.patch(
            url,
            {'codigo_nbu': '660546'},
            format='json',
            HTTP_HOST='localhost',
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.panel.refresh_from_db()
        self.assertEqual(self.panel.codigo_nbu, '660546')
        self.assertEqual(self.panel.ub_nbu, Decimal('3.5'))
        self.assertEqual(r.data.get('codigo_nbu'), '660546')

    def test_patch_codigo_nbu_invalido(self):
        url = f'/api/lab/paneles/{self.panel.pk}/'
        r = self.client.patch(
            url,
            {'codigo_nbu': 'IONO'},
            format='json',
            HTTP_HOST='localhost',
        )
        self.assertEqual(r.status_code, 400, r.data)
