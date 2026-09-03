"""Tests para tipos de dieta en internación."""
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from internacion.models import Sector, Cama, Internacion, TipoDieta
from internacion.management.commands.poblar_tipos_dieta import TIPOS_DIETA
from internacion.tests.helpers import unique_suffix
from pacientes.models import Paciente

User = get_user_model()


def _list_payload(response):
    data = response.data
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


class TiposDietaAPITestCase(APITestCase):
    def setUp(self):
        suffix = unique_suffix()

        self.user_medico = User.objects.create_user(
            username=f'medico-dieta-{suffix}',
            password='testpass123',
            email=f'medico-dieta-{suffix}@test.com',
            rol='medico',
        )
        self.user_secretaria = User.objects.create_user(
            username=f'sec-dieta-{suffix}',
            password='testpass123',
            email=f'sec-dieta-{suffix}@test.com',
            rol='secretaria',
        )

        self.sector = Sector.objects.create(nombre=f'UCO-dieta-{suffix}')
        self.cama_disponible = Cama.objects.create(
            nombre=f'Cama-disp-dieta-{suffix}',
            sector=self.sector,
            estado='DISPONIBLE',
        )
        self.cama_ocupada = Cama.objects.create(
            nombre=f'Cama-ocup-dieta-{suffix}',
            sector=self.sector,
            estado='DISPONIBLE',
        )
        self.paciente_libre = Paciente.objects.create(
            nombre='Luis',
            apellido='Dieta',
            dni=f'11111111-{suffix}',
            fecha_nacimiento='1990-01-01',
            sexo='M',
            telefono='1234567890',
            email=f'luis-dieta-{suffix}@test.com',
        )
        self.paciente_internado = Paciente.objects.create(
            nombre='Ana',
            apellido='Dieta',
            dni=f'22222222-{suffix}',
            fecha_nacimiento='1988-02-02',
            sexo='F',
            telefono='0987654321',
            email=f'ana-dieta-{suffix}@test.com',
        )
        self.tipo_hiposodica = TipoDieta.objects.create(
            nombre=f'Hiposódica-{suffix}',
            descripcion='Para hipertensión / restricción de sodio',
            activo=True,
        )
        self.tipo_diabetica = TipoDieta.objects.create(
            nombre=f'Diabética-{suffix}',
            activo=True,
        )
        self.tipo_inactiva = TipoDieta.objects.create(
            nombre=f'Obsoleta-{suffix}',
            activo=False,
        )
        self.internacion_activa = Internacion.objects.create(
            paciente=self.paciente_internado,
            cama=self.cama_ocupada,
            diagnostico_ingreso='Diagnóstico de prueba',
            tipo_dieta=self.tipo_hiposodica,
            activo=True,
        )
        self.cama_ocupada.refresh_from_db()

    def test_admitir_con_tipo_dieta(self):
        self.client.force_authenticate(user=self.user_medico)
        response = self.client.post(
            '/api/internacion/internaciones/',
            {
                'paciente': self.paciente_libre.id,
                'cama': self.cama_disponible.id,
                'diagnostico_ingreso': 'Ingreso con dieta',
                'tipo_dieta_id': self.tipo_diabetica.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        internacion = Internacion.objects.get(paciente=self.paciente_libre, activo=True)
        self.assertEqual(internacion.tipo_dieta_id, self.tipo_diabetica.id)
        self.assertEqual(response.data['tipo_dieta']['id'], self.tipo_diabetica.id)

    def test_admitir_sin_tipo_dieta_sigue_opcional(self):
        self.client.force_authenticate(user=self.user_medico)
        response = self.client.post(
            '/api/internacion/internaciones/',
            {
                'paciente': self.paciente_libre.id,
                'cama': self.cama_disponible.id,
                'diagnostico_ingreso': 'Ingreso sin dieta',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        internacion = Internacion.objects.get(paciente=self.paciente_libre, activo=True)
        self.assertIsNone(internacion.tipo_dieta)

    def test_patch_cambia_tipo_dieta(self):
        self.client.force_authenticate(user=self.user_medico)
        response = self.client.patch(
            f'/api/internacion/internaciones/{self.internacion_activa.id}/',
            {'tipo_dieta_id': self.tipo_diabetica.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.internacion_activa.refresh_from_db()
        self.assertEqual(self.internacion_activa.tipo_dieta_id, self.tipo_diabetica.id)
        self.assertEqual(response.data['tipo_dieta']['nombre'], self.tipo_diabetica.nombre)

    def test_internacion_actual_incluye_nombre_dieta(self):
        self.client.force_authenticate(user=self.user_medico)
        response = self.client.get(f'/api/internacion/camas/{self.cama_ocupada.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual = response.data.get('internacion_actual') or {}
        self.assertEqual(actual.get('tipo_dieta'), self.tipo_hiposodica.nombre)

    def test_listado_default_omite_inactivos(self):
        self.client.force_authenticate(user=self.user_medico)
        response = self.client.get('/api/internacion/tipos-dieta/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        nombres = {item['nombre'] for item in _list_payload(response)}
        self.assertIn(self.tipo_hiposodica.nombre, nombres)
        self.assertNotIn(self.tipo_inactiva.nombre, nombres)

    def test_listado_todos_incluye_inactivos(self):
        self.client.force_authenticate(user=self.user_medico)
        response = self.client.get('/api/internacion/tipos-dieta/?todos=1&page_size=100')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nombres = {item['nombre'] for item in _list_payload(response)}
        self.assertIn(self.tipo_inactiva.nombre, nombres)

    def test_crud_tipo_dieta(self):
        self.client.force_authenticate(user=self.user_medico)
        nombre = f'Hepática-{unique_suffix()}'
        created = self.client.post(
            '/api/internacion/tipos-dieta/',
            {'nombre': nombre, 'descripcion': 'Hepática'},
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        tipo_id = created.data['id']

        patched = self.client.patch(
            f'/api/internacion/tipos-dieta/{tipo_id}/',
            {'activo': False},
            format='json',
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertFalse(patched.data['activo'])

        listed = self.client.get('/api/internacion/tipos-dieta/?page_size=100')
        nombres = {item['nombre'] for item in _list_payload(listed)}
        self.assertNotIn(nombre, nombres)

        deleted = self.client.delete(f'/api/internacion/tipos-dieta/{tipo_id}/')
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TipoDieta.objects.filter(id=tipo_id).exists())

    def test_secretaria_no_puede_crear_tipo_dieta(self):
        self.client.force_authenticate(user=self.user_secretaria)
        response = self.client.post(
            '/api/internacion/tipos-dieta/',
            {'nombre': f'Sec-{unique_suffix()}'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poblar_tipos_dieta_es_idempotente(self):
        call_command('poblar_tipos_dieta')
        call_command('poblar_tipos_dieta')
        nombres = {nombre for nombre, _ in TIPOS_DIETA}
        self.assertEqual(
            TipoDieta.objects.filter(nombre__in=nombres).count(),
            len(nombres),
        )
