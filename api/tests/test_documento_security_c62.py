"""C6.2 — Seguridad y auditoría de Documento API."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from emr.models import Documento
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
def setup_atencion(db):
    u_med = User.objects.create_user(username=f'md_{_uid()}', password='x', rol='medico')
    med = Medico.objects.create(user=u_med, matricula=f'M{_uid()}', nombre='M', apellido='D')
    u_pac = User.objects.create_user(username=f'pc_{_uid()}', password='x', rol='paciente')
    pac = Paciente.objects.create(user=u_pac, dni=f'D{_uid()}', nombre='P', apellido='A')
    rec = Recurso.objects.create(
        nombre=f'R{_uid()}', ubicacion='CEHTA', tipo_recurso='CONSULTORIO', activo=True,
    )
    turno = Turno.objects.create(
        paciente=pac,
        medico=med,
        recurso=rec,
        fecha_hora_inicio=timezone.now(),
        fecha_hora_fin=timezone.now() + timedelta(minutes=30),
        estado='CONFIRMADO',
    )
    at = Atencion.objects.create(
        turno=turno,
        paciente=pac,
        medico_principal=med,
        tipo_atencion='CONSULTORIO',
        tipo_intervencion='CONSULTA',
        estado_clinico='ABIERTA',
    )
    f = SimpleUploadedFile('informe.pdf', b'%PDF', content_type='application/pdf')
    doc = Documento.objects.create(
        atencion=at,
        tipo_documento='INFORME',
        archivo=f,
        descripcion='Informe',
        usuario_cargador=u_med,
    )
    return {'medico': med, 'paciente': pac, 'atencion': at, 'documento': doc}


@pytest.mark.django_db
def test_serializer_no_media_url(client, setup_atencion):
    doc = setup_atencion['documento']
    client.force_authenticate(user=setup_atencion['medico'].user)
    r = client.get(f'/api/documentos/{doc.id}/')
    assert r.status_code == 200
    assert '/media/' not in str(r.data)
    assert 'download_url' in r.data
    assert f'/documentos/{doc.id}/download/' in r.data['download_url']


@pytest.mark.django_db
def test_medico_descarga_200(client, setup_atencion):
    doc = setup_atencion['documento']
    client.force_authenticate(user=setup_atencion['medico'].user)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(f'/api/documentos/{doc.id}/download/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_paciente_propio_descarga(client, setup_atencion):
    doc = setup_atencion['documento']
    client.force_authenticate(user=setup_atencion['paciente'].user)
    r = client.get(f'/api/documentos/{doc.id}/download/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_usuario_sin_permiso(client, setup_atencion):
    doc = setup_atencion['documento']
    lab = User.objects.create_user(username=f'lab_{_uid()}', password='x', rol='laboratorio')
    client.force_authenticate(user=lab)
    r = client.get(f'/api/documentos/{doc.id}/download/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_create_audit(client, setup_atencion):
    at = setup_atencion['atencion']
    client.force_authenticate(user=setup_atencion['medico'].user)
    f = SimpleUploadedFile('doc2.pdf', b'%PDF2', content_type='application/pdf')
    payload = {
        'atencion_id': at.id,
        'tipo_documento': 'INFORME',
        'archivo': f,
        'descripcion': 'Nuevo',
    }
    with capture_on_commit_callbacks(execute=True):
        r = client.post('/api/documentos/', payload, format='multipart')
    assert r.status_code in (200, 201)
    doc_id = r.data['id']
    ev = AuditEvent.objects.filter(
        entity_type='emr.Documento',
        entity_id=str(doc_id),
        action='CREATE',
    ).first()
    assert ev is not None
    assert ev.metadata.get('accion') == 'documento_create'


@pytest.mark.django_db
def test_delete_405(client, setup_atencion):
    doc = setup_atencion['documento']
    client.force_authenticate(user=setup_atencion['medico'].user)
    r = client.delete(f'/api/documentos/{doc.id}/')
    assert r.status_code == 405
    assert Documento.objects.filter(pk=doc.pk).exists()
