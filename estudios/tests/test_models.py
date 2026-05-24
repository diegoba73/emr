"""Tests de modelos — estudios complementarios."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from estudios.models import ArchivoEstudioComplementario, EstudioComplementario, InformeEstudioComplementario
from estudios.tests.conftest import _payload_crear


@pytest.mark.django_db
def test_crear_estudio_valido(paciente, tipo_estudio, admin_user):
    e = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        modalidad=tipo_estudio.modalidad,
        creado_por=admin_user,
    )
    assert e.estado == EstudioComplementario.Estado.SOLICITADO
    assert e.paciente_id == paciente.id


@pytest.mark.django_db
def test_atencion_otro_paciente_rechazada(paciente, otro_paciente, tipo_estudio, medico, recurso):
    from datetime import timedelta
    from django.utils import timezone
    from turnos.models import Atencion, Turno

    turno = Turno.objects.create(
        paciente=otro_paciente,
        medico=medico,
        recurso=recurso,
        fecha_hora_inicio=timezone.now(),
        fecha_hora_fin=timezone.now() + timedelta(minutes=30),
        estado='CONFIRMADO',
    )
    atencion = Atencion.objects.create(
        turno=turno,
        paciente=otro_paciente,
        medico_principal=medico,
        tipo_atencion='CONSULTORIO',
        tipo_intervencion='CONSULTA',
        estado_clinico='ABIERTA',
    )
    e = EstudioComplementario(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        modalidad=tipo_estudio.modalidad,
        atencion=atencion,
    )
    with pytest.raises(ValidationError):
        e.full_clean()


@pytest.mark.django_db
def test_consulta_otro_paciente_rechazada(paciente, otro_paciente, tipo_estudio, medico):
    from historias_clinicas.models import Consulta, HistoriaClinica

    hc = HistoriaClinica.objects.create(paciente=otro_paciente)
    from django.utils import timezone

    consulta = Consulta.objects.create(
        historia_clinica=hc,
        medico=medico,
        fecha_hora_consulta=timezone.now(),
        motivo_consulta_detalle='X',
    )
    e = EstudioComplementario(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        modalidad=tipo_estudio.modalidad,
        consulta_hc=consulta,
    )
    with pytest.raises(ValidationError):
        e.full_clean()


@pytest.mark.django_db
def test_solicitud_otro_paciente_rechazada(paciente, otro_paciente, tipo_estudio, medico):
    from solicitudes.models import Solicitud

    sol = Solicitud.objects.create(
        paciente=otro_paciente,
        medico_solicitante=medico,
        tipo_solicitud='ESTUDIO_IMAGEN',
        descripcion='RX',
    )
    e = EstudioComplementario(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        modalidad=tipo_estudio.modalidad,
        solicitud_emr=sol,
    )
    with pytest.raises(ValidationError):
        e.full_clean()


@pytest.mark.django_db
def test_archivo_medico_otro_paciente_rechazado(estudio_solicitado, archivo_otro_paciente):
    v = ArchivoEstudioComplementario(
        estudio=estudio_solicitado,
        archivo_medico=archivo_otro_paciente,
    )
    with pytest.raises(ValidationError):
        v.full_clean()


@pytest.mark.django_db
def test_informe_version_manual(estudio_solicitado, admin_user):
    i1 = InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=1,
        texto='v1',
        creado_por=admin_user,
    )
    i2 = InformeEstudioComplementario.objects.create(
        estudio=estudio_solicitado,
        version=2,
        texto='v2',
        creado_por=admin_user,
    )
    assert i2.version == 2
    assert i1.version == 1
