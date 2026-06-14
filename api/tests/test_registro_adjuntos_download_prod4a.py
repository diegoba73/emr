"""PROD-4-A — Descarga segura de adjuntos clínicos en registros de procedimiento y quirúrgicos."""

from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

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
    return {'medico': med, 'paciente': pac, 'atencion': at, 'registro': registro}


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
    return {'medico': med, 'paciente': pac, 'atencion': at, 'registro': registro}


@pytest.mark.django_db
def test_procedimiento_serializer_no_media_url(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    client.force_authenticate(user=setup_procedimiento['medico'].user)
    r = client.get(f'/api/registros-procedimientos/{registro.pk}/')
    assert r.status_code == 200
    assert '/media/' not in str(r.data)
    assert 'adjunto_resultado_download_url' in r.data
    assert 'download-adjunto-resultado' in r.data['adjunto_resultado_download_url']
    assert r.data['adjunto_resultado_nombre'] == os.path.basename(registro.adjunto_resultado.name)


@pytest.mark.django_db
def test_quirurgico_serializer_no_media_url(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    client.force_authenticate(user=setup_quirurgico['medico'].user)
    r = client.get(f'/api/registros-quirurgicos/{registro.pk}/')
    assert r.status_code == 200
    assert '/media/' not in str(r.data)
    assert 'consentimiento_informado_download_url' in r.data
    assert 'download-consentimiento-informado' in r.data['consentimiento_informado_download_url']
    assert r.data['consentimiento_informado_nombre'] == os.path.basename(
        registro.consentimiento_informado.name
    )


@pytest.mark.django_db
def test_procedimiento_anonimo_bloqueado(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_quirurgico_anonimo_bloqueado(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    r = client.get(f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/')
    assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_procedimiento_medico_descarga_200(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    client.force_authenticate(user=setup_procedimiento['medico'].user)
    r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code == 200
    assert r['Content-Disposition'].startswith('attachment;')
    nombre = os.path.basename(registro.adjunto_resultado.name)
    assert nombre in r['Content-Disposition']
    body = b''.join(r.streaming_content)
    assert b'%PDF-proc' in body


@pytest.mark.django_db
def test_quirurgico_medico_descarga_200(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    client.force_authenticate(user=setup_quirurgico['medico'].user)
    r = client.get(f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/')
    assert r.status_code == 200
    assert r['Content-Disposition'].startswith('attachment;')
    nombre = os.path.basename(registro.consentimiento_informado.name)
    assert nombre in r['Content-Disposition']
    body = b''.join(r.streaming_content)
    assert b'%PDF-cons' in body


@pytest.mark.django_db
def test_procedimiento_paciente_propio_descarga(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    client.force_authenticate(user=setup_procedimiento['paciente'].user)
    r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_quirurgico_paciente_propio_descarga(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    client.force_authenticate(user=setup_quirurgico['paciente'].user)
    r = client.get(f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_procedimiento_usuario_no_autorizado(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    lab = User.objects.create_user(username=f'lab_{_uid()}', password='x', rol='laboratorio')
    client.force_authenticate(user=lab)
    r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_quirurgico_usuario_no_autorizado(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    lab = User.objects.create_user(username=f'lab2_{_uid()}', password='x', rol='laboratorio')
    client.force_authenticate(user=lab)
    r = client.get(f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_procedimiento_medico_ajeno_no_descarga(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    u = User.objects.create_user(username=f'mx_{_uid()}', password='x', rol='medico')
    med_ajeno = Medico.objects.create(user=u, matricula=f'MX{_uid()}', nombre='X', apellido='Y')
    client.force_authenticate(user=med_ajeno.user)
    r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_quirurgico_medico_ajeno_no_descarga(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    u = User.objects.create_user(username=f'my_{_uid()}', password='x', rol='medico')
    med_ajeno = Medico.objects.create(user=u, matricula=f'MY{_uid()}', nombre='X', apellido='Z')
    client.force_authenticate(user=med_ajeno.user)
    r = client.get(f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/')
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_procedimiento_sin_archivo_404(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    registro.adjunto_resultado = None
    registro.save(update_fields=['adjunto_resultado'])
    client.force_authenticate(user=setup_procedimiento['medico'].user)
    r = client.get(f'/api/registros-procedimientos/{registro.pk}/download-adjunto-resultado/')
    assert r.status_code == 404


@pytest.mark.django_db
def test_quirurgico_sin_archivo_404(client, setup_quirurgico):
    registro = setup_quirurgico['registro']
    registro.consentimiento_informado = None
    registro.save(update_fields=['consentimiento_informado'])
    client.force_authenticate(user=setup_quirurgico['medico'].user)
    r = client.get(f'/api/registros-quirurgicos/{registro.pk}/download-consentimiento-informado/')
    assert r.status_code == 404


@pytest.mark.django_db
def test_procedimiento_serializer_sin_archivo_no_download_url(client, setup_procedimiento):
    registro = setup_procedimiento['registro']
    registro.adjunto_resultado = None
    registro.save(update_fields=['adjunto_resultado'])
    client.force_authenticate(user=setup_procedimiento['medico'].user)
    r = client.get(f'/api/registros-procedimientos/{registro.pk}/')
    assert r.status_code == 200
    assert r.data['adjunto_resultado_download_url'] is None
    assert r.data['adjunto_resultado_nombre'] is None
