"""CRUD web de paquetes lab móvil."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from laboratorio.models import PanelExamen, TipoExamen, TipoMuestra
from movil.models import PaqueteLabContexto

pytestmark = pytest.mark.django_db
User = get_user_model()


def _client(rol='admin'):
    user = User.objects.create_user(username=f'u-{rol}', password='test-password', rol=rol)
    if rol == 'admin':
        user.is_staff = True
        user.save(update_fields=['is_staff'])
    c = APIClient()
    assert c.login(username=user.username, password='test-password')
    return c


def test_admin_crea_paquete_movil_desde_api_web():
    tm = TipoMuestra.objects.create(codigo='SUE-P', nombre='Suero', activo=True)
    te = TipoExamen.objects.create(codigo='GLU-P', nombre='Glucemia', tipo_muestra_requerida=tm, activo=True)
    panel = PanelExamen.objects.create(codigo='PAN-P', nombre='Básico', activo=True)
    panel.tipos_examen.add(te)

    c = _client('admin')
    r = c.post(
        '/api/lab/paquetes-movil/',
        {
            'codigo': 'GUARDIA-BAS',
            'nombre': 'Guardia básico',
            'contexto': 'GUARDIA',
            'descripcion': 'Pedido típico de guardia',
            'paneles_ids': [panel.id],
            'examenes_ids': [te.id],
            'activo': True,
            'orden': 1,
        },
        format='json',
    )
    assert r.status_code == 201, r.data
    assert PaqueteLabContexto.objects.filter(codigo='GUARDIA-BAS').exists()
    listed = c.get('/api/lab/paquetes-movil/')
    assert listed.status_code == 200
    assert any(row['codigo'] == 'GUARDIA-BAS' for row in listed.data['results'])


def test_medico_no_puede_crear_paquete_web():
    c = _client('medico')
    r = c.post(
        '/api/lab/paquetes-movil/',
        {
            'codigo': 'X',
            'nombre': 'X',
            'contexto': 'GUARDIA',
            'paneles_ids': [],
            'examenes_ids': [],
        },
        format='json',
    )
    assert r.status_code == 403
