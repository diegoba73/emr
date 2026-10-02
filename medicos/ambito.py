"""Ámbito de atención del médico (ambulatorio vs completo)."""

from __future__ import annotations

from medicos.models import Medico

# Contextos de pedido lab móvil / chips UI
CONTEXTO_LAB_AMBULATORIO = 'AMBULATORIO'
CONTEXTO_LAB_GUARDIA = 'GUARDIA'
CONTEXTO_LAB_INTERNACION = 'INTERNACION'

CONTEXTOS_LAB_COMPLETOS = (
    CONTEXTO_LAB_GUARDIA,
    CONTEXTO_LAB_AMBULATORIO,
    CONTEXTO_LAB_INTERNACION,
)

CONTEXTOS_LAB_SOLO_AMBULATORIO = (CONTEXTO_LAB_AMBULATORIO,)

CONTEXTOS_LAB_LABELS = {
    CONTEXTO_LAB_GUARDIA: 'Guardia',
    CONTEXTO_LAB_AMBULATORIO: 'Ambulatorio',
    CONTEXTO_LAB_INTERNACION: 'Internado',
}

# Orígenes LIMS que un médico solo-ambulatorio no puede asignar
ORIGENES_LIMS_NO_AMBULATORIO = frozenset({
    'GUARDIA',
    'INTERNACION_UCE',
    'INTERNACION_UCO',
    'INTERNACION_PISO',
})


def ambito_atencion_de(medico: Medico | None) -> str:
    if medico is None:
        return Medico.AMBITO_COMPLETO
    return getattr(medico, 'ambito_atencion', None) or Medico.AMBITO_COMPLETO


def medico_es_solo_ambulatorio(medico: Medico | None) -> bool:
    return ambito_atencion_de(medico) == Medico.AMBITO_AMBULATORIO


def medico_de_user(user) -> Medico | None:
    if user is None:
        return None
    medico = getattr(user, 'medico', None)
    if medico is not None:
        return medico
    try:
        return Medico.objects.get(user=user)
    except Medico.DoesNotExist:
        return None


def user_medico_es_solo_ambulatorio(user) -> bool:
    """True solo si el usuario tiene rol médico y ficha con ámbito AMBULATORIO."""
    if user is None:
        return False
    rol = str(getattr(user, 'rol', '') or '').lower()
    if rol != 'medico':
        return False
    return medico_es_solo_ambulatorio(medico_de_user(user))


def contextos_lab_permitidos(medico: Medico | None) -> tuple[str, ...]:
    if medico_es_solo_ambulatorio(medico):
        return CONTEXTOS_LAB_SOLO_AMBULATORIO
    return CONTEXTOS_LAB_COMPLETOS


def contextos_lab_para_api(medico: Medico | None) -> list[dict]:
    return [
        {'id': ctx, 'label': CONTEXTOS_LAB_LABELS[ctx]}
        for ctx in contextos_lab_permitidos(medico)
    ]


def contexto_lab_permitido(medico: Medico | None, contexto: str) -> bool:
    return (contexto or '').strip().upper() in contextos_lab_permitidos(medico)


def origen_lims_permitido_para_medico(medico: Medico | None, origen: str | None) -> bool:
    if not medico_es_solo_ambulatorio(medico):
        return True
    origen_u = (origen or '').strip().upper()
    if not origen_u:
        return True
    return origen_u not in ORIGENES_LIMS_NO_AMBULATORIO
