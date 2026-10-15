"""Edición de médicos: especialidad, email y teléfono desde el ABM."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from medicos.models import Especialidad, Medico

User = get_user_model()


@pytest.mark.django_db
class TestMedicoEdicionAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username=f'admin_med_edit_{self.suf}',
            password='x',
            rol='admin',
            is_staff=True,
        )
        self.esp = Especialidad.objects.create(nombre=f'Esp Edit {self.suf}')
        self.medico = Medico.objects.create(
            nombre='Ana',
            apellido='Prueba',
            matricula=f'ME{self.suf}',
            especialidad=self.esp,
        )
        self.client.force_authenticate(user=self.admin)

    def test_list_incluye_especialidad_id_y_contacto(self):
        r = self.client.get('/api/medicos/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        rows = r.data['results'] if isinstance(r.data, dict) and 'results' in r.data else r.data
        row = next(m for m in rows if m['id'] == self.medico.id)
        self.assertEqual(row.get('especialidad_id'), self.esp.id)
        self.assertEqual(row.get('especialidad_nombre'), self.esp.nombre)
        self.assertIn('email', row)
        self.assertIn('telefono', row)

    def test_patch_actualiza_especialidad_email_telefono(self):
        otra = Especialidad.objects.create(nombre=f'Esp2 {self.suf}')
        r = self.client.patch(
            f'/api/medicos/{self.medico.id}/',
            {
                'nombre': 'Ana María',
                'apellido': 'Prueba',
                'matricula': self.medico.matricula,
                'especialidad_id': otra.id,
                'email': 'ana@example.com',
                'telefono': '2991112222',
                'ambito_atencion': 'AMBULATORIO',
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.medico.refresh_from_db()
        self.assertEqual(self.medico.nombre, 'Ana María')
        self.assertEqual(self.medico.especialidad_id, otra.id)
        self.assertEqual(self.medico.email, 'ana@example.com')
        self.assertEqual(self.medico.telefono, '2991112222')
        self.assertEqual(self.medico.ambito_atencion, 'AMBULATORIO')
        self.assertEqual(r.data.get('email'), 'ana@example.com')
        self.assertEqual(r.data.get('especialidad', {}).get('id'), otra.id)

    def test_patch_null_limpia_especialidad(self):
        r = self.client.patch(
            f'/api/medicos/{self.medico.id}/',
            {'especialidad_id': None},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.medico.refresh_from_db()
        self.assertIsNone(self.medico.especialidad_id)
