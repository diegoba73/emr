"""
Origen clínico de una orden LIMS (dónde estaba el paciente al pedir análisis).
"""
from __future__ import annotations

from django.utils import timezone

# Valores persistidos en SolicitudExamen.origen_solicitud
INTERNACION_UCO = 'INTERNACION_UCO'
INTERNACION_UCE = 'INTERNACION_UCE'
GUARDIA = 'GUARDIA'
AMBULATORIO_CEHTA = 'AMBULATORIO_CEHTA'
AMBULATORIO_ICPL = 'AMBULATORIO_ICPL'
EXTERNO_CEHTA = 'EXTERNO_CEHTA'
EXTERNO_ICPL = 'EXTERNO_ICPL'

ORIGEN_CHOICES = [
    (INTERNACION_UCO, 'Internación — UCO'),
    (INTERNACION_UCE, 'Internación — UCE'),
    (GUARDIA, 'Guardia — ICPL'),
    (AMBULATORIO_CEHTA, 'Ambulatorio — CEHTA'),
    (AMBULATORIO_ICPL, 'Ambulatorio — ICPL'),
    (EXTERNO_CEHTA, 'Ambulatorio externo — CEHTA'),
    (EXTERNO_ICPL, 'Ambulatorio externo — ICPL'),
]

ORIGEN_LABELS = dict(ORIGEN_CHOICES)
ORIGENES_EXTERNOS = frozenset({EXTERNO_CEHTA, EXTERNO_ICPL})

# Migración desde valores legacy
_LEGACY_MAP = {
    'EMR': AMBULATORIO_CEHTA,
    'EXTERNO_PAPEL': EXTERNO_CEHTA,
    'GUARDIA': GUARDIA,
}


def es_origen_ambulatorio_externo(codigo: str | None) -> bool:
    return (codigo or '') in ORIGENES_EXTERNOS


def procedencia_display_externo(solicitud) -> str | None:
    """Texto de procedencia para receta externa presentada en CEHTA o ICPL."""
    origen = getattr(solicitud, 'origen_solicitud', '') or ''
    if not es_origen_ambulatorio_externo(origen):
        return None
    sede = 'CEHTA' if origen == EXTERNO_CEHTA else 'ICPL'
    medico = (getattr(solicitud, 'medico_externo_nombre', '') or '').strip()
    base = f'Receta externa — presentada en {sede}'
    return f'{base} · {medico}' if medico else base


def label_origen_solicitud(codigo: str | None) -> str:
    if not codigo:
        return '—'
    if codigo in ORIGEN_LABELS:
        return ORIGEN_LABELS[codigo]
    return _LEGACY_MAP.get(codigo, codigo)


def _sector_es_uco(sector_nombre: str) -> bool:
    n = (sector_nombre or '').upper()
    return 'UCO' in n and 'UCE' not in n


def _sector_es_uce(sector_nombre: str) -> bool:
    return 'UCE' in (sector_nombre or '').upper()


def _atencion_desde_consulta(consulta):
    if consulta is None:
        return None
    atencion = getattr(consulta, 'atencion', None)
    if atencion is not None:
        return atencion
    atencion_id = getattr(consulta, 'atencion_id', None)
    if not atencion_id:
        return None
    try:
        from turnos.models import Atencion
    except Exception:
        return None
    return Atencion.objects.filter(pk=atencion_id).first()


def _atencion_es_guardia(atencion) -> bool:
    if atencion is None:
        return False
    ctx = getattr(atencion, 'contexto_atencion', '') or ''
    if ctx == GUARDIA:
        return True
    return (getattr(atencion, 'tipo_atencion', '') or '') == GUARDIA


def _consulta_es_guardia(consulta) -> bool:
    return _atencion_es_guardia(_atencion_desde_consulta(consulta))


def procedencia_display_guardia() -> str:
    """Guardia cardiológica: único punto de atención en ICPL."""
    return 'Guardia cardiológica — ICPL'


def _recurso_es_guardia(recurso) -> bool:
    if recurso is None:
        return False
    nombre = (getattr(recurso, 'nombre', '') or '').upper()
    if 'GUARDIA' in nombre:
        return True
    turno = getattr(recurso, '_turno_guardia_ctx', None)
    if turno is not None:
        motivo = (getattr(turno, 'motivo_reserva', '') or '').upper()
        if 'GUARDIA' in motivo:
            return True
    return False


def _internacion_activa(paciente_id: int, fecha_ref=None):
    try:
        from internacion.models import Internacion
    except Exception:
        return None
    ref = fecha_ref or timezone.now()
    return (
        Internacion.objects.filter(
            paciente_id=paciente_id,
            activo=True,
            fecha_ingreso__lte=ref,
        )
        .select_related('cama__sector')
        .order_by('-fecha_ingreso')
        .first()
    )


def inferir_origen_solicitud(
    *,
    paciente_id: int,
    consulta_hc=None,
    origen_explicito: str | None = None,
    fecha_ref=None,
) -> str:
    """
    Determina el origen clínico al crear la orden.

    Prioridad:
    1. Internación activa (UCO / UCE)
    2. Consulta → atención de guardia (walk-in sin turno)
    3. Consulta → turno → recurso (guardia vs ambulatorio CEHTA/ICPL)
    4. Origen explícito del cliente (si es válido)
    5. Ambulatorio CEHTA por defecto
    """
    if origen_explicito:
        norm = normalizar_origen_solicitud(origen_explicito) or origen_explicito
        if norm in ORIGEN_LABELS and es_origen_ambulatorio_externo(norm):
            return norm

    internacion = _internacion_activa(paciente_id, fecha_ref)
    if internacion is not None:
        sector = ''
        if internacion.cama_id and internacion.cama.sector_id:
            sector = internacion.cama.sector.nombre or ''
        if _sector_es_uce(sector):
            return INTERNACION_UCE
        if _sector_es_uco(sector):
            return INTERNACION_UCO
        # Sector genérico de internación → UCE como observación/intermedia
        return INTERNACION_UCE

    consulta = consulta_hc
    if consulta is not None and _consulta_es_guardia(consulta):
        return GUARDIA

    if consulta is not None:
        turno = getattr(consulta, 'turno', None)
        recurso = getattr(turno, 'recurso', None) if turno is not None else None
        if recurso is not None and turno is not None:
            recurso._turno_guardia_ctx = turno
        if _recurso_es_guardia(recurso):
            return GUARDIA
        ubicacion = (getattr(recurso, 'ubicacion', '') or '').upper()
        if ubicacion == 'ICPL':
            return AMBULATORIO_ICPL
        if ubicacion == 'CEHTA':
            return AMBULATORIO_CEHTA

    if origen_explicito and origen_explicito in ORIGEN_LABELS:
        return origen_explicito
    if origen_explicito and origen_explicito in _LEGACY_MAP:
        return _LEGACY_MAP[origen_explicito]

    return AMBULATORIO_CEHTA


def normalizar_origen_solicitud(valor: str | None) -> str | None:
    """Acepta valores legacy en escritura y devuelve código vigente."""
    if not valor:
        return None
    if valor in ORIGEN_LABELS:
        return valor
    return _LEGACY_MAP.get(valor)
