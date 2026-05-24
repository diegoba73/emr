"""Fixtures compartidas — estudios complementarios."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from archivos_medicos.models import ArchivoMedico
from estudios.models import EstudioComplementario, TipoEstudioComplementario
from historias_clinicas.models import Consulta, HistoriaClinica
from medicos.models import Medico
from pacientes.models import Paciente
from solicitudes.models import Solicitud
from turnos.models import Atencion, Recurso, Turno
from usuarios.models import User


def _uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def tipo_estudio(db):
    return TipoEstudioComplementario.objects.create(
        nombre='RX Tórax',
        modalidad=TipoEstudioComplementario.Modalidad.IMAGEN_RX,
    )


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
def admin_user(db):
    return User.objects.create_user(
        username=f'adm_{_uid()}', password='x', rol='admin', is_staff=True,
    )


@pytest.fixture
def secretaria(db):
    return User.objects.create_user(username=f'sec_{_uid()}', password='x', rol='secretaria')


@pytest.fixture
def enfermeria(db):
    return User.objects.create_user(username=f'enf_{_uid()}', password='x', rol='enfermeria')


@pytest.fixture
def recurso(db):
    return Recurso.objects.create(
        nombre=f'Cons {_uid()}',
        ubicacion='CEHTA',
        tipo_recurso='CONSULTORIO',
        activo=True,
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


@pytest.fixture
def consulta_vinculada(paciente, medico):
    hc = HistoriaClinica.objects.create(paciente=paciente)
    return Consulta.objects.create(
        historia_clinica=hc,
        medico=medico,
        fecha_hora_consulta=timezone.now(),
        motivo_consulta_detalle='Control',
    )


@pytest.fixture
def solicitud_emr(paciente, medico):
    return Solicitud.objects.create(
        paciente=paciente,
        medico_solicitante=medico,
        tipo_solicitud='ESTUDIO_IMAGEN',
        descripcion='RX',
    )


@pytest.fixture
def archivo_medico(paciente):
    content = SimpleUploadedFile('estudio.pdf', b'%PDF-1.4 test', content_type='application/pdf')
    return ArchivoMedico.objects.create(
        paciente=paciente,
        titulo='Estudio',
        tipo_archivo='PDF',
        archivo=content,
    )


@pytest.fixture
def archivo_otro_paciente(otro_paciente):
    content = SimpleUploadedFile('otro.pdf', b'%PDF-1.4', content_type='application/pdf')
    return ArchivoMedico.objects.create(
        paciente=otro_paciente,
        titulo='Otro',
        tipo_archivo='PDF',
        archivo=content,
    )


@pytest.fixture
def estudio_solicitado(paciente, tipo_estudio, medico, admin_user):
    return EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        modalidad=tipo_estudio.modalidad,
        estado=EstudioComplementario.Estado.SOLICITADO,
        medico_solicitante=medico,
        creado_por=admin_user,
    )


def _payload_crear(paciente, tipo_estudio):
    return {
        'paciente_id': paciente.id,
        'tipo_estudio': tipo_estudio.id,
        'modalidad': tipo_estudio.modalidad,
        'origen': 'INTERNO',
        'descripcion_clinica': 'Control',
    }
