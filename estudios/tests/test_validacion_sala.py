"""Tests — disponibilidad de salas de estudio (buffer 30 min)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from estudios.models import EstudioComplementario
from estudios.services import asignar_turno_estudio
from turnos.models import Turno
from turnos.validacion_sala import validar_disponibilidad_sala_estudio


@pytest.mark.django_db
def test_sala_rechaza_turno_dentro_de_buffer_30_min(estudio_solicitado, recurso_sala):
    inicio = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=5)
    fin = inicio + timedelta(minutes=30)
    Turno.objects.create(
        paciente=estudio_solicitado.paciente,
        recurso=recurso_sala,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=fin,
        estado=Turno.Estado.CONFIRMADO,
    )
    nuevo_inicio = fin + timedelta(minutes=15)
    nuevo_fin = nuevo_inicio + timedelta(minutes=30)
    with pytest.raises(ValidationError):
        validar_disponibilidad_sala_estudio(
            recurso=recurso_sala,
            fecha_hora_inicio=nuevo_inicio,
            fecha_hora_fin=nuevo_fin,
        )


@pytest.mark.django_db
def test_sala_acepta_turno_con_30_min_libres(estudio_solicitado, recurso_sala):
    inicio = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=6)
    fin = inicio + timedelta(minutes=30)
    Turno.objects.create(
        paciente=estudio_solicitado.paciente,
        recurso=recurso_sala,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=fin,
        estado=Turno.Estado.CONFIRMADO,
    )
    nuevo_inicio = fin + timedelta(minutes=30)
    nuevo_fin = nuevo_inicio + timedelta(minutes=30)
    validar_disponibilidad_sala_estudio(
        recurso=recurso_sala,
        fecha_hora_inicio=nuevo_inicio,
        fecha_hora_fin=nuevo_fin,
    )


@pytest.mark.django_db
def test_asignar_turno_estudio_rechaza_sala_ocupada(
    secretaria, estudio_solicitado, recurso_sala, tipo_estudio, paciente, admin_user,
):
    inicio = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=7)
    fin = inicio + timedelta(minutes=30)
    Turno.objects.create(
        paciente=paciente,
        recurso=recurso_sala,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=fin,
        estado=Turno.Estado.CONFIRMADO,
    )
    otro = EstudioComplementario.objects.create(
        paciente=paciente,
        tipo_estudio=tipo_estudio,
        modalidad=tipo_estudio.modalidad,
        estado=EstudioComplementario.Estado.SOLICITADO,
        creado_por=admin_user,
    )
    with pytest.raises(ValidationError):
        asignar_turno_estudio(
            otro,
            user=secretaria,
            recurso=recurso_sala,
            fecha_hora_inicio=inicio + timedelta(minutes=15),
            fecha_hora_fin=fin + timedelta(minutes=15),
        )
