"""
Tests para la gestión de infraestructura (Sectores y Camas) del módulo de Internación.
"""
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from internacion.models import Sector, Cama
from internacion.tests.helpers import unique_suffix

User = get_user_model()


class InfraestructuraAPITestCase(APITestCase):
    """Tests para la API de infraestructura (Sectores y Camas)"""

    def setUp(self):
        suffix = unique_suffix()

        self.user_enfermeria = User.objects.create_user(
            username=f'enfermeria-inf-{suffix}',
            password='testpass123',
            email=f'enfermeria-inf-{suffix}@test.com',
            rol='enfermeria',
        )

        self.user_medico = User.objects.create_user(
            username=f'medico-inf-{suffix}',
            password='testpass123',
            email=f'medico-inf-{suffix}@test.com',
            rol='medico',
        )

        self.user_admin = User.objects.create_user(
            username=f'admin-inf-{suffix}',
            password='testpass123',
            email=f'admin-inf-{suffix}@test.com',
            rol='admin',
            is_staff=True,
            is_superuser=True,
        )

        self.user_paciente = User.objects.create_user(
            username=f'paciente-inf-{suffix}',
            password='testpass123',
            email=f'paciente-inf-{suffix}@test.com',
            rol='paciente',
        )

        self.sector_uco = Sector.objects.create(nombre=f'UCO-inf-{suffix}')
        self.sector_uce = Sector.objects.create(nombre=f'UCE-inf-{suffix}')

        self.cama_disponible = Cama.objects.create(
            nombre=f'Cama-disp-inf-{suffix}',
            sector=self.sector_uco,
            estado='DISPONIBLE',
            aislada=False,
        )

        self.cama_ocupada = Cama.objects.create(
            nombre=f'Cama-ocup-inf-{suffix}',
            sector=self.sector_uco,
            estado='OCUPADA',
            aislada=False,
        )

    def _cama_payload(self, nombre: str, sector, **extra):
        return {
            'nombre': nombre,
            'sector_id': sector.id,
            'estado': extra.get('estado', 'DISPONIBLE'),
            'aislada': extra.get('aislada', False),
        }

    def test_enfermeria_puede_crear_cama(self):
        """Usuario enfermería puede crear cama (201)."""
        self.client.force_authenticate(user=self.user_enfermeria)
        nombre = f'Cama-enf-{unique_suffix()}'
        before = Cama.objects.count()

        response = self.client.post(
            '/api/internacion/camas/',
            self._cama_payload(nombre, self.sector_uco),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cama.objects.count(), before + 1)
        self.assertEqual(Cama.objects.get(nombre=nombre).sector, self.sector_uco)

    def test_paciente_no_puede_crear_cama(self):
        """Usuario paciente no puede crear cama (403)."""
        self.client.force_authenticate(user=self.user_paciente)
        before = Cama.objects.count()

        response = self.client.post(
            '/api/internacion/camas/',
            self._cama_payload(f'Cama-pac-{unique_suffix()}', self.sector_uco),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Cama.objects.count(), before)

    def test_medico_puede_crear_cama(self):
        """Médico puede crear cama (201)."""
        self.client.force_authenticate(user=self.user_medico)
        nombre = f'Cama-med-{unique_suffix()}'

        response = self.client.post(
            '/api/internacion/camas/',
            self._cama_payload(nombre, self.sector_uce, aislada=True),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cama_creada = Cama.objects.get(nombre=nombre)
        self.assertEqual(cama_creada.sector, self.sector_uce)
        self.assertTrue(cama_creada.aislada)

    def test_admin_puede_crear_cama(self):
        """Admin puede crear cama (201)."""
        self.client.force_authenticate(user=self.user_admin)

        response = self.client.post(
            '/api/internacion/camas/',
            self._cama_payload(f'Cama-adm-{unique_suffix()}', self.sector_uco),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_eliminar_cama_ocupada_falla(self):
        """No se puede eliminar cama ocupada (400)."""
        self.client.force_authenticate(user=self.user_admin)

        response = self.client.delete(f'/api/internacion/camas/{self.cama_ocupada.id}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertIn('No se puede eliminar una cama activa/ocupada', str(response.data['estado']))
        self.assertTrue(Cama.objects.filter(id=self.cama_ocupada.id).exists())

    def test_eliminar_cama_disponible_exitoso(self):
        """Eliminar cama disponible es exitoso (204)."""
        self.client.force_authenticate(user=self.user_admin)

        response = self.client.delete(f'/api/internacion/camas/{self.cama_disponible.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cama.objects.filter(id=self.cama_disponible.id).exists())

    def test_enfermeria_puede_crear_sector(self):
        """Enfermería puede crear sector (201)."""
        self.client.force_authenticate(user=self.user_enfermeria)
        nombre = f'Sector-{unique_suffix()}'
        before = Sector.objects.count()

        response = self.client.post('/api/internacion/sectores/', {'nombre': nombre}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Sector.objects.count(), before + 1)
        self.assertTrue(Sector.objects.filter(nombre=nombre).exists())

    def test_paciente_no_puede_crear_sector(self):
        """Paciente no puede crear sector (403)."""
        self.client.force_authenticate(user=self.user_paciente)
        before = Sector.objects.count()

        response = self.client.post(
            '/api/internacion/sectores/',
            {'nombre': f'Sector-pac-{unique_suffix()}'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Sector.objects.count(), before)

    def test_eliminar_cama_en_limpieza_falla(self):
        """Eliminar cama en limpieza falla (400)."""
        cama_limpieza = Cama.objects.create(
            nombre=f'Cama-limp-{unique_suffix()}',
            sector=self.sector_uco,
            estado='LIMPIEZA',
            aislada=False,
        )

        self.client.force_authenticate(user=self.user_admin)

        response = self.client.delete(f'/api/internacion/camas/{cama_limpieza.id}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)

    def test_eliminar_cama_en_mantenimiento_falla(self):
        """Eliminar cama en mantenimiento falla (400)."""
        cama_mantenimiento = Cama.objects.create(
            nombre=f'Cama-mant-{unique_suffix()}',
            sector=self.sector_uco,
            estado='MANTENIMIENTO',
            aislada=False,
        )

        self.client.force_authenticate(user=self.user_admin)

        response = self.client.delete(f'/api/internacion/camas/{cama_mantenimiento.id}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)

    def test_editar_cama_disponible(self):
        """Admin puede editar nombre, sector y aislada de cama disponible."""
        self.client.force_authenticate(user=self.user_admin)
        nuevo_nombre = f'Cama-edit-{unique_suffix()}'

        response = self.client.patch(
            f'/api/internacion/camas/{self.cama_disponible.id}/',
            {
                'nombre': nuevo_nombre,
                'sector_id': self.sector_uce.id,
                'aislada': True,
                'estado': 'LIMPIEZA',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cama_disponible.refresh_from_db()
        self.assertEqual(self.cama_disponible.nombre, nuevo_nombre)
        self.assertEqual(self.cama_disponible.sector, self.sector_uce)
        self.assertTrue(self.cama_disponible.aislada)
        self.assertEqual(self.cama_disponible.estado, 'LIMPIEZA')

    def test_editar_cama_ocupada_solo_nombre_y_aislada(self):
        """En cama ocupada solo se permite editar nombre y aislada."""
        self.client.force_authenticate(user=self.user_admin)
        nuevo_nombre = f'Cama-ocup-edit-{unique_suffix()}'

        response = self.client.patch(
            f'/api/internacion/camas/{self.cama_ocupada.id}/',
            {'nombre': nuevo_nombre, 'aislada': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cama_ocupada.refresh_from_db()
        self.assertEqual(self.cama_ocupada.nombre, nuevo_nombre)
        self.assertTrue(self.cama_ocupada.aislada)

    def test_editar_cama_ocupada_sector_falla(self):
        """No se puede cambiar sector en cama ocupada."""
        self.client.force_authenticate(user=self.user_admin)

        response = self.client.patch(
            f'/api/internacion/camas/{self.cama_ocupada.id}/',
            {'sector_id': self.sector_uce.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_enfermeria_puede_editar_cama(self):
        """Enfermería puede editar cama disponible."""
        self.client.force_authenticate(user=self.user_enfermeria)
        nuevo_nombre = f'Cama-enf-edit-{unique_suffix()}'

        response = self.client.patch(
            f'/api/internacion/camas/{self.cama_disponible.id}/',
            {'nombre': nuevo_nombre},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cama_disponible.refresh_from_db()
        self.assertEqual(self.cama_disponible.nombre, nuevo_nombre)
