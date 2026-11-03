"""Motor de ruteo: decide a qué puesto va una llegada."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db.models import Count, Q
from django.utils import timezone

from .models import LlegadaRecepcion, PuestoRecepcion, ReglaRuteoRecepcion


@dataclass
class ContextoRuteo:
    tipo_actividad: str
    tipo_recurso: str = ''
    recurso_id: Optional[int] = None
    medico_id: Optional[int] = None


@dataclass
class ResultadoRuteo:
    puesto: PuestoRecepcion
    mensaje: str
    regla_id: Optional[int] = None
    motivo: str = ''


def _cola_abierta_por_puesto(fecha=None) -> dict[int, int]:
    fecha = fecha or timezone.localdate()
    estados = [
        LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION,
        LlegadaRecepcion.EstadoFlujo.EN_ESPERA,
        LlegadaRecepcion.EstadoFlujo.LLAMADO,
    ]
    rows = (
        LlegadaRecepcion.objects.filter(fecha=fecha, estado_flujo__in=estados)
        .values('puesto_id')
        .annotate(n=Count('id'))
    )
    return {r['puesto_id']: r['n'] for r in rows}


def _regla_matchea(regla: ReglaRuteoRecepcion, ctx: ContextoRuteo) -> bool:
    if regla.tipo_actividad and regla.tipo_actividad != ctx.tipo_actividad:
        return False
    if regla.tipo_recurso and regla.tipo_recurso != (ctx.tipo_recurso or ''):
        return False
    if regla.recurso_id and regla.recurso_id != ctx.recurso_id:
        return False
    if regla.medico_id and regla.medico_id != ctx.medico_id:
        return False
    return True


def _elegir_menor_cola(puestos: list[PuestoRecepcion], colas: dict[int, int]) -> PuestoRecepcion:
    return min(puestos, key=lambda p: (colas.get(p.id, 0), p.orden, p.id))


def resolver_puesto(ctx: ContextoRuteo, *, fecha=None) -> ResultadoRuteo:
    """
    1) Si hay reglas que matchean el tipo → solo esos puestos (prioridad + menor cola).
       Así EXTRACCION no cae en un puesto modo TODO genérico (ej. consultas).
    2) Si no hay regla: puestos modo TODO → menor cola.
    3) Fallback: puesto es_fallback activo.
    """
    fecha = fecha or timezone.localdate()
    colas = _cola_abierta_por_puesto(fecha)
    activos = list(
        PuestoRecepcion.objects.filter(activo=True).order_by('orden', 'id')
    )
    if not activos:
        raise ValueError('No hay puestos de recepción activos. Configurá al menos uno.')

    reglas = (
        ReglaRuteoRecepcion.objects.filter(activo=True, puesto__activo=True)
        .select_related('puesto')
        .order_by('prioridad', 'id')
    )
    por_regla: list[tuple[PuestoRecepcion, Optional[int], str]] = []
    for regla in reglas:
        if not _regla_matchea(regla, ctx):
            continue
        por_regla.append((regla.puesto, regla.id, f'regla:{regla.id}'))

    candidatos = por_regla
    if not candidatos:
        for p in activos:
            if p.modo == PuestoRecepcion.Modo.TODO:
                candidatos.append((p, None, 'modo_todo'))

    # Deduplicar puestos conservando primer motivo (mejor prioridad de regla)
    vistos: dict[int, tuple[PuestoRecepcion, Optional[int], str]] = {}
    for p, rid, motivo in candidatos:
        if p.id not in vistos:
            vistos[p.id] = (p, rid, motivo)

    lista = list(vistos.values())
    if lista:
        puestos = [t[0] for t in lista]
        elegido = _elegir_menor_cola(puestos, colas)
        _, rid, motivo = vistos[elegido.id]
        return ResultadoRuteo(
            puesto=elegido,
            mensaje=f'Andá al {elegido.label_publico}.',
            regla_id=rid,
            motivo=motivo,
        )

    fallback = next((p for p in activos if p.es_fallback), None) or activos[0]
    return ResultadoRuteo(
        puesto=fallback,
        mensaje=f'Andá al {fallback.label_publico}.',
        regla_id=None,
        motivo='fallback',
    )


def tipo_actividad_desde_turno(turno) -> str:
    """Deriva tipo de actividad de un Turno (estudio vinculado / recurso)."""
    ec = getattr(turno, 'estudio_complementario', None)
    if ec is not None:
        try:
            tipo = getattr(ec, 'tipo_actividad', None) or 'ESTUDIO'
            if tipo in ('ESTUDIO', 'PROCEDIMIENTO', 'CIRUGIA'):
                return tipo
        except Exception:
            return 'ESTUDIO'
    recurso = getattr(turno, 'recurso', None)
    tipo_r = getattr(recurso, 'tipo_recurso', None) if recurso else None
    if tipo_r == 'EXTRACCIONES':
        return 'EXTRACCION'
    if tipo_r == 'QUIROFANO':
        return 'CIRUGIA'
    if tipo_r in ('SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA'):
        # Sin estudio: procedimiento genérico
        if ec is None:
            return 'PROCEDIMIENTO'
        return 'ESTUDIO'
    return 'CONSULTA'


def contexto_desde_turno(turno) -> ContextoRuteo:
    recurso = getattr(turno, 'recurso', None)
    return ContextoRuteo(
        tipo_actividad=tipo_actividad_desde_turno(turno),
        tipo_recurso=getattr(recurso, 'tipo_recurso', '') or '',
        recurso_id=getattr(turno, 'recurso_id', None),
        medico_id=getattr(turno, 'medico_id', None),
    )
