"""Constantes de roles de aplicación — fuente única para permisos EMR."""

from __future__ import annotations

ROLES_ESTUDIO_COMPLEMENTARIO = frozenset({
    'kinesiologo',
    'radiologo',
    'ecografista',
    'fonoaudiologo',
})

# Operadores LIMS: técnico (laboratorio) y bioquímico.
ROLES_LIMS_OPERADOR = frozenset({
    'laboratorio',
    'bioquimico',
})

# Escritura operativa LIMS (toma, carga, recepción, catálogos editables).
ROLES_LIMS_WRITE = frozenset({
    'admin',
    *ROLES_LIMS_OPERADOR,
})

# Liberación clínica de resultados / informe (Fase A).
ROLES_LIMS_VALIDAR = frozenset({
    'admin',
    'bioquimico',
})

# Lectura operativa de pacientes y agenda (sin acceso clínico EMR completo).
ROLES_LECTURA_OPERATIVA = frozenset({
    *ROLES_LIMS_OPERADOR,
    *ROLES_ESTUDIO_COMPLEMENTARIO,
})

ROLES_AGENDA_TURNOS_LECTURA = frozenset({
    'enfermeria',
    *ROLES_LECTURA_OPERATIVA,
})

# Lectura de catálogos LIMS (exámenes, tipos de muestra, micro catálogos).
ROLES_LIMS_CATALOG_READ = frozenset({
    'admin',
    *ROLES_LIMS_OPERADOR,
    'medico',
})

# Secretaría/enfermería: bandeja LIMS restringida (pendientes + órdenes finalizadas).
ROLES_LIMS_OPERATIVA_LIMITADA = frozenset({
    'secretaria',
    'enfermeria',
})

ESTADOS_LIMS_OPERATIVA_LIMITADA = frozenset({
    'PENDIENTE',
    'FINALIZADO',
})

# Roles que no deben escalar a PHI EMR global aunque tengan is_staff=True.
ROLES_SIN_BYPASS_EMR_STAFF = frozenset({
    *ROLES_LIMS_OPERADOR,
    *ROLES_ESTUDIO_COMPLEMENTARIO,
})


def normalize_rol(user_or_str) -> str:
    if hasattr(user_or_str, 'rol'):
        return (getattr(user_or_str, 'rol', '') or '').lower()
    return (user_or_str or '').lower()


def es_rol_estudio_complementario(user_or_str) -> bool:
    return normalize_rol(user_or_str) in ROLES_ESTUDIO_COMPLEMENTARIO


def es_lectura_operativa(user_or_str) -> bool:
    return normalize_rol(user_or_str) in ROLES_LECTURA_OPERATIVA


def es_agenda_turnos_lectura(user_or_str) -> bool:
    return normalize_rol(user_or_str) in ROLES_AGENDA_TURNOS_LECTURA


def es_operador_lims(user_or_str) -> bool:
    return normalize_rol(user_or_str) in ROLES_LIMS_OPERADOR


def puede_escribir_lims(user_or_str) -> bool:
    return normalize_rol(user_or_str) in ROLES_LIMS_WRITE


def puede_validar_lims(user_or_str) -> bool:
    return normalize_rol(user_or_str) in ROLES_LIMS_VALIDAR
