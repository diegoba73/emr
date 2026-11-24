"""Pedido de estudio por paciente (app/portal) y tipificación/agenda por secretaría."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from medicos.agenda import duracion_de, recurso_de_franja_publicada, validar_reserva
from medicos.models import DisponibilidadMedico, Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno
from usuarios.roles import es_secretaria_institucional

from .models import (
    EstudioComplementario,
    MedicoTipoEstudio,
    PedidoEstudioPaciente,
    TipoEstudioComplementario,
    TipoEstudioSala,
)
from . import services


def _rol(user) -> str:
    return str(getattr(user, 'rol', '') or '').lower()


def usuario_puede_gestionar_pedidos_estudio(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or _rol(user) == 'admin':
        return True
    return es_secretaria_institucional(user)


_MSG_ESTUDIO_SOLO_SECRETARIA = (
    'Los turnos de estudio solo los agenda secretaría (presencial o por teléfono). '
    'Desde el portal o la app solo podés reservar consultas.'
)


def crear_pedido_estudio_paciente(
    *,
    user,
    paciente: Paciente,
    foto,
    origen_canal: str,
    notas: str = '',
) -> PedidoEstudioPaciente:
    """Deshabilitado: estudios solo los agenda secretaría (presencial / teléfono)."""
    raise ValidationError(_MSG_ESTUDIO_SOLO_SECRETARIA)


def salas_ids_para_tipo(tipo_estudio_id: int) -> set[int]:
    return set(
        TipoEstudioSala.objects.filter(tipo_estudio_id=tipo_estudio_id).values_list(
            'recurso_id', flat=True
        )
    )


def medicos_ids_para_tipo(tipo_estudio_id: int) -> set[int]:
    return set(
        MedicoTipoEstudio.objects.filter(tipo_estudio_id=tipo_estudio_id).values_list(
            'medico_id', flat=True
        )
    )


def validar_catalogo_agenda_estudio(*, medico: Medico, tipo_estudio: TipoEstudioComplementario, recurso: Recurso):
    if not MedicoTipoEstudio.objects.filter(medico=medico, tipo_estudio=tipo_estudio).exists():
        raise ValidationError(
            {'medico_id': 'Ese médico no tiene habilitado este tipo de estudio en el catálogo.'}
        )
    salas = salas_ids_para_tipo(tipo_estudio.pk)
    if not salas:
        raise ValidationError(
            {'tipo_estudio': 'El tipo de estudio no tiene salas asociadas en el catálogo.'}
        )
    if recurso.pk not in salas:
        raise ValidationError(
            {'recurso_id': 'La sala no corresponde a este tipo de estudio.'}
        )


@transaction.atomic
def agendar_pedido_estudio(
    pedido: PedidoEstudioPaciente,
    *,
    user,
    tipo_estudio: TipoEstudioComplementario,
    medico: Medico,
    inicio,
    horario_id: int | None = None,
) -> PedidoEstudioPaciente:
    if not usuario_puede_gestionar_pedidos_estudio(user):
        raise ValidationError('Solo secretaría puede agendar pedidos de estudio.')
    pedido = PedidoEstudioPaciente.objects.select_for_update().get(pk=pedido.pk)
    if pedido.estado != PedidoEstudioPaciente.Estado.PENDIENTE:
        raise ValidationError('El pedido ya no está pendiente.')

    if timezone.is_naive(inicio):
        inicio = timezone.make_aware(inicio, timezone.get_current_timezone())

    slot = duracion_de(medico)
    fin = inicio + slot

    # Recurso: franja publicada ESTUDIO del médico.
    if not DisponibilidadMedico.objects.filter(medico=medico, tipo='ESTUDIO', activo=True).exists():
        raise ValidationError(
            {'medico_id': 'El médico no tiene franjas de estudio publicadas.'}
        )
    try:
        recurso = recurso_de_franja_publicada(
            medico,
            inicio,
            fin,
            tipo='ESTUDIO',
            horario_id=horario_id,
        )
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError({'inicio': str(exc)}) from exc

    validar_catalogo_agenda_estudio(medico=medico, tipo_estudio=tipo_estudio, recurso=recurso)
    validar_reserva(
        medico,
        inicio,
        fin,
        recurso,
        exigir_horario=True,
        horario_id=horario_id,
    )

    estudio = services.crear_estudio(
        {
            'paciente': pedido.paciente,
            'tipo_estudio': tipo_estudio,
            'practica': tipo_estudio.practica,
            'origen': EstudioComplementario.Origen.EXTERNO,
            'descripcion_clinica': 'Pedido de estudio vía app/portal (foto del pedido médico).',
            'medico_solicitante': None,
        },
        user=user,
    )
    estudio = services.asignar_turno_estudio(
        estudio,
        user=user,
        recurso=recurso,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=fin,
        medico=medico,
        estado_turno=Turno.Estado.RESERVADO,
    )
    turno = estudio.turno
    pedido.estudio = estudio
    pedido.turno = turno
    pedido.estado = PedidoEstudioPaciente.Estado.AGENDADO
    pedido.agendado_por = user
    pedido.agendado_en = timezone.now()
    pedido.save(
        update_fields=[
            'estudio',
            'turno',
            'estado',
            'agendado_por',
            'agendado_en',
            'updated_at',
        ]
    )
    return pedido


def turno_viene_de_pedido_paciente(turno: Turno) -> bool:
    if not turno or not turno.pk:
        return False
    return PedidoEstudioPaciente.objects.filter(
        turno_id=turno.pk,
        estado=PedidoEstudioPaciente.Estado.AGENDADO,
    ).exists()


def turno_es_estudio_agenda(turno: Turno) -> bool:
    """True si el turno es de estudio/procedimiento de agenda (no consulta)."""
    if not turno or not turno.pk:
        return False
    if tipo_estudio_de_turno(turno) is not None:
        return True
    if turno_viene_de_pedido_paciente(turno):
        return True
    if EstudioComplementario.objects.filter(turno_id=turno.pk).exists():
        return True
    recurso = getattr(turno, 'recurso', None)
    tipo_recurso = str(getattr(recurso, 'tipo_recurso', '') or '').upper()
    return tipo_recurso in {
        Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
        Recurso.TipoRecurso.SALA_HEMODINAMIA,
        Recurso.TipoRecurso.QUIROFANO,
    }


def tipo_estudio_de_turno(turno: Turno) -> TipoEstudioComplementario | None:
    """Tipo tipificado vinculado al turno (pedido agendado o estudio directo)."""
    if not turno or not turno.pk:
        return None
    pedido = (
        PedidoEstudioPaciente.objects.filter(
            turno_id=turno.pk,
            estado=PedidoEstudioPaciente.Estado.AGENDADO,
        )
        .select_related('estudio__tipo_estudio')
        .first()
    )
    if pedido and pedido.estudio_id and getattr(pedido.estudio, 'tipo_estudio_id', None):
        return pedido.estudio.tipo_estudio
    estudio = (
        EstudioComplementario.objects.filter(turno_id=turno.pk)
        .select_related('tipo_estudio')
        .first()
    )
    if estudio and estudio.tipo_estudio_id:
        return estudio.tipo_estudio
    return None


def validar_reprogramacion_estudio(
    turno: Turno,
    *,
    actor,
    medico: Medico,
    recurso: Recurso,
    tipo_franja: str | None = None,
) -> None:
    """
    Reglas comunes web/móvil para reprogramar turnos de estudio tipificado.
    Paciente: mismo médico, franja ESTUDIO, sala compatible con el tipo.
    Secretaría: si reasigna médico/sala, exige compatibilidad de catálogo.
    """
    tipo_estudio = tipo_estudio_de_turno(turno)
    es_pedido = turno_viene_de_pedido_paciente(turno)
    if not tipo_estudio and not es_pedido:
        return

    rol = _rol(actor)
    if rol == 'paciente':
        raise ValidationError(_MSG_ESTUDIO_SOLO_SECRETARIA)

    # Staff: si hay tipo tipificado, médico y sala deben ser compatibles.
    if tipo_estudio and medico is not None and recurso is not None:
        validar_catalogo_agenda_estudio(
            medico=medico, tipo_estudio=tipo_estudio, recurso=recurso
        )
