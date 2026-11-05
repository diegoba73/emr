"""Operaciones de recepción: anuncio, check-in, llamado, tablero."""
from __future__ import annotations

import secrets

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    TIPOS_COBERTURA_SECRETARIA,
    CoberturaRecepcion,
    LlegadaRecepcion,
    PuestoRecepcion,
)
from .ruteo import ContextoRuteo, contexto_desde_turno, resolver_puesto, tipo_actividad_desde_turno

# Motivo kiosco → prefijo de código (códigos internos / cola; no todos son del QR papel).
PREFIJO_POR_MOTIVO = {
    'CON_TURNO': 'T',
    'SIN_TURNO': 'S',
    'ESTUDIO': 'E',
    'PROCEDIMIENTO': 'P',
    'CIRUGIA': 'P',
    'EXTRACCION': 'L',
    # Legacy / tipología interna
    'CONSULTA': 'T',
}

# QR papel: solo recepción (puesto 1) o sala de extracción.
MOTIVOS_KIOSCO_PAPEL = frozenset({'SIN_TURNO', 'EXTRACCION'})
MOTIVOS_KIOSCO = MOTIVOS_KIOSCO_PAPEL

CODIGO_PUESTO_1 = 'puesto-1'


def puesto_recepcion_1() -> PuestoRecepcion:
    """Puesto físico 1 (QR papel / anuncio walk-in a secretaría)."""
    try:
        return PuestoRecepcion.objects.get(codigo=CODIGO_PUESTO_1, activo=True)
    except PuestoRecepcion.DoesNotExist as exc:
        raise ValidationError(
            {'puesto': 'No está configurado el puesto 1 de recepción.'}
        ) from exc


def prefijo_desde_motivo(motivo: str) -> str:
    m = (motivo or '').strip().upper()
    return PREFIJO_POR_MOTIVO.get(m, 'S')


def prefijo_desde_llegada(*, tipo_actividad: str, tiene_turno: bool, motivo: str | None = None) -> str:
    if motivo:
        return prefijo_desde_motivo(motivo)
    tipo = (tipo_actividad or '').strip().upper()
    if tipo == 'EXTRACCION':
        return 'L'
    if tipo == 'ESTUDIO':
        return 'E'
    if tipo in ('PROCEDIMIENTO', 'CIRUGIA'):
        return 'P'
    if tipo == 'SIN_TURNO':
        return 'S'
    if tipo == 'CONSULTA' and tiene_turno:
        return 'T'
    if tiene_turno:
        return 'T'
    return 'S'


def _siguiente_numero_prefijo(fecha, prefijo: str) -> int:
    agg = (
        LlegadaRecepcion.objects.filter(fecha=fecha, prefijo_llamado=prefijo)
        .aggregate(m=Max('numero_orden_dia'))
    )
    return (agg['m'] or 0) + 1


def _siguiente_numero_orden(fecha) -> int:
    """Fallback global (legacy); preferir _siguiente_numero_prefijo."""
    agg = LlegadaRecepcion.objects.filter(fecha=fecha).aggregate(m=Max('numero_orden_dia'))
    return (agg['m'] or 0) + 1


def asignar_codigo_llamado(
    llegada: LlegadaRecepcion,
    *,
    motivo: str | None = None,
    force: bool = False,
) -> LlegadaRecepcion:
    """Asigna prefijo + codigo_llamado (T03) una sola vez por llegada."""
    if llegada.codigo_llamado and not force:
        return llegada
    prefijo = prefijo_desde_llegada(
        tipo_actividad=llegada.tipo_actividad,
        tiene_turno=bool(llegada.turno_id),
        motivo=motivo,
    )
    n = _siguiente_numero_prefijo(llegada.fecha, prefijo)
    llegada.prefijo_llamado = prefijo
    llegada.numero_orden_dia = n
    llegada.codigo_llamado = f'{prefijo}{n:02d}'
    llegada.save(
        update_fields=[
            'prefijo_llamado',
            'numero_orden_dia',
            'codigo_llamado',
            'updated_at',
        ]
    )
    return llegada


def ensure_token_publico(llegada: LlegadaRecepcion) -> LlegadaRecepcion:
    """Garantiza token para QR / página de espera del paciente."""
    if llegada.token_publico:
        return llegada
    for _ in range(8):
        candidate = secrets.token_urlsafe(18)[:32]
        if not LlegadaRecepcion.objects.filter(token_publico=candidate).exists():
            llegada.token_publico = candidate
            llegada.save(update_fields=['token_publico', 'updated_at'])
            return llegada
    raise ValidationError({'token_publico': 'No se pudo generar token de espera.'})


def _destino_desde_turno(turno) -> tuple:
    recurso = getattr(turno, 'recurso', None)
    if recurso:
        return recurso, recurso.nombre
    return None, ''


def _normalizar_medico_turno(turno) -> None:
    """
    Si el turno apunta a un Medico huérfano (sin user) y existe un homónimo
    con usuario, reasigna al perfil canónico para que el médico lo vea en recepción.
    """
    from medicos.models import Medico

    medico = getattr(turno, 'medico', None)
    if not medico or getattr(medico, 'user_id', None):
        return
    ap = (medico.apellido or '').strip()
    primer = ((medico.nombre or '').strip().split() or [''])[0]
    if not ap:
        return
    q = Medico.objects.filter(apellido__iexact=ap, user__isnull=False).exclude(pk=medico.pk)
    if primer:
        q = q.filter(nombre__istartswith=primer)
    canon = q.order_by('id').first()
    if not canon:
        return
    turno.medico = canon
    turno.save(update_fields=['medico', 'updated_at'] if hasattr(turno, 'updated_at') else ['medico'])


@transaction.atomic
def checkin_turno(
    *,
    turno,
    puesto_id=None,
    user=None,
    motivo: str | None = None,
    pasar_a_medico: bool = False,
) -> LlegadaRecepcion:
    """
    Registra llegada vinculada a un turno.

    Por defecto queda en EN_ESPERA_RECEPCION (anuncio / recepción).
    pasar_a_medico=True: check-in administrativo → cola del médico (EN_ESPERA).
    No aplica a EXTRACCION (cola laboratorio).
    """
    if not turno.paciente_id:
        raise ValidationError({'turno': 'El turno no tiene paciente.'})
    hoy = timezone.localdate()
    inicio = timezone.localtime(turno.fecha_hora_inicio).date()
    if inicio != hoy:
        raise ValidationError({'turno': 'Solo se puede hacer check-in de turnos de hoy.'})
    if turno.estado in ('CANCELADO',):
        raise ValidationError({'turno': 'El turno está cancelado.'})

    _normalizar_medico_turno(turno)

    existente = (
        LlegadaRecepcion.objects.select_for_update()
        .filter(turno=turno, fecha=hoy)
        .exclude(estado_flujo__in=['CANCELADO', 'NO_ASISTIO'])
        .first()
    )
    if existente and existente.estado_flujo not in (
        LlegadaRecepcion.EstadoFlujo.PROGRAMADO,
    ):
        llegada = ensure_token_publico(existente)
        if not llegada.codigo_llamado:
            llegada = asignar_codigo_llamado(llegada, motivo=motivo)
        if pasar_a_medico and llegada.tipo_actividad != 'EXTRACCION':
            if llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION:
                llegada = derivar_a_espera_clinica(llegada)
        llegada._mensaje_paciente = f'Andá al {llegada.puesto.label_publico}.'  # type: ignore[attr-defined]
        return llegada

    ctx = contexto_desde_turno(turno)
    if ctx.tipo_actividad == 'EXTRACCION':
        puesto = puesto_sala_extraccion()
        resultado_msg = f'Andá al {puesto.label_publico}.'
    elif puesto_id:
        try:
            puesto = PuestoRecepcion.objects.get(pk=puesto_id, activo=True)
        except PuestoRecepcion.DoesNotExist:
            raise ValidationError({'puesto_id': 'Puesto inválido.'})
        resultado_msg = 'Esperá en recepción. Te van a llamar por pantalla.'
    else:
        puesto = puesto_placeholder_recepcion()
        resultado_msg = 'Esperá en recepción. Te van a llamar por pantalla.'

    destino, destino_label = _destino_desde_turno(turno)
    now = timezone.now()
    if existente:
        existente.puesto = puesto
        existente.estado_flujo = LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION
        existente.checkin_en = now
        existente.tipo_actividad = ctx.tipo_actividad
        existente.destino_recurso = destino
        existente.destino_label = destino_label
        existente.save()
        llegada = existente
    else:
        llegada = LlegadaRecepcion.objects.create(
            paciente_id=turno.paciente_id,
            puesto=puesto,
            turno=turno,
            tipo_actividad=ctx.tipo_actividad,
            estado_flujo=LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION,
            fecha=hoy,
            checkin_en=now,
            destino_recurso=destino,
            destino_label=destino_label,
        )
    llegada = ensure_token_publico(llegada)
    llegada = asignar_codigo_llamado(llegada, motivo=motivo)
    if hasattr(turno, 'asistencia_confirmada_en') and not turno.asistencia_confirmada_en:
        turno.asistencia_confirmada_en = now
        turno.save(update_fields=['asistencia_confirmada_en', 'updated_at'])

    # Check-in administrativo explícito → cola médico (nunca L).
    if (
        pasar_a_medico
        and llegada.tipo_actividad != 'EXTRACCION'
        and llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION
    ):
        llegada = derivar_a_espera_clinica(llegada)

    llegada._mensaje_paciente = resultado_msg  # type: ignore[attr-defined]
    return llegada


@transaction.atomic
def checkin_walkin(
    *,
    paciente,
    tipo_actividad='SIN_TURNO',
    puesto_id=None,
    notas='',
    motivo: str | None = None,
) -> LlegadaRecepcion:
    hoy = timezone.localdate()
    tipo = tipo_actividad or 'SIN_TURNO'
    if tipo == 'EXTRACCION':
        puesto = puesto_sala_extraccion()
        msg = f'Andá al {puesto.label_publico}.'
    elif puesto_id:
        try:
            puesto = PuestoRecepcion.objects.get(pk=puesto_id, activo=True)
        except PuestoRecepcion.DoesNotExist:
            raise ValidationError({'puesto_id': 'Puesto inválido.'})
        msg = 'Esperá en recepción. Te van a llamar por pantalla.'
    else:
        puesto = puesto_placeholder_recepcion()
        msg = 'Esperá en recepción. Te van a llamar por pantalla.'

    abierta = (
        LlegadaRecepcion.objects.select_for_update()
        .filter(
            paciente=paciente,
            fecha=hoy,
            turno__isnull=True,
            estado_flujo__in=[
                LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION,
                LlegadaRecepcion.EstadoFlujo.EN_ESPERA,
                LlegadaRecepcion.EstadoFlujo.LLAMADO,
            ],
        )
        .first()
    )
    if abierta:
        abierta = ensure_token_publico(abierta)
        if not abierta.codigo_llamado:
            abierta = asignar_codigo_llamado(abierta, motivo=motivo or tipo)
        abierta._mensaje_paciente = msg  # type: ignore[attr-defined]
        return abierta

    llegada = LlegadaRecepcion.objects.create(
        paciente=paciente,
        puesto=puesto,
        turno=None,
        tipo_actividad=tipo,
        estado_flujo=LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION,
        fecha=hoy,
        checkin_en=timezone.now(),
        notas=notas or '',
        destino_label=puesto.label_publico if tipo == 'EXTRACCION' else '',
    )
    llegada = ensure_token_publico(llegada)
    llegada = asignar_codigo_llamado(llegada, motivo=motivo or tipo)
    llegada._mensaje_paciente = msg  # type: ignore[attr-defined]
    return llegada


@transaction.atomic
def mover_puesto(llegada: LlegadaRecepcion, puesto_id: int) -> LlegadaRecepcion:
    try:
        puesto = PuestoRecepcion.objects.get(pk=puesto_id, activo=True)
    except PuestoRecepcion.DoesNotExist:
        raise ValidationError({'puesto_id': 'Puesto inválido.'})
    llegada = LlegadaRecepcion.objects.select_for_update().get(pk=llegada.pk)
    llegada.puesto = puesto
    llegada.save(update_fields=['puesto', 'updated_at'])
    return llegada


@transaction.atomic
def derivar_a_espera_clinica(llegada: LlegadaRecepcion) -> LlegadaRecepcion:
    """Check-in administrativo: pasa de recepción a cola del médico."""
    llegada = LlegadaRecepcion.objects.select_for_update().get(pk=llegada.pk)
    if llegada.tipo_actividad == LlegadaRecepcion.TipoActividad.EXTRACCION:
        raise ValidationError(
            {'tipo_actividad': 'Extracción/laboratorio no pasa a cola del médico.'}
        )
    if not llegada.turno_id or not getattr(llegada, 'turno', None) or not llegada.turno.medico_id:
        raise ValidationError(
            {'turno': 'Hace falta un turno con médico para el check-in a consulta.'}
        )
    if llegada.estado_flujo not in (
        LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION,
        LlegadaRecepcion.EstadoFlujo.PROGRAMADO,
        LlegadaRecepcion.EstadoFlujo.LLAMADO,
    ):
        raise ValidationError({'estado_flujo': 'La llegada no está en recepción.'})
    llegada.estado_flujo = LlegadaRecepcion.EstadoFlujo.EN_ESPERA
    if llegada.turno.recurso_id:
        llegada.destino_recurso_id = llegada.turno.recurso_id
        llegada.destino_label = llegada.turno.recurso.nombre
    llegada.zona_llamado = ''
    llegada.save(
        update_fields=[
            'estado_flujo',
            'destino_recurso',
            'destino_label',
            'zona_llamado',
            'updated_at',
        ]
    )
    return llegada


CODIGO_SALA_EXTRACCION = 'sala-extraccion'


def puesto_placeholder_recepcion() -> PuestoRecepcion:
    """Puesto genérico al anunciarse (antes de que una secretaria llame)."""
    p = (
        PuestoRecepcion.objects.filter(activo=True)
        .exclude(codigo=CODIGO_SALA_EXTRACCION)
        .order_by('-es_fallback', 'orden', 'id')
        .first()
    )
    if not p:
        raise ValidationError({'puesto': 'No hay puestos de recepción activos.'})
    return p


def cobertura_hoy(*, usuario, fecha=None) -> CoberturaRecepcion | None:
    fecha = fecha or timezone.localdate()
    return (
        CoberturaRecepcion.objects.select_related('puesto')
        .filter(usuario=usuario, fecha=fecha)
        .first()
    )


def guardar_cobertura_hoy(
    *,
    usuario,
    puesto_id: int,
    tipos: list,
    sede: str | None = None,
    fecha=None,
) -> CoberturaRecepcion:
    fecha = fecha or timezone.localdate()
    try:
        puesto = PuestoRecepcion.objects.get(pk=puesto_id, activo=True)
    except PuestoRecepcion.DoesNotExist:
        raise ValidationError({'puesto_id': 'Puesto inválido.'})
    if puesto.codigo == CODIGO_SALA_EXTRACCION:
        raise ValidationError(
            {'puesto_id': 'Sala de extracción es solo para laboratorio.'}
        )
    tipos_limpios = []
    for t in tipos or []:
        t = str(t).strip().upper()
        if t in TIPOS_COBERTURA_SECRETARIA and t not in tipos_limpios:
            tipos_limpios.append(t)
    if not tipos_limpios:
        raise ValidationError({'tipos': 'Elegí al menos un tipo de atención.'})
    sede_val = (sede or '').strip().upper() or None
    if sede_val and sede_val not in ('CEHTA', 'ICPL'):
        raise ValidationError({'sede': 'Sede inválida.'})
    obj, _ = CoberturaRecepcion.objects.update_or_create(
        usuario=usuario,
        fecha=fecha,
        defaults={
            'puesto': puesto,
            'tipos': tipos_limpios,
            'sede': sede_val,
        },
    )
    return obj


def puesto_sala_extraccion() -> PuestoRecepcion:
    """Puesto dedicado a cola L (laboratorio)."""
    puesto = PuestoRecepcion.objects.filter(codigo=CODIGO_SALA_EXTRACCION, activo=True).first()
    if puesto:
        return puesto
    # Fallback: resolver por regla EXTRACCION
    r = resolver_puesto(ContextoRuteo(tipo_actividad='EXTRACCION'))
    return r.puesto


def _asegurar_puesto_extraccion(llegada: LlegadaRecepcion) -> LlegadaRecepcion:
    sala = puesto_sala_extraccion()
    if llegada.puesto_id != sala.id:
        llegada.puesto = sala
    return llegada


@transaction.atomic
def llamar_paciente(llegada: LlegadaRecepcion, *, user=None) -> LlegadaRecepcion:
    from .permissions import es_laboratorio_recepcion, es_medico_recepcion

    llegada = LlegadaRecepcion.objects.select_for_update().get(pk=llegada.pk)
    if llegada.estado_flujo not in (
        LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION,
        LlegadaRecepcion.EstadoFlujo.EN_ESPERA,
        LlegadaRecepcion.EstadoFlujo.LLAMADO,
    ):
        raise ValidationError({'estado_flujo': 'No se puede llamar en este estado.'})

    es_medico = bool(user and es_medico_recepcion(user))
    es_lab = bool(user and es_laboratorio_recepcion(user))

    # Médico: solo tras check-in administrativo (cola clínica). Sin cobertura.
    if es_medico:
        en_cola_clinica = llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.EN_ESPERA or (
            llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.LLAMADO
            and (llegada.zona_llamado or '') == 'MEDICO'
        )
        if not en_cola_clinica:
            raise ValidationError(
                {
                    'estado_flujo': (
                        'El paciente aún está en recepción. Esperá el check-in administrativo.'
                    )
                }
            )
        zona = 'MEDICO'
        llegada.estado_flujo = LlegadaRecepcion.EstadoFlujo.LLAMADO
        llegada.llamado_en = timezone.now()
        llegada.zona_llamado = zona
        if llegada.turno_id and llegada.turno and llegada.turno.recurso_id:
            llegada.destino_recurso_id = llegada.turno.recurso_id
            llegada.destino_label = llegada.turno.recurso.nombre
        elif llegada.destino_label:
            pass
        else:
            llegada.destino_label = 'Consultorio'
        llegada.save(
            update_fields=[
                'estado_flujo',
                'llamado_en',
                'zona_llamado',
                'destino_recurso',
                'destino_label',
                'updated_at',
            ]
        )
        try:
            from .push_llamado import enviar_push_llamado

            enviar_push_llamado(llegada)
        except Exception:
            pass
        return llegada

    # Zona TV: recepción (o sala extracción para L).
    if llegada.tipo_actividad == LlegadaRecepcion.TipoActividad.EXTRACCION or es_lab:
        zona = 'RECEPCION'
    elif llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.EN_ESPERA:
        # No debería llamar secretaría en cola clínica; por seguridad no reabrir recepción.
        raise ValidationError(
            {'estado_flujo': 'Este paciente ya está en la cola del médico.'}
        )
    elif (
        llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.LLAMADO
        and (llegada.zona_llamado or '') == 'MEDICO'
    ):
        raise ValidationError(
            {'estado_flujo': 'Este paciente ya está en la cola del médico.'}
        )
    else:
        zona = 'RECEPCION'

    llegada.estado_flujo = LlegadaRecepcion.EstadoFlujo.LLAMADO
    llegada.llamado_en = timezone.now()
    llegada.zona_llamado = zona
    if llegada.tipo_actividad == LlegadaRecepcion.TipoActividad.EXTRACCION:
        llegada = _asegurar_puesto_extraccion(llegada)
        llegada.destino_label = llegada.puesto.label_publico
    else:
        # Secretaría: destino = ventanilla de su cobertura del día.
        if user is not None:
            cov = cobertura_hoy(usuario=user)
            if not cov:
                raise ValidationError(
                    {
                        'cobertura': (
                            'Configurá tu cobertura de hoy (puesto y tipos) antes de llamar.'
                        )
                    }
                )
            if llegada.tipo_actividad not in (cov.tipos or []):
                raise ValidationError(
                    {
                        'cobertura': (
                            f'Hoy no atendés {llegada.tipo_actividad}. '
                            'Actualizá tu cobertura o pedile a otra secretaria.'
                        )
                    }
                )
            llegada.puesto = cov.puesto
            llegada.destino_label = cov.puesto.label_publico
        else:
            llegada.destino_label = llegada.puesto.label_publico
    llegada.save(
        update_fields=[
            'estado_flujo',
            'llamado_en',
            'zona_llamado',
            'puesto',
            'destino_recurso',
            'destino_label',
            'updated_at',
        ]
    )
    try:
        from .push_llamado import enviar_push_llamado

        enviar_push_llamado(llegada)
    except Exception:
        pass
    return llegada


@transaction.atomic
def marcar_en_atencion(llegada: LlegadaRecepcion) -> LlegadaRecepcion:
    llegada = LlegadaRecepcion.objects.select_for_update().get(pk=llegada.pk)
    llegada.estado_flujo = LlegadaRecepcion.EstadoFlujo.EN_ATENCION
    llegada.save(update_fields=['estado_flujo', 'updated_at'])
    return llegada


@transaction.atomic
def marcar_atendido(llegada: LlegadaRecepcion) -> LlegadaRecepcion:
    llegada = LlegadaRecepcion.objects.select_for_update().get(pk=llegada.pk)
    llegada.estado_flujo = LlegadaRecepcion.EstadoFlujo.ATENDIDO
    llegada.save(update_fields=['estado_flujo', 'updated_at'])
    return llegada


def marcar_atendido_por_turno_id(
    turno_id: int, *, fecha=None
) -> LlegadaRecepcion | None:
    """
    Tras cerrar consulta: pasa a ATENDIDO la llegada activa del turno (hoy).
    Idempotente si ya está ATENDIDO. No toca CANCELADO / NO_ASISTIO.
    """
    from django.utils import timezone as dj_tz

    if not turno_id:
        return None
    dia = fecha or dj_tz.localdate()
    llegada = (
        LlegadaRecepcion.objects.filter(turno_id=turno_id, fecha=dia)
        .exclude(
            estado_flujo__in=[
                LlegadaRecepcion.EstadoFlujo.CANCELADO,
                LlegadaRecepcion.EstadoFlujo.NO_ASISTIO,
            ]
        )
        .order_by('-id')
        .first()
    )
    if not llegada:
        return None
    if llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.ATENDIDO:
        return llegada
    return marcar_atendido(llegada)


@transaction.atomic
def marcar_no_asistio(llegada: LlegadaRecepcion) -> LlegadaRecepcion:
    llegada = LlegadaRecepcion.objects.select_for_update().get(pk=llegada.pk)
    llegada.estado_flujo = LlegadaRecepcion.EstadoFlujo.NO_ASISTIO
    llegada.save(update_fields=['estado_flujo', 'updated_at'])
    return llegada


@transaction.atomic
def paciente_ya_voy(llegada: LlegadaRecepcion) -> LlegadaRecepcion:
    """
    Paciente confirma el llamado («Ya voy»).
    Solo aplica si está LLAMADO. No marca ATENDIDO (eso es secretaría/médico).
    - Zona MEDICO: EN_ATENCION (sale del destacado TV consultorio).
    - Zona RECEPCION / lab: queda en LLAMADO (solo acusa recibo en el celular);
      secretaría sigue operando en el tablero.
    """
    llegada = LlegadaRecepcion.objects.select_for_update().get(pk=llegada.pk)
    if llegada.estado_flujo != LlegadaRecepcion.EstadoFlujo.LLAMADO:
        return llegada
    if (llegada.zona_llamado or '') == 'MEDICO':
        llegada.estado_flujo = LlegadaRecepcion.EstadoFlujo.EN_ATENCION
        llegada.save(update_fields=['estado_flujo', 'updated_at'])
    return llegada


def nombre_publico_paciente(paciente) -> str:
    ap = (getattr(paciente, 'apellido', None) or '').strip().upper()
    no = (getattr(paciente, 'nombre', None) or '').strip()
    inicial = (no[:1] + '.') if no else ''
    if ap and inicial:
        return f'{ap}, {inicial}'
    return ap or inicial or 'PACIENTE'


def evaluar_prioridad_horario(*, turno=None, ahora=None) -> dict:
    """
    Prioridad clara para kiosco / recepción según horario del turno.

    Ventana EN_HORARIO: desde 15 min antes hasta 20 min después.
    """
    if turno is None:
        return {
            'codigo': 'SIN_TURNO',
            'label': 'Sin turno',
            'detalle': 'Te van a ubicar en el orden de llegada.',
            'es_prioridad': False,
            'hora_turno': None,
            'minutos': None,
        }

    ahora = ahora or timezone.now()
    inicio = timezone.localtime(turno.fecha_hora_inicio)
    minutos = int((inicio - ahora).total_seconds() // 60)
    hora = inicio.strftime('%H:%M')

    if -20 <= minutos <= 15:
        return {
            'codigo': 'EN_HORARIO',
            'label': 'Prioridad por horario',
            'detalle': f'Tu turno es a las {hora}. Tenés prioridad ahora.',
            'es_prioridad': True,
            'hora_turno': hora,
            'minutos': minutos,
        }
    if minutos > 15:
        return {
            'codigo': 'ANTICIPADO',
            'label': 'Turno más tarde',
            'detalle': (
                f'Tu turno es a las {hora} (en {minutos} min). '
                'Te van a llamar cerca de esa hora.'
            ),
            'es_prioridad': False,
            'hora_turno': hora,
            'minutos': minutos,
        }
    tarde = abs(minutos)
    return {
        'codigo': 'TARDE',
        'label': 'Fuera de horario',
        'detalle': (
            f'Tu turno era a las {hora} (hace {tarde} min). '
            'Recepción te acomodará en la cola.'
        ),
        'es_prioridad': False,
        'hora_turno': hora,
        'minutos': minutos,
    }
