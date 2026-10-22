"""Tests de exclusividad de situación clínica del paciente."""
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from internacion.models import Sector, Cama, Internacion
from internacion.tests.helpers import unique_suffix
from medicos.models import Medico, Especialidad
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso, Turno
from turnos.services import AtencionService, BusinessLogicError
from turnos.situacion_paciente import (
    GUARDIA_MAX_HORAS_ABIERTA,
    SituacionPacienteConflictError,
    assert_puede_admitir_internacion,
    assert_puede_iniciar_atencion_ambulatoria_o_guardia,
    cerrar_guardias_vencidas,
)


@pytest.fixture
def medico(db):
    esp, _ = Especialidad.objects.get_or_create(nombre=f"Cardio-sit-{unique_suffix()}")
    return Medico.objects.create(
        matricula=f"M-SIT-{unique_suffix()}",
        nombre="Ana",
        apellido="Situacion",
        especialidad=esp,
    )


@pytest.fixture
def paciente(db):
    suffix = unique_suffix()
    return Paciente.objects.create(
        dni=f"SIT-{suffix}",
        nombre="Luis",
        apellido="Exclusivo",
    )


@pytest.fixture
def cama_disponible(db):
    sector = Sector.objects.create(nombre=f"UCO-sit-{unique_suffix()}")
    return Cama.objects.create(
        nombre=f"C-sit-{unique_suffix()}",
        sector=sector,
        estado="DISPONIBLE",
    )


@pytest.mark.django_db
def test_internado_no_puede_iniciar_guardia(paciente, medico, cama_disponible):
    Internacion.objects.create(
        paciente=paciente,
        cama=cama_disponible,
        medico=medico,
        diagnostico_ingreso="Dx",
        activo=True,
    )
    with pytest.raises(BusinessLogicError, match="esta internado|está internado"):
        AtencionService.iniciar_atencion_guardia(
            paciente_id=paciente.pk,
            medico_id=medico.pk,
            motivo_consulta="Dolor",
        )


@pytest.mark.django_db
def test_internado_no_puede_iniciar_ambulatoria(paciente, medico, cama_disponible):
    Internacion.objects.create(
        paciente=paciente,
        cama=cama_disponible,
        medico=medico,
        diagnostico_ingreso="Dx",
        activo=True,
    )
    recurso = Recurso.objects.create(
        nombre=f"Cons-{unique_suffix()}",
        ubicacion=Recurso.Ubicacion.ICPL,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )
    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        estado=Turno.Estado.CONFIRMADO,
        fecha_hora_inicio=timezone.now() + timedelta(days=1),
        fecha_hora_fin=timezone.now() + timedelta(days=1, minutes=30),
    )
    with pytest.raises(BusinessLogicError, match="esta internado|está internado"):
        AtencionService.iniciar_atencion_desde_turno(turno.pk)


@pytest.mark.django_db
def test_guardia_abierta_bloquea_ambulatoria(paciente, medico):
    AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
    )
    with pytest.raises(SituacionPacienteConflictError, match="guardia"):
        assert_puede_iniciar_atencion_ambulatoria_o_guardia(
            paciente.pk, Atencion.ContextoAtencion.AMBULATORIA
        )


@pytest.mark.django_db
def test_nueva_consulta_desde_turno_cierra_ambulatoria_previa(paciente, medico):
    recurso = Recurso.objects.create(
        nombre=f"Cons-{unique_suffix()}",
        ubicacion=Recurso.Ubicacion.ICPL,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )
    ahora = timezone.now()
    turno_previo = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        estado=Turno.Estado.CONFIRMADO,
        fecha_hora_inicio=ahora + timedelta(days=1),
        fecha_hora_fin=ahora + timedelta(days=1, minutes=30),
    )
    previo = AtencionService.iniciar_atencion_clinica_desde_turno(turno_previo).atencion
    assert previo.estado_clinico == Atencion.EstadoClinico.ABIERTA

    turno_nuevo = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        estado=Turno.Estado.CONFIRMADO,
        fecha_hora_inicio=ahora + timedelta(days=8),
        fecha_hora_fin=ahora + timedelta(days=8, minutes=30),
    )
    nuevo = AtencionService.iniciar_atencion_clinica_desde_turno(turno_nuevo).atencion
    previo.refresh_from_db()
    assert previo.estado_clinico == Atencion.EstadoClinico.FINALIZADA
    assert previo.fecha_cierre is not None
    assert nuevo.pk != previo.pk
    assert nuevo.estado_clinico == Atencion.EstadoClinico.ABIERTA
    assert nuevo.turno_id == turno_nuevo.pk


@pytest.mark.django_db
def test_ambulatoria_abierta_bloquea_guardia(paciente, medico):
    recurso = Recurso.objects.create(
        nombre=f"Cons-{unique_suffix()}",
        ubicacion=Recurso.Ubicacion.ICPL,
        tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
        activo=True,
    )
    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        recurso=recurso,
        estado=Turno.Estado.CONFIRMADO,
        fecha_hora_inicio=timezone.now() + timedelta(days=2),
        fecha_hora_fin=timezone.now() + timedelta(days=2, minutes=30),
    )
    AtencionService.iniciar_atencion_desde_turno(turno.pk)
    with pytest.raises(BusinessLogicError, match="ambulatoria"):
        AtencionService.iniciar_atencion_guardia(
            paciente_id=paciente.pk,
            medico_id=medico.pk,
        )


@pytest.mark.django_db
def test_admitir_con_guardia_abierta_sin_origen_falla(paciente, medico, cama_disponible):
    AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
    )
    with pytest.raises(SituacionPacienteConflictError, match="guardia"):
        assert_puede_admitir_internacion(paciente.pk)


@pytest.mark.django_db
def test_derivar_guardia_a_internacion_cierra_origen(
    paciente, medico, cama_disponible, django_user_model
):
    outcome = AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
        motivo_consulta="Urgencia",
    )
    atencion = outcome.atencion

    user = django_user_model.objects.create_user(
        username=f"med-sit-{unique_suffix()}",
        password="testpass123",
        rol="medico",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/internacion/internaciones/",
        {
            "paciente": paciente.pk,
            "cama": cama_disponible.pk,
            "medico": medico.pk,
            "diagnostico_ingreso": "IAM",
            "atencion_origen": atencion.pk,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED, response.data

    atencion.refresh_from_db()
    assert atencion.estado_clinico == Atencion.EstadoClinico.FINALIZADA
    assert atencion.fecha_cierre is not None
    assert Internacion.objects.filter(paciente=paciente, activo=True).exists()


@pytest.mark.django_db
def test_atencion_clean_bloquea_guardia_si_internado(paciente, medico, cama_disponible):
    Internacion.objects.create(
        paciente=paciente,
        cama=cama_disponible,
        medico=medico,
        diagnostico_ingreso="Dx",
        activo=True,
    )
    atencion = Atencion(
        paciente=paciente,
        medico_principal=medico,
        contexto_atencion=Atencion.ContextoAtencion.GUARDIA,
        tipo_atencion=Recurso.TipoRecurso.GUARDIA,
        tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
        estado_clinico=Atencion.EstadoClinico.ABIERTA,
    )
    with pytest.raises(ValidationError):
        atencion.full_clean()


@pytest.mark.django_db
def test_cerrar_guardias_vencidas_cierra_solo_mayores_a_24h(paciente, medico):
    reciente = AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
        motivo_consulta="Reciente",
    ).atencion

    paciente_viejo = Paciente.objects.create(
        dni=f"SIT-OLD-{unique_suffix()}",
        nombre="Ana",
        apellido="Vencida",
    )
    vieja = AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente_viejo.pk,
        medico_id=medico.pk,
        motivo_consulta="Vieja",
    ).atencion
    Atencion.objects.filter(pk=vieja.pk).update(
        fecha_admision=timezone.now() - timedelta(hours=GUARDIA_MAX_HORAS_ABIERTA + 1)
    )

    cerrados = cerrar_guardias_vencidas()
    assert vieja.pk in cerrados
    assert reciente.pk not in cerrados

    vieja.refresh_from_db()
    reciente.refresh_from_db()
    assert vieja.estado_clinico == Atencion.EstadoClinico.FINALIZADA
    assert vieja.fecha_cierre is not None
    assert reciente.estado_clinico == Atencion.EstadoClinico.ABIERTA


@pytest.mark.django_db
def test_guardia_vencida_deja_iniciar_nueva_al_validar_situacion(paciente, medico):
    vieja = AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
    ).atencion
    Atencion.objects.filter(pk=vieja.pk).update(
        fecha_admision=timezone.now() - timedelta(hours=GUARDIA_MAX_HORAS_ABIERTA + 2)
    )

    # Al validar situación se cierra la vencida y permite una nueva guardia.
    assert_puede_iniciar_atencion_ambulatoria_o_guardia(
        paciente.pk, Atencion.ContextoAtencion.GUARDIA
    )
    vieja.refresh_from_db()
    assert vieja.estado_clinico == Atencion.EstadoClinico.FINALIZADA

    nueva = AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
        motivo_consulta="Nueva tras auto-cierre",
    ).atencion
    assert nueva.pk != vieja.pk
    assert nueva.estado_clinico == Atencion.EstadoClinico.ABIERTA


@pytest.mark.django_db
def test_admitir_libera_paciente_si_guardia_vencida_sin_origen(
    paciente, medico, cama_disponible
):
    vieja = AtencionService.iniciar_atencion_guardia(
        paciente_id=paciente.pk,
        medico_id=medico.pk,
    ).atencion
    Atencion.objects.filter(pk=vieja.pk).update(
        fecha_admision=timezone.now() - timedelta(hours=GUARDIA_MAX_HORAS_ABIERTA + 3)
    )

    assert_puede_admitir_internacion(paciente.pk)
    vieja.refresh_from_db()
    assert vieja.estado_clinico == Atencion.EstadoClinico.FINALIZADA