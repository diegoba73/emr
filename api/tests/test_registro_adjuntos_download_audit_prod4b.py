"""PROD-4-B — Auditoría de descarga de adjuntos clínicos en registros turnos."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from medicos.models import Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, RegistroProcedimiento, RegistroQuirurgico, Turno
from usuarios.models import User


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def setup_procedimiento(db):
    u_med = User.objects.create_user(username=f'md_{_uid()}', password='x', rol='medico')
    med = Medico.objects.create(user=u_med, matricula=f'M{_uid()}', nombre='M', apellido='D')
    u_pac = User.objects.create_user(username=f'pc_{_uid()}', password='x', rol='paciente')
    pac = Paciente.objects.create(user=u_pac, dni=f'D{_uid()}', nombre='P', apellido='A')
    rec = Recurso.objects.create(
        nombre=f'R{_uid()}', ubicacion='CEHTA', tipo_recurso='SALA_PROCEDIMIENTO', activo=True,
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
        tipo_atencion='SALA_PROCEDIMIENTO',
        tipo_intervencion='ESTUDIO',
        estado_clinico='ABIERTA',
    )
    f = SimpleUploadedFile('resultado.pdf', b'%PDF-proc', content_type='application/pdf')
    registro = RegistroProcedimiento.objects.create(
        atencion=at,
        descripcion_procedimiento='Eco Doppler',
        adjunto_resultado=f,
    )
    return {'medico': med, 'paciente': pac, 'registro': registro}


@pytest.fixture
def setup_quirurgico(db):
    u_med = User.objects.create_user(username=f'mq_{_uid()}', password='x', rol='medico')
    med = Medico.objects.create(user=u_med, matricula=f'MQ{_uid()}', nombre='Q', apellido='X')
    u_pac = User.objects.create_user(username=f'pq_{_uid()}', password='x', rol='paciente')
    pac = Paciente.objects.create(user=u_pac, dni=f'DQ{_uid()}', nombre='P', apellido='Q')
    rec = Recurso.objects.create(
        nombre=f'RQ{_uid()}', ubicacion='CEHTA', tipo_recurso='QUIROFANO', activo=True,
    )
    turno = Turno.objects.create(
        paciente=pac,
        medico=med,
        recurso=rec,
        fecha_hora_inicio=timezone.now(),
        fecha_hora_fin=timezone.now() + timedelta(hours=2),
        estado='CONFIRMADO',
    )
    at = Atencion.objects.create(
        turno=turno,
        paciente=pac,
        medico_principal=med,
        tipo_atencion='QUIROFANO',
        tipo_intervencion='CIRUGIA',
        estado_clinico='ABIERTA',
    )
    f = SimpleUploadedFile('consentimiento.pdf', b'%PDF-cons', content_type='application/pdf')
    registro = RegistroQuirurgico.objects.create(
        atencion=at,
        anestesista=med,
        diagnostico_preoperatorio='Dx pre',
        protocolo_quirurgico='Protocolo',
        consentimiento_informado=f,
    )
    return {'medico': med, 'registro': registro}


def _audit_blob(ev: AuditEvent) -> str:
    return str(ev.metadata or {}) + str(ev.after_state or {}) + str(ev.before_state or {})


@pytest.mark.django_db
def test_procedimiento_descarga_crea_auditoria(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    med = setup_procedimiento['medico']
    n_before = AuditEvent.objects.filter(entity_type='turnos.RegistroProcedimiento').count()
    client.force_authenticate(user=med.user)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code == 200
    assert AuditEvent.objects.filter(entity_type='turnos.RegistroProcedimiento').count() == n_before + 1
    ev = AuditEvent.objects.filter(
        entity_type='turnos.RegistroProcedimiento',
        entity_id=str(registro.pk),
        action='UPDATE',
    ).order_by('-id').first()
    assert ev is not None
    assert ev.actor_id == med.user.id
    assert ev.module == 'turnos'
    assert ev.success is True
    assert ev.metadata.get('accion') == 'registro_procedimiento_adjunto_download'
    assert ev.metadata.get('field') == 'adjunto_resultado'
    assert ev.metadata.get('endpoint') == 'download-adjunto-resultado'
    blob = _audit_blob(ev)
    assert '/media/' not in blob
    assert 'emr/procedimientos' not in blob
    assert 'resultado.pdf' not in blob
    assert 'absolute_path' not in blob.lower()
    assert 'file_path' not in blob.lower()


@pytest.mark.django_db
def test_quirurgico_descarga_crea_auditoria(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    med = setup_quirurgico['medico']
    n_before = AuditEvent.objects.filter(entity_type='turnos.RegistroQuirurgico').count()
    client.force_authenticate(user=med.user)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(
            f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/'
        )
    assert r.status_code == 200
    assert AuditEvent.objects.filter(entity_type='turnos.RegistroQuirurgico').count() == n_before + 1
    ev = AuditEvent.objects.filter(
        entity_type='turnos.RegistroQuirurgico',
        entity_id=str(registro.pk),
        action='UPDATE',
    ).order_by('-id').first()
    assert ev is not None
    assert ev.actor_id == med.user.id
    assert ev.module == 'turnos'
    assert ev.success is True
    assert ev.metadata.get('accion') == 'registro_quirurgico_consentimiento_download'
    assert ev.metadata.get('field') == 'consentimiento_informado'
    assert ev.metadata.get('endpoint') == 'download-consentimiento-informado'
    blob = _audit_blob(ev)
    assert '/media/' not in blob
    assert 'emr/consentimientos' not in blob
    assert 'consentimiento.pdf' not in blob


@pytest.mark.django_db
def test_procedimiento_no_autorizado_no_auditoria(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    lab = User.objects.create_user(username=f'lab_{_uid()}', password='x', rol='laboratorio')
    n_before = AuditEvent.objects.filter(
        metadata__accion='registro_procedimiento_adjunto_download',
    ).count()
    client.force_authenticate(user=lab)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code in (403, 404)
    assert AuditEvent.objects.filter(
        metadata__accion='registro_procedimiento_adjunto_download',
    ).count() == n_before


@pytest.mark.django_db
def test_quirurgico_no_autorizado_no_auditoria(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    lab = User.objects.create_user(username=f'lab2_{_uid()}', password='x', rol='laboratorio')
    n_before = AuditEvent.objects.filter(
        metadata__accion='registro_quirurgico_consentimiento_download',
    ).count()
    client.force_authenticate(user=lab)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(
            f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/'
        )
    assert r.status_code in (403, 404)
    assert AuditEvent.objects.filter(
        metadata__accion='registro_quirurgico_consentimiento_download',
    ).count() == n_before


@pytest.mark.django_db
def test_procedimiento_sin_archivo_no_auditoria(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    registro.adjunto_resultado = None
    registro.save(update_fields=['adjunto_resultado'])
    n_before = AuditEvent.objects.filter(
        metadata__accion='registro_procedimiento_adjunto_download',
    ).count()
    client.force_authenticate(user=setup_procedimiento['medico'].user)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code == 404
    assert AuditEvent.objects.filter(
        metadata__accion='registro_procedimiento_adjunto_download',
    ).count() == n_before


@pytest.mark.django_db
def test_quirurgico_sin_archivo_no_auditoria(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    registro.consentimiento_informado = None
    registro.save(update_fields=['consentimiento_informado'])
    n_before = AuditEvent.objects.filter(
        metadata__accion='registro_quirurgico_consentimiento_download',
    ).count()
    client.force_authenticate(user=setup_quirurgico['medico'].user)
    with capture_on_commit_callbacks(execute=True):
        r = client.get(
            f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/'
        )
    assert r.status_code == 404
    assert AuditEvent.objects.filter(
        metadata__accion='registro_quirurgico_consentimiento_download',
    ).count() == n_before
