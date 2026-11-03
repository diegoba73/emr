"""Anuncio de llegada desde la app (Estoy en sala / laboratorio)."""
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from pacientes.services import ensure_paciente_linked_to_user
from recepcion import services as recepcion_services
from recepcion.models import LlegadaRecepcion
from recepcion.ruteo import tipo_actividad_desde_turno
from turnos.models import Turno

from .authentication import AutenticacionMovil, RolMovil


def _paciente_o_403(user):
    if str(user.rol).lower() != 'paciente':
        raise PermissionDenied('Solo el paciente puede anunciarse desde la app.')
    paciente = ensure_paciente_linked_to_user(user)
    if not paciente:
        raise ValidationError('Tu usuario no tiene ficha de paciente vinculada.')
    return paciente


def _payload_anuncio(llegada, *, modo: str, tipo_actividad: str, turno_id=None):
    msg = getattr(llegada, '_mensaje_paciente', '') or (
        f'Tu código es {llegada.codigo_llamado or "—"}. Esperá el llamado.'
    )
    return {
        'ok': True,
        'modo': modo,
        'mensaje': msg,
        'llegada_id': llegada.pk,
        'turno_id': turno_id or llegada.turno_id,
        'codigo_llamado': llegada.codigo_llamado or '',
        'numero_orden_dia': llegada.numero_orden_dia,
        'prefijo_llamado': llegada.prefijo_llamado or '',
        'tipo_actividad': tipo_actividad,
        'puesto': llegada.puesto.label_publico if llegada.puesto_id else '',
        'estado_flujo': llegada.estado_flujo,
    }


def _turnos_hoy_consulta_estudio(paciente):
    hoy = timezone.localdate()
    start = timezone.make_aware(datetime.strptime(hoy.isoformat(), '%Y-%m-%d'))
    end = start + timedelta(days=1)
    turnos = list(
        Turno.objects.filter(
            paciente=paciente,
            fecha_hora_inicio__gte=start,
            fecha_hora_inicio__lt=end,
            estado__in=[Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO],
        )
        .select_related('recurso', 'medico')
        .order_by('fecha_hora_inicio')
    )
    out = []
    for t in turnos:
        tipo = tipo_actividad_desde_turno(t)
        if tipo in ('CONSULTA', 'ESTUDIO'):
            out.append((t, tipo))
    return out


def _llegada_activa_turno(turno):
    hoy = timezone.localdate()
    return (
        LlegadaRecepcion.objects.filter(turno=turno, fecha=hoy)
        .exclude(
            estado_flujo__in=[
                LlegadaRecepcion.EstadoFlujo.CANCELADO,
                LlegadaRecepcion.EstadoFlujo.NO_ASISTIO,
                LlegadaRecepcion.EstadoFlujo.ATENDIDO,
            ]
        )
        .select_related('puesto')
        .order_by('-id')
        .first()
    )


def _llegada_lab_hoy(paciente):
    hoy = timezone.localdate()
    return (
        LlegadaRecepcion.objects.filter(
            paciente=paciente,
            fecha=hoy,
            tipo_actividad='EXTRACCION',
        )
        .exclude(
            estado_flujo__in=[
                LlegadaRecepcion.EstadoFlujo.CANCELADO,
                LlegadaRecepcion.EstadoFlujo.NO_ASISTIO,
                LlegadaRecepcion.EstadoFlujo.ATENDIDO,
            ]
        )
        .select_related('puesto')
        .order_by('-id')
        .first()
    )


class RecepcionHoyMovil(APIView):
    """Estado de anuncio del día para la UI (Estoy en sala / lab)."""

    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def get(self, request):
        paciente = _paciente_o_403(request.user)
        candidatos = _turnos_hoy_consulta_estudio(paciente)
        turno_hoy = candidatos[0][0] if candidatos else None
        llegada_turno = _llegada_activa_turno(turno_hoy) if turno_hoy else None
        anunciado = bool(
            llegada_turno
            and llegada_turno.estado_flujo
            != LlegadaRecepcion.EstadoFlujo.PROGRAMADO
        )
        lab = _llegada_lab_hoy(paciente)
        return Response(
            {
                'turno_hoy_id': turno_hoy.pk if turno_hoy else None,
                'puedo_estoy_en_sala': bool(turno_hoy) and not anunciado,
                'estoy_en_sala': (
                    _payload_anuncio(
                        llegada_turno,
                        modo='turno',
                        tipo_actividad=llegada_turno.tipo_actividad,
                        turno_id=turno_hoy.pk,
                    )
                    if anunciado and llegada_turno
                    else None
                ),
                'lab': (
                    _payload_anuncio(
                        lab, modo='walkin', tipo_actividad='EXTRACCION'
                    )
                    if lab
                    else None
                ),
            }
        )


class EstoyEnSalaMovil(APIView):
    """Paciente con turno hoy (consulta/estudio) se anuncia a cola de recepción."""

    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def post(self, request):
        paciente = _paciente_o_403(request.user)
        turno_id = request.data.get('turno_id')
        candidatos = _turnos_hoy_consulta_estudio(paciente)
        if not candidatos:
            raise ValidationError(
                'No tenés un turno de consulta o estudio para hoy. Acercate a recepción.'
            )
        turno = None
        tipo = None
        if turno_id is not None:
            try:
                tid = int(turno_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError('turno_id inválido.') from exc
            for t, tip in candidatos:
                if t.pk == tid:
                    turno, tipo = t, tip
                    break
            if turno is None:
                raise ValidationError('Ese turno no está disponible para anunciarte hoy.')
        else:
            turno, tipo = candidatos[0]

        motivo = 'CON_TURNO' if tipo == 'CONSULTA' else 'ESTUDIO'
        with transaction.atomic():
            llegada = recepcion_services.checkin_turno(
                turno=turno, motivo=motivo, pasar_a_medico=False
            )
        return Response(
            _payload_anuncio(
                llegada, modo='turno', tipo_actividad=tipo, turno_id=turno.pk
            )
        )


class AnuncioLabMovil(APIView):
    """Paciente se anuncia a sala de extracción (sin reingresar DNI)."""

    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def post(self, request):
        paciente = _paciente_o_403(request.user)
        with transaction.atomic():
            llegada = recepcion_services.checkin_walkin(
                paciente=paciente,
                tipo_actividad='EXTRACCION',
                motivo='EXTRACCION',
            )
        return Response(
            _payload_anuncio(llegada, modo='walkin', tipo_actividad='EXTRACCION')
        )
