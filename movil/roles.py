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

ESTADOS_INFORME_PDF = frozenset({'FINALIZADO', 'INFORMADO_PARCIAL'})
ESTADOS_INFORME_LISTADO = frozenset({'FINALIZADO', 'INFORMADO_PARCIAL'})
ESTADOS_BIOQUIMICO_TRABAJO = frozenset({
    'EN_PROCESO',
    'INFORMADO_PARCIAL',
    'LISTO_PARA_VALIDAR',
    'FINALIZADO',
})
