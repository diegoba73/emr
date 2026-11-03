"""QR papel: solo recepción puesto 1 o sala de extracción."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from pacientes.models import Paciente
from recepcion.models import PuestoRecepcion
from recepcion.services import CODIGO_PUESTO_1, CODIGO_SALA_EXTRACCION

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def paciente_kiosco():
    return Paciente.objects.create(
        nombre='Ana', apellido='Perez', dni='30111222', fecha_nacimiento='1990-01-01'
    )


@pytest.fixture
def puestos():
    p1, _ = PuestoRecepcion.objects.get_or_create(
        codigo=CODIGO_PUESTO_1,
        defaults={'nombre': 'Puesto 1', 'etiqueta_paciente': 'Puesto 1', 'activo': True, 'orden': 1},
    )
    lab, _ = PuestoRecepcion.objects.get_or_create(
        codigo=CODIGO_SALA_EXTRACCION,
        defaults={
            'nombre': 'Sala extracción',
            'etiqueta_paciente': 'Sala de extracción',
            'activo': True,
            'orden': 99,
        },
    )
    return p1, lab


def test_kiosco_sin_turno_va_a_puesto_1(paciente_kiosco, puestos):
    p1, _lab = puestos
    r = APIClient().post(
        '/api/recepcion/kiosco-checkin/',
        {'dni': '30111222', 'apellido': 'Perez', 'tipo_actividad': 'SIN_TURNO'},
        format='json',
    )
    assert r.status_code == 200, r.data
    assert r.data['tipo_actividad'] == 'SIN_TURNO'
    assert r.data['puesto'] == p1.label_publico
    assert (r.data.get('codigo_llamado') or '').startswith('S')


def test_kiosco_extraccion_va_a_sala_lab(paciente_kiosco, puestos):
    _p1, lab = puestos
    r = APIClient().post(
        '/api/recepcion/kiosco-checkin/',
        {'dni': '30111222', 'apellido': 'Perez', 'tipo_actividad': 'EXTRACCION'},
        format='json',
    )
    assert r.status_code == 200, r.data
    assert r.data['tipo_actividad'] == 'EXTRACCION'
    assert r.data['puesto'] == lab.label_publico
    assert (r.data.get('codigo_llamado') or '').startswith('L')


@pytest.mark.parametrize('motivo', ['CON_TURNO', 'ESTUDIO', 'PROCEDIMIENTO', 'CONSULTA'])
def test_kiosco_rechaza_motivos_de_turno(paciente_kiosco, puestos, motivo):
    r = APIClient().post(
        '/api/recepcion/kiosco-checkin/',
        {'dni': '30111222', 'apellido': 'Perez', 'tipo_actividad': motivo},
        format='json',
    )
    assert r.status_code == 400
    assert 'app' in str(r.data).lower() or 'recepción' in str(r.data).lower()
