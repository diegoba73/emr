"""Tests API catálogo TipoExamen (PATCH tolerante a null en campos texto)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from laboratorio.models import TipoExamen, TipoMuestra

User = get_user_model()


class TestTipoExamenCatalogApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='lab_cat',
            password='testpass123',
            rol='laboratorio',
        )
        self.client.force_authenticate(user=self.user)
        self.muestra = TipoMuestra.objects.create(codigo='SANGRE_T', nombre='Sangre test')
        self.examen = TipoExamen.objects.create(
            codigo='GLU_T',
            nombre='Glucosa test',
            tipo_muestra_requerida=self.muestra,
            metodo='',
            unidad_default='',
            modo_entrada='TICKET_ENTERO',
            ticket_decimales=1,
            multiplicador_clinico=1000,
            formato_informe_entrada='absolute_int',
        )

    def test_patch_acepta_null_en_metodo_y_unidad(self):
        url = f'/api/lab/examenes/{self.examen.pk}/'
        r = self.client.patch(
            url,
            {
                'nombre': 'Glucosa test',
                'metodo': None,
                'unidad_default': None,
            },
            format='json',
            HTTP_HOST='localhost',
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.examen.refresh_from_db()
        self.assertEqual(self.examen.metodo, '')
        self.assertEqual(self.examen.unidad_default, '')

    def test_patch_multiplicador_vacio_usa_default(self):
        url = f'/api/lab/examenes/{self.examen.pk}/'
        r = self.client.patch(
            url,
            {'multiplicador_clinico': ''},
            format='json',
            HTTP_HOST='localhost',
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.examen.refresh_from_db()
        self.assertEqual(self.examen.multiplicador_clinico, 1)

    def test_codigo_no_editable_en_patch(self):
        url = f'/api/lab/examenes/{self.examen.pk}/'
        r = self.client.patch(
            url,
            {'codigo': 'OTRO'},
            format='json',
            HTTP_HOST='localhost',
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.examen.refresh_from_db()
        self.assertEqual(self.examen.codigo, 'GLU_T')
