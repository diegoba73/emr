"""Reglas A2/A2b/C — tipo_actividad, snapshot y guardas de circuito.

LIMS no se toca. Multisesión sigue deshabilitada.
C: PROCEDIMIENTO (NO_QUIRURGICO). D: CIRUGIA (QUIRURGICO).
"""
from __future__ import annotations

from django.core.exceptions import ValidationError

# Campos inmutables vía create/update/PATCH genérico (A2).
CAMPOS_A2_PROTEGIDOS = (
    'tipo_actividad',
    'procedimiento_catalogo',
    'cirugia_especialidad',
    'cirugia_procedimiento',
    'cirugia_abordaje',
    'cirugia_especialidad_snapshot',
    'cirugia_procedimiento_snapshot',
    'cirugia_abordaje_snapshot',
    'clasificacion_quirurgica_snapshot',
    'permite_multi_sesion',
)

# Snapshot ↔ tipo (correspondencia exacta).
SNAPSHOT_POR_TIPO = {
    'PROCEDIMIENTO': 'NO_QUIRURGICO',
    'CIRUGIA': 'QUIRURGICO',
}

ESTADOS_POST_REALIZACION = frozenset(
    {
        'REALIZADO',
        'INFORMADO',
        'VALIDADO',
        'ENTREGADO',
        'ANULADO',
    }
)

MSG_TIPO_NO_HABILITADO = (
    'Tipo de actividad no habilitado para esta operación.'
)
MSG_CIRUGIA_NO_HABILITADA = MSG_TIPO_NO_HABILITADO  # legacy alias; D habilita CIRUGIA
MSG_SOLO_CIRCUITO_ESTUDIO = (
    'Esta acción solo aplica a indicaciones de tipo ESTUDIO, PROCEDIMIENTO o CIRUGIA.'
)
MSG_PACIENTE_IDENTIDAD = (
    'El paciente vinculado no tiene DNI y nombre completos. '
    'Completá la ficha del paciente antes de registrar la realización.'
)
MSG_PROFESIONAL_REQUERIDO = (
    'Indique el profesional responsable del procedimiento '
    '(no se asigna automáticamente a quien registra la acción).'
)
MSG_PROFESIONAL_CIRUGIA_REQUERIDO = (
    'Indique el profesional responsable de la cirugía '
    '(no se asigna automáticamente a quien registra la acción).'
)
MSG_ANESTESISTA_REQUERIDO = (
    'Indique el anestesista real (obligatorio; sin No aplica ni placeholders).'
)
MSG_DX_PRE_REQUERIDO = (
    'El diagnóstico preoperatorio es obligatorio (texto real, sin relleno).'
)
MSG_CIERRE_PROTOCOLO = (
    'El cierre requiere un protocolo completo y validado por un profesional autorizado.'
)
MSG_ENTREGA_SIN_CIERRE = (
    'La entrega de cirugía requiere un cierre administrativo vinculado '
    'a la versión validada vigente del protocolo.'
)
MSG_ATENCION_INCOMPATIBLE = (
    'Ya existe una atención vinculada incompatible con el procedimiento. '
    'Resolvé manualmente; no se crea ni elimina otra atención automáticamente.'
)
MSG_MULTI_SESION = (
    'permite_multi_sesion no puede activarse hasta completar '
    'realización e informes por sesión.'
)
MSG_SESION_INVALIDA = 'Sesión no válida para esta indicación'
MSG_MULTI_ACCION_NO_SOPORTADA = (
    'Las indicaciones multisesión no admiten esta acción hasta completar '
    'realización e informes por sesión.'
)
MSG_SESION_ID_REQUERIDO = (
    'sesion_id es obligatorio para indicaciones multisesión.'
)
MSG_CAMPOS_PROTEGIDOS = (
    'No se pueden modificar tipo_actividad, procedimiento_catalogo, '
    'campos de catálogo quirúrgico, clasificacion_quirurgica_snapshot '
    'ni permite_multi_sesion por esta vía.'
)


def snapshot_esperado_para(tipo_actividad: str) -> str | None:
    return SNAPSHOT_POR_TIPO.get(tipo_actividad)


def validar_correspondencia_actividad(
    *,
    tipo_actividad: str,
    procedimiento_catalogo=None,
    clasificacion_quirurgica_snapshot: str | None = None,
    permite_multi_sesion: bool = False,
    cirugia_especialidad=None,
    cirugia_procedimiento=None,
    cirugia_abordaje=None,
) -> None:
    """Valida invariantes de tipo/snapshot y catálogo CIRUGIA jerárquico."""
    errors: dict = {}
    snap = (clasificacion_quirurgica_snapshot or '').strip()

    if permite_multi_sesion:
        errors['permite_multi_sesion'] = MSG_MULTI_SESION

    if tipo_actividad == 'ESTUDIO':
        if procedimiento_catalogo is not None:
            errors['procedimiento_catalogo'] = (
                'ESTUDIO no admite procedimiento_catalogo.'
            )
        if cirugia_especialidad is not None or cirugia_procedimiento is not None or cirugia_abordaje is not None:
            errors['cirugia_procedimiento'] = (
                'ESTUDIO no admite catálogo quirúrgico.'
            )
        if snap:
            errors['clasificacion_quirurgica_snapshot'] = (
                'ESTUDIO no admite snapshot de clasificación quirúrgica.'
            )
    elif tipo_actividad == 'PROCEDIMIENTO':
        esperado = SNAPSHOT_POR_TIPO[tipo_actividad]
        if procedimiento_catalogo is None:
            errors['procedimiento_catalogo'] = (
                'PROCEDIMIENTO exige procedimiento_catalogo.'
            )
        else:
            clasif = getattr(
                procedimiento_catalogo, 'clasificacion_quirurgica', None
            )
            # SIN_ASIGNAR permitido (catálogo histórico); QUIRURGICO no (va a CIRUGIA).
            if clasif not in (esperado, 'SIN_ASIGNAR', None, ''):
                errors['procedimiento_catalogo'] = (
                    f'PROCEDIMIENTO exige catálogo {esperado} o SIN_ASIGNAR '
                    f'(no QUIRURGICO).'
                )
        if cirugia_especialidad is not None or cirugia_procedimiento is not None or cirugia_abordaje is not None:
            errors['cirugia_procedimiento'] = (
                'PROCEDIMIENTO no admite catálogo quirúrgico jerárquico.'
            )
        if snap != esperado:
            errors['clasificacion_quirurgica_snapshot'] = (
                f'PROCEDIMIENTO exige snapshot exactamente {esperado}.'
            )
    elif tipo_actividad == 'CIRUGIA':
        esperado = SNAPSHOT_POR_TIPO[tipo_actividad]
        if snap != esperado:
            errors['clasificacion_quirurgica_snapshot'] = (
                f'CIRUGIA exige snapshot exactamente {esperado}.'
            )
        # Nueva vía: especialidad + procedimiento (abordaje opcional).
        if cirugia_procedimiento is not None:
            if cirugia_especialidad is None:
                errors['cirugia_especialidad'] = (
                    'CIRUGIA exige cirugia_especialidad junto al procedimiento.'
                )
            elif getattr(cirugia_procedimiento, 'especialidad_id', None) != getattr(
                cirugia_especialidad, 'pk', None
            ):
                errors['cirugia_procedimiento'] = (
                    'El procedimiento no pertenece a la especialidad indicada.'
                )
            if cirugia_abordaje is not None:
                if getattr(cirugia_abordaje, 'procedimiento_id', None) != getattr(
                    cirugia_procedimiento, 'pk', None
                ):
                    errors['cirugia_abordaje'] = (
                        'El abordaje no pertenece al procedimiento indicado.'
                    )
            if procedimiento_catalogo is not None:
                errors['procedimiento_catalogo'] = (
                    'CIRUGIA con catálogo jerárquico no admite procedimiento_catalogo.'
                )
        elif procedimiento_catalogo is not None:
            # Legacy: cirugías previas con catálogo plano QUIRURGICO.
            clasif = getattr(
                procedimiento_catalogo, 'clasificacion_quirurgica', None
            )
            if clasif != esperado:
                errors['procedimiento_catalogo'] = (
                    f'CIRUGIA exige catálogo con clasificación {esperado}.'
                )
            if cirugia_abordaje is not None:
                errors['cirugia_abordaje'] = (
                    'Legacy CIRUGIA no admite abordaje sin procedimiento jerárquico.'
                )
        else:
            errors['cirugia_procedimiento'] = (
                'CIRUGIA exige especialidad y procedimiento del catálogo quirúrgico.'
            )
    else:
        errors['tipo_actividad'] = 'tipo_actividad inválido.'

    if errors:
        raise ValidationError(errors)


def assert_altas_proc_cirugia_deshabilitadas(tipo_actividad: str | None) -> None:
    """Compat A2: historicamente bloqueaba CIRUGIA. D la habilita; no-op."""
    return


def assert_circuito_estudio_legacy(estudio) -> None:
    """D: ESTUDIO, PROCEDIMIENTO y CIRUGIA en circuito del módulo."""
    tipo = getattr(estudio, 'tipo_actividad', None) or 'ESTUDIO'
    if tipo not in ('ESTUDIO', 'PROCEDIMIENTO', 'CIRUGIA'):
        raise ValidationError({'tipo_actividad': MSG_SOLO_CIRCUITO_ESTUDIO})


def assert_paciente_identidad_para_realizacion(paciente) -> None:
    dni = (getattr(paciente, 'dni', None) or '').strip()
    nombre = (getattr(paciente, 'nombre', None) or '').strip()
    apellido = (getattr(paciente, 'apellido', None) or '').strip()
    if not dni or not nombre or not apellido:
        raise ValidationError({'paciente': MSG_PACIENTE_IDENTIDAD})


def assert_no_multi_acciones_legacy(estudio) -> None:
    """A4: realización/informes/anulación legacy rechazan multi sin escribir."""
    if getattr(estudio, 'permite_multi_sesion', False):
        raise ValidationError(MSG_MULTI_ACCION_NO_SOPORTADA)


def assert_campos_protegidos_ausentes(data: dict | None, *, initial_data=None) -> None:
    """Rechaza si el cliente envió claves protegidas (aunque el valor no cambie)."""
    keys = set()
    if initial_data is not None:
        keys.update(k for k in CAMPOS_A2_PROTEGIDOS if k in initial_data)
    if data:
        keys.update(k for k in CAMPOS_A2_PROTEGIDOS if k in data)
    if keys:
        raise ValidationError({k: MSG_CAMPOS_PROTEGIDOS for k in sorted(keys)})
