"""Roles y helpers de la API móvil."""

from __future__ import annotations

ROLES_MOVIL = frozenset({
    'paciente',
    'medico',
    'secretaria',
    'laboratorio',
    'bioquimico',
})

ROLES_MOVIL_TURNOS = frozenset({'paciente', 'medico'})

ROLES_MOVIL_INFORMES = frozenset({
    'paciente',
    'medico',
    'secretaria',
    'laboratorio',
    'bioquimico',
})

ROLES_MOVIL_VALIDAR = frozenset({'bioquimico'})

ROLES_MOVIL_PEDIR_LAB = frozenset({'medico'})

# PDF solo tras validación; el listado sí incluye informe parcial (solo pantalla).
ESTADOS_INFORME_PDF = frozenset({'FINALIZADO'})
ESTADOS_INFORME_LISTADO = frozenset({'FINALIZADO', 'INFORMADO_PARCIAL'})
ESTADOS_BIOQUIMICO_TRABAJO = frozenset({
    'EN_PROCESO',
    'INFORMADO_PARCIAL',
    'LISTO_PARA_VALIDAR',
    'FINALIZADO',
})

# Chips de contexto en la app → origen_solicitud LIMS
CONTEXTO_A_ORIGEN = {
    'GUARDIA': 'GUARDIA',
    'AMBULATORIO': 'AMBULATORIO_CEHTA',
    'INTERNACION': 'INTERNACION_UCE',
}

# Reexport para callers móviles
from medicos.ambito import (  # noqa: E402
    CONTEXTOS_LAB_COMPLETOS,
    CONTEXTOS_LAB_SOLO_AMBULATORIO,
    contextos_lab_permitidos,
    contextos_lab_para_api,
    contexto_lab_permitido,
)
