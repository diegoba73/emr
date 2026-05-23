"""C6.2 — Seguridad y auditoría de ArchivoMedico API."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from archivos_medicos.models import ArchivoMedico
from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from medicos.models import Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, Turno
from usuarios.models import User


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def paciente(db):
    u = User.objects.create_user(username=f'pac_{_uid()}', password='x', rol='paciente')
    return Paciente.objects.create(
        user=u, dni=f'DNI{_uid()}', nombre='Ana', apellido='Test',
    )


@pytest.fixture
def otro_paciente(db):
    u = User.objects.create_user(username=f'pac2_{_uid()}', password='x', rol='paciente')
    return Paciente.objects.create(
        user=u, dni=f'DNI2{_uid()}', nombre='Otro', apellido='Pac',
    )


@pytest.fixture
def medico(db):
    u = User.objects.create_user(username=f'med_{_uid()}', password='x', rol='medico')
    return Medico.objects.create(
        user=u, matricula=f'M{_uid()}', nombre='Dr', apellido='Test',
    )


@pytest.fixture
def medico_ajeno(db):
    u = User.objects.create_user(username=f'med2_{_uid()}', password='x', rol='medico')
    return Medico.objects.create(
        user=u, matricula=f'M2{_uid()}', nombre='Dr', apellido='Ajeno',
    )


@pytest.fixture
def recurso(db):
    return Recurso.objects.create(
        nombre=f'Cons {_uid()}',
        ubicacion='CEHTA',
        tipo_recurso='CONSULTORIO',
        activo=True,
    )


@pytest.fixture
def archivo_medico(paciente, medico):
    content = SimpleUploadedFile('estudio.pdf', b'%PDF-1.4 test', content_type='application/pdf')
    return ArchivoMedico.objects.create(
        paciente=paciente,
        titulo='Estudio',
        tipo_archivo='PDF',
        archivo=content,
    )


@pytest.fixture
def atencion_vinculada(paciente, medico, recurso):
    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio=timezone.now(),
        fecha_hora_fin=timezone.now() + timedelta(minutes=30),
        estado='CONFIRMADO',
    )
    return Atencion.objects.create(
        turno=turno,
        paciente=paciente,
        medico_principal=medico,
        tipo_atencion='CONSULTORIO',
        tipo_intervencion='CONSULTA',
        estado_clinico='ABIERTA',
    )


@pytest.mark.django_db
def test_list_no_expone_media_url(client, archivo_medico, medico, atencion_vinculada):
    client.force_authenticate(user=medico.user)
    r = client.get('/api/archivos-medicos/archivos/')
    assert r.status_code == 200
    items = r.data.get('results', r.data)
    assert len(items) >= 1
    row = next(i for i in items if i['id'] == archivo_medico.id)
    assert '/media/' not in str(row)
    assert 'download_url' in row
    assert '/download/' in row['download_url']


@pytest.mark.django_db
def test_medico_atencion_moderna_puede_listar(
    client, archivo_medico, medico, atencion_vinculada,
):
    assert atencion_vinculada.paciente_id == archivo_medico.paciente_id
    client.force_authenticate(user=medico.user)
    r = client.get('/api/archivos-medicos/archivos/')
    assert r.status_code == 200
    ids = [i['id'] for i in r.data.get('results', r.data)]
    assert archivo_medico.id in ids


@pytest.mark.django_db
def test_medico_ajeno_no_descarga(client, archivo_medico, medico_ajeno):
    client.force_authenticate(user=medico_ajeno.user)
    r = client.get(f'/api/archivos-medicos/archivos/{archivo_medico.id}/download/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_paciente_propio_descarga(client, archivo_medico, paciente):
    client.force_authenticate(user=paciente.user)
    r = client.get(f'/api/archivos-medicos/archivos/{archivo_medico.id}/download/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_paciente_otro_no_descarga(client, archivo_medico, otro_paciente):
    client.force_authenticate(user=otro_paciente.user)
    r = client.get(f'/api/archivos-medicos/archivos/{archivo_medico.id}/download/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_laboratorio_no_lista(client, archivo_medico):
    lab = User.objects.create_user(username=f'lab_{_uid()}', password='x', rol='laboratorio')
    client.force_authenticate(user=lab)
    r = client.get('/api/archivos-medicos/archivos/')
    assert r.status_code == 200
    items = r.data.get('results', r.data)
    assert items == [] or len(items) == 0


@pytest.mark.django_db
def test_upload_audit_event(client, paciente, medico, atencion_vinculada):
    client.force_authenticate(user=medico.user)
    f = SimpleUploadedFile('nuevo.pdf', b'pdf', content_type='application/pdf')
    payload = {
        'titulo': 'Nuevo',
        'tipo_archivo': 'PDF',
        'paciente_id': paciente.id,
        'archivo': f,
    }
    with capture_on_commit_callbacks(execute=True):
        r = client.post(
            '/api/archivos-medicos/archivos/',
            payload,
            format='multipart',
        )
    assert r.status_code in (200, 201)
    am_id = r.data['id']
    ev = AuditEvent.objects.filter(
        entity_type='archivos_medicos.ArchivoMedico',
        entity_id=str(am_id),
        action='CREATE',
    ).first()
    assert ev is not None
    assert ev.metadata.get('accion') == 'archivo_medico_create'
    assert '/media/' not in str(ev.metadata)


@pytest.mark.django_db
def test_download_audit_event(client, archivo_medico, paciente):
    client.force_authenticate(user=paciente.user)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(f'/api/archivos-medicos/archivos/{archivo_medico.id}/download/')
    assert r.status_code == 200
    ev = AuditEvent.objects.filter(
        entity_type='archivos_medicos.ArchivoMedico',
        entity_id=str(archivo_medico.id),
        action='UPDATE',
    ).order_by('-id').first()
    assert ev is not None
    assert ev.metadata.get('accion') == 'archivo_medico_download'


@pytest.mark.django_db
def test_delete_returns_405(client, archivo_medico, medico, atencion_vinculada):
    client.force_authenticate(user=medico.user)
    r = client.delete(f'/api/archivos-medicos/archivos/{archivo_medico.id}/')
    assert r.status_code == 405
    assert ArchivoMedico.objects.filter(pk=archivo_medico.pk).exists()


@pytest.mark.django_db
def test_secretaria_no_puede_crear_archivo(client, paciente, archivo_medico):
    sec = User.objects.create_user(username=f'sec_{_uid()}', password='x', rol='secretaria')
    client.force_authenticate(user=sec)
    f = SimpleUploadedFile('x.pdf', b'pdf', content_type='application/pdf')
    r = client.post(
        '/api/archivos-medicos/archivos/',
        {'titulo': 'X', 'tipo_archivo': 'PDF', 'paciente_id': paciente.id, 'archivo': f},
        format='multipart',
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_medico_no_puede_crear_archivo_paciente_ajeno(
    client, paciente, medico, medico_ajeno, atencion_vinculada,
):
    otro = Paciente.objects.create(dni=f'OT{_uid()}', nombre='O', apellido='T')
    client.force_authenticate(user=medico_ajeno.user)
    f = SimpleUploadedFile('x.pdf', b'pdf', content_type='application/pdf')
    r = client.post(
        '/api/archivos-medicos/archivos/',
        {'titulo': 'X', 'tipo_archivo': 'PDF', 'paciente_id': otro.id, 'archivo': f},
        format='multipart',
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_create_audit_sin_ruta_archivo(client, paciente, medico, atencion_vinculada):
    client.force_authenticate(user=medico.user)
    f = SimpleUploadedFile('sensible_nombre.pdf', b'pdf', content_type='application/pdf')
    with capture_on_commit_callbacks(execute=True):
        r = client.post(
            '/api/archivos-medicos/archivos/',
            {'titulo': 'T', 'tipo_archivo': 'PDF', 'paciente_id': paciente.id, 'archivo': f},
            format='multipart',
        )
    assert r.status_code in (200, 201)
    ev = AuditEvent.objects.filter(action='CREATE').order_by('-id').first()
    assert ev is not None
    after = str(ev.after_state or {})
    assert 'archivos_medicos/' not in after
    assert 'sensible_nombre' not in after


@pytest.mark.django_db
def test_invalid_extension_rejected(client, paciente, medico, atencion_vinculada):
    client.force_authenticate(user=medico.user)
    f = SimpleUploadedFile('mal.exe', b'x', content_type='application/octet-stream')
    payload = {
        'titulo': 'Mal',
        'tipo_archivo': 'PDF',
        'paciente_id': paciente.id,
        'archivo': f,
    }
    r = client.post('/api/archivos-medicos/archivos/', payload, format='multipart')
    assert r.status_code == 400
