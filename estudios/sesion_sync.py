"""
Sincronización SesionActividad ↔ espejo legacy EstudioComplementario.turno (A3/A4).

- SoT de turno por sesión: SesionActividad.turno (vínculos históricos nunca se borran).
- Monosesión: estudio.turno siempre = sesión #1.turno (contrato A3).
- Multisesión: espejo D5 — 0 vigentes → null; 1 → ese turno; >1 → null.
- fecha_realizacion / realizado_por: dual-write mono en sesión #1 (A3).
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from estudios.actividad_rules import MSG_SESION_ID_REQUERIDO, MSG_SESION_INVALIDA
from estudios.models import EstudioComplementario, SesionActividad

_TURNOS_VIGENTES = frozenset({'RESERVADO', 'CONFIRMADO'})


def _estado_desde_estudio(estudio: EstudioComplementario) -> str:
    if estudio.estado == EstudioComplementario.Estado.ANULADO:
        return SesionActividad.EstadoSesion.CANCELADA
    if estudio.estado in (
        EstudioComplementario.Estado.REALIZADO,
        EstudioComplementario.Estado.INFORMADO,
        EstudioComplementario.Estado.ENTREGADO,
    ):
        return SesionActividad.EstadoSesion.REALIZADA
    if estudio.turno_id:
        return SesionActividad.EstadoSesion.PROGRAMADA
    return SesionActividad.EstadoSesion.PENDIENTE


def asegurar_sesion_uno(estudio: EstudioComplementario) -> SesionActividad:
    """Obtiene o crea la sesión #1 (monosesión operativa A3)."""
    sesion, _ = SesionActividad.objects.get_or_create(
        estudio=estudio,
        numero_sesion=1,
        defaults={
            'turno_id': estudio.turno_id,
            'fecha_realizacion': estudio.fecha_realizacion,
            'realizado_por_id': estudio.realizado_por_id,
            'estado_sesion': _estado_desde_estudio(estudio),
        },
    )
    return sesion


def resolver_sesion_para_asignacion(
    estudio: EstudioComplementario,
    sesion_id,
) -> SesionActividad:
    """
    Resuelve la sesión target. Caller debe haber hecho select_for_update del estudio.
    Devuelve sesión con select_for_update.
    """
    multi = bool(estudio.permite_multi_sesion)

    if multi:
        if sesion_id is None:
            raise ValidationError({'sesion_id': MSG_SESION_ID_REQUERIDO})
        sesion = (
            SesionActividad.objects.select_for_update()
            .filter(pk=sesion_id, estudio_id=estudio.pk)
            .first()
        )
        if sesion is None:
            raise ValidationError({'sesion_id': MSG_SESION_INVALIDA})
        return sesion

    # Monosesión: sesión #1 por numero_sesion; comparar sesion_id con PK real.
    sesion = asegurar_sesion_uno(estudio)
    sesion = (
        SesionActividad.objects.select_for_update()
        .filter(pk=sesion.pk)
        .first()
    )
    if sesion_id is not None and int(sesion_id) != sesion.pk:
        raise ValidationError({'sesion_id': MSG_SESION_INVALIDA})
    return sesion


def _turno_id_espejo_multi(estudio_id: int):
    """D5: 0 → None; 1 vigente → ese; >1 → None. No toca FKs de sesión."""
    qs = (
        SesionActividad.objects.filter(estudio_id=estudio_id, turno_id__isnull=False)
        .select_related('turno')
    )
    vigentes = [
        s.turno_id
        for s in qs
        if s.turno_id and getattr(s.turno, 'estado', None) in _TURNOS_VIGENTES
    ]
    if len(vigentes) == 1:
        return vigentes[0]
    return None


@transaction.atomic
def sincronizar_espejo_turno(estudio: EstudioComplementario) -> SesionActividad | None:
    """
    Mono (A3): estudio.turno_id := sesión#1.turno_id siempre.
    Multi (A4 D5): 0/1/>1 vigentes → null / ese / null. No borra sesión.turno.
    """
    if estudio.permite_multi_sesion:
        nuevo = _turno_id_espejo_multi(estudio.pk)
        if estudio.turno_id != nuevo:
            EstudioComplementario.objects.filter(pk=estudio.pk).update(turno_id=nuevo)
            estudio.turno_id = nuevo
        return None

    sesion = (
        SesionActividad.objects.select_for_update()
        .filter(estudio_id=estudio.pk, numero_sesion=1)
        .first()
    )
    if sesion is None:
        sesion = asegurar_sesion_uno(estudio)
        sesion = (
            SesionActividad.objects.select_for_update()
            .filter(pk=sesion.pk)
            .first()
        )
    if estudio.turno_id != sesion.turno_id:
        EstudioComplementario.objects.filter(pk=estudio.pk).update(turno_id=sesion.turno_id)
        estudio.turno_id = sesion.turno_id
    return sesion


def sync_realizar_sesion_uno(
    estudio: EstudioComplementario,
    *,
    fecha_realizacion,
    realizado_por,
) -> SesionActividad:
    """Dual-write realización a sesión #1 (solo monosesión operativa)."""
    sesion = asegurar_sesion_uno(estudio)
    sesion.fecha_realizacion = fecha_realizacion
    sesion.realizado_por = realizado_por
    sesion.estado_sesion = SesionActividad.EstadoSesion.REALIZADA
    sesion.save(
        update_fields=[
            'fecha_realizacion',
            'realizado_por',
            'estado_sesion',
            'updated_at',
        ]
    )
    sincronizar_espejo_turno(estudio)
    return sesion


def sync_asignar_turno_a_sesion(
    estudio: EstudioComplementario,
    sesion: SesionActividad,
    turno,
) -> SesionActividad:
    """Asigna turno a la sesión dada y sincroniza espejo (misma TX del caller)."""
    sesion.turno = turno
    if sesion.estado_sesion == SesionActividad.EstadoSesion.PENDIENTE:
        sesion.estado_sesion = SesionActividad.EstadoSesion.PROGRAMADA
    sesion.save(update_fields=['turno', 'estado_sesion', 'updated_at'])
    sincronizar_espejo_turno(estudio)
    return sesion


def sync_asignar_turno_sesion_uno(
    estudio: EstudioComplementario,
    turno,
) -> SesionActividad:
    """Compat A3: asigna a sesión #1."""
    sesion = asegurar_sesion_uno(estudio)
    sesion = SesionActividad.objects.select_for_update().filter(pk=sesion.pk).first()
    return sync_asignar_turno_a_sesion(estudio, sesion, turno)


def sync_anular_sesion_uno(estudio: EstudioComplementario) -> SesionActividad:
    """Marca sesión #1 CANCELADA; conserva turno histórico."""
    sesion = asegurar_sesion_uno(estudio)
    sesion.estado_sesion = SesionActividad.EstadoSesion.CANCELADA
    sesion.save(update_fields=['estado_sesion', 'updated_at'])
    sincronizar_espejo_turno(estudio)
    return sesion


def crear_sesion_inicial_post_alta(estudio: EstudioComplementario) -> SesionActividad:
    """Alta: sesión #1 alineada al estado del estudio (misma TX)."""
    return asegurar_sesion_uno(estudio)


def backfill_sesiones_desde_estudios(*, force: bool = False) -> dict:
    """Idempotente: crea sesión #1 por estudio sin sobrescribir existentes."""
    creadas = 0
    omitidas = 0
    for estudio in EstudioComplementario.objects.all().iterator():
        exists = SesionActividad.objects.filter(estudio_id=estudio.pk, numero_sesion=1).exists()
        if exists:
            omitidas += 1
            continue
        SesionActividad.objects.create(
            estudio=estudio,
            numero_sesion=1,
            turno_id=estudio.turno_id,
            fecha_realizacion=estudio.fecha_realizacion,
            realizado_por_id=estudio.realizado_por_id,
            estado_sesion=_estado_desde_estudio(estudio),
        )
        creadas += 1
    return {'creadas': creadas, 'omitidas': omitidas, 'at': timezone.now().isoformat()}
