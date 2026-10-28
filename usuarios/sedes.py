"""Sedes operativas CEHTA / ICPL — aislamiento sin roles nuevos.

``User.sedes`` / ``Medico.sedes`` vacíos = sin restricción (retrocompat).
Admin / superuser = sin filtro de sede.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

SEDE_CEHTA = 'CEHTA'
SEDE_ICPL = 'ICPL'
SEDES = (SEDE_CEHTA, SEDE_ICPL)
SEDE_CHOICES = (
    (SEDE_CEHTA, 'CEHTA'),
    (SEDE_ICPL, 'ICPL'),
)

# Capacidades por sede (menú + gates API). Unión si el usuario tiene varias.
SEDE_CAPACIDADES = {
    SEDE_CEHTA: {
        'guardia': False,
        'internacion': False,
        'recepcion': True,
        'agenda': True,
    },
    SEDE_ICPL: {
        'guardia': True,
        'internacion': True,
        'recepcion': True,
        'agenda': True,
    },
}

# Orígenes LIMS tipados por sede (ver laboratorio / DOC_FLUJOS_LIMS).
_ORIGENES_POR_SEDE = {
    SEDE_CEHTA: (
        'AMBULATORIO_CEHTA',
        'EXTERNO_CEHTA',
    ),
    SEDE_ICPL: (
        'AMBULATORIO_ICPL',
        'EXTERNO_ICPL',
        'GUARDIA',
        'INTERNADO',
    ),
}


def normalize_sedes(raw) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for item in raw:
        s = str(item or '').strip().upper()
        if s in SEDES and s not in out:
            out.append(s)
    return out


def sedes_efectivas(user) -> Optional[list[str]]:
    """Sedes que restringen datos. ``None`` = sin filtro (admin o sedes vacías)."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    if getattr(user, 'is_superuser', False):
        return None
    rol = (getattr(user, 'rol', '') or '').lower()
    if rol == 'admin':
        return None
    sedes = normalize_sedes(getattr(user, 'sedes', None))
    if not sedes:
        return None
    return sedes


def usuario_tiene_capacidad(user, capacidad: str) -> bool:
    """True si alguna sede del usuario habilita la capacidad (o no hay filtro)."""
    sedes = sedes_efectivas(user)
    if sedes is None:
        return True
    for sede in sedes:
        caps = SEDE_CAPACIDADES.get(sede) or {}
        if caps.get(capacidad):
            return True
    return False


def filtro_origen_lims(sedes: Optional[Sequence[str]]) -> Optional[tuple[str, ...]]:
    """Orígenes LIMS permitidos; ``None`` = no filtrar."""
    if sedes is None:
        return None
    norm = normalize_sedes(sedes)
    if not norm:
        return None
    origenes: list[str] = []
    for sede in norm:
        for o in _ORIGENES_POR_SEDE.get(sede, ()):
            if o not in origenes:
                origenes.append(o)
    return tuple(origenes)


def medico_visible_para_sedes(medico_sedes, user_sedes: Optional[Sequence[str]]) -> bool:
    """Médico con sedes vacías es visible en todas; si no, debe solapar."""
    if user_sedes is None:
        return True
    msedes = normalize_sedes(medico_sedes)
    if not msedes:
        return True
    allowed = set(normalize_sedes(user_sedes))
    return bool(allowed.intersection(msedes))


def q_medico_en_sedes(user_sedes: Optional[Sequence[str]]):
    """Q para filtrar Medico por solapamiento de sedes (Postgres ArrayField)."""
    from django.db.models import Q

    if user_sedes is None:
        return Q()
    norm = normalize_sedes(user_sedes)
    if not norm:
        return Q()
    # vacío en médico = visible; overlap con sedes del usuario
    return Q(sedes=[]) | Q(sedes__overlap=list(norm))
