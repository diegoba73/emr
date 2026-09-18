from datetime import timedelta

import pytest
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework.test import APIClient

from internacion.models import Cama, Internacion, Sector
from pacientes.models import Paciente
from usuarios.models import User


@pytest.fixture
def escenario(db):
    sector = Sector.objects.create(nombre='Sector histórico')
    cama = Cama.objects.create(nombre='Cama histórica', sector=sector)
    paciente = Paciente.objects.create(dni='RET-123', nombre='Prueba', apellido='Retiro')
    ingreso = Internacion.objects.create(cama=cama, paciente=paciente, diagnostico_ingreso='Prueba')
    user = User.objects.create_user(username='retiro-admin', password='x', rol='admin')
    client = APIClient()
    client.force_authenticate(user)
    return client, sector, cama, ingreso


@pytest.mark.django_db
def test_retirar_cama_ocupada_conserva_y_muestra_internacion(escenario):
    client, sector, cama, ingreso = escenario
    assert client.delete(f'/api/internacion/camas/{cama.pk}/').status_code == 204
    cama.refresh_from_db()
    ingreso.refresh_from_db()
    assert not cama.activo
    assert ingreso.activo and ingreso.cama_id == cama.pk
    response = client.get('/api/internacion/camas/')
    rows = response.data['results'] if isinstance(response.data, dict) else response.data
    assert cama.pk in {r['id'] for r in rows}
    ingreso.fecha_alta = timezone.now() + timedelta(minutes=1)
    ingreso.save()
    response = client.get('/api/internacion/camas/')
    rows = response.data['results'] if isinstance(response.data, dict) else response.data
    assert cama.pk not in {r['id'] for r in rows}
    assert Internacion.objects.filter(pk=ingreso.pk).exists()
    assert client.patch(f'/api/internacion/camas/{cama.pk}/', {'activo': True}, format='json').status_code == 200
    cama.refresh_from_db()
    assert cama.activo


@pytest.mark.django_db
def test_retirar_sector_conserva_camas_e_historial(escenario):
    client, sector, cama, ingreso = escenario
    assert client.delete(f'/api/internacion/sectores/{sector.pk}/').status_code == 204
    sector.refresh_from_db()
    cama.refresh_from_db()
    assert not sector.activo and not cama.activo
    assert Internacion.objects.filter(pk=ingreso.pk).exists()
    with pytest.raises(ProtectedError):
        cama.delete()
    with pytest.raises(ProtectedError):
        sector.delete()


@pytest.mark.django_db
@pytest.mark.parametrize('rol', ['medico', 'enfermeria', 'secretaria'])
def test_solo_admin_retira_o_recupera(escenario, rol):
    client, sector, cama, ingreso = escenario
    user = User.objects.create_user(username=rol, password='x', rol=rol)
    client.force_authenticate(user)
    assert client.delete(f'/api/internacion/camas/{cama.pk}/').status_code == 403
    assert client.patch(f'/api/internacion/camas/{cama.pk}/', {'activo': False}, format='json').status_code in (400, 403)
    cama.refresh_from_db()
    assert cama.activo


@pytest.mark.django_db
def test_no_admite_ni_traslada_a_cama_retirada(escenario):
    client, sector, cama, ingreso = escenario
    destino = Cama.objects.create(nombre='Retirada', sector=sector, activo=False)
    response = client.post(f'/api/internacion/internaciones/{ingreso.pk}/mover-cama/',
                           {'cama_id': destino.pk}, format='json')
    assert response.status_code == 400
    otro = Paciente.objects.create(dni='RET-OTRO', nombre='Otro', apellido='Paciente')
    response = client.post('/api/internacion/internaciones/', {
        'paciente': otro.pk, 'cama': destino.pk, 'diagnostico_ingreso': 'Prueba',
    }, format='json')
    assert response.status_code == 400
    assert not Internacion.objects.filter(paciente=otro).exists()


@pytest.mark.django_db
def test_paciente_sale_de_cama_retirada_sin_reemplazarlo(escenario):
    client, sector, cama, ingreso = escenario
    client.delete(f'/api/internacion/camas/{cama.pk}/')
    destino = Cama.objects.create(nombre='Destino ocupado', sector=sector)
    otro = Paciente.objects.create(dni='RET-SWAP', nombre='Otro', apellido='Paciente')
    otro_ingreso = Internacion.objects.create(cama=destino, paciente=otro)
    response = client.post(f'/api/internacion/internaciones/{ingreso.pk}/mover-cama/',
                           {'cama_id': destino.pk}, format='json')
    assert response.status_code == 400
    otro_ingreso.refresh_from_db()
    assert otro_ingreso.cama_id == destino.pk
    libre = Cama.objects.create(nombre='Destino disponible', sector=sector)
    response = client.post(f'/api/internacion/internaciones/{ingreso.pk}/mover-cama/',
                           {'cama_id': libre.pk}, format='json')
    assert response.status_code == 200
    ingreso.refresh_from_db()
    assert ingreso.cama_id == libre.pk
