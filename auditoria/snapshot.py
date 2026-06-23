"""
Serialización conservadora para auditoría — evita payloads binarios grandes.

- FileField / ImageField: sólo ``<file:nombre>`` o marcador corto.
- BinaryField: ``<binary>`` sin raw bytes.
- FK: valores escalares usando ``field.attname`` (p.ej. ``medico_id``).
- M2M: marcador textual, sin expandir colecciones.
"""

from __future__ import annotations

import json

from django.core.exceptions import ValidationError
from django.db import models


_MAX_RECURSION = 48
_JSON_MAX_BYTES_DEFAULT = 400_000
_LEAF_STRING_MAX_CHARS = 8_192

# Modelos con FileField clínico: no persistir ruta ni nombre de archivo en auditoría (C6.2).
_CLINICAL_FILE_MODEL_LABELS = frozenset({
    'archivos_medicos.ArchivoMedico',
    'emr.Documento',
    'estudios.InformeEstudioComplementario',
})

# Campos de texto clínico no deben persistirse completos en auditoría (C6.4.1).
_REDACT_LONG_TEXT_FIELDS = frozenset({
    ('estudios.InformeEstudioComplementario', 'texto'),
    ('laboratorio.Muestra', 'observaciones'),
    ('laboratorio.Muestra', 'motivo_rechazo'),
    ('laboratorio.Muestra', 'codigo_barra'),
    ('laboratorio.EventoMuestra', 'observaciones'),
})

# Resultado de laboratorio: valores y referencias clínicas (LIMS B2-A).
_REDACT_RESULTADO_EXAMEN_FIELDS = frozenset({
    'valor_obtenido',
    'valor_numerico',
    'unidad',
    'rango_referencia_snapshot',
    'rango_min_snapshot',
    'rango_max_snapshot',
    'valor_critico_min_snapshot',
    'valor_critico_max_snapshot',
    'observaciones',
})

_CLINICAL_VALUE_PLACEHOLDER = '<valor clínico redactado>'
_CLINICAL_TEXT_REDACTED = '<texto clínico redactado>'
_MICRO_RESULT_PLACEHOLDER = '<resultado microbiológico redactado>'
_SENSITIVE_DATA_PLACEHOLDER = '<dato sensible redactado>'

# Campos demográficos / identificadores — redacción global por nombre de campo.
_GLOBAL_PII_FIELD_NAMES = frozenset({
    'dni',
    'documento',
    'documento_numero',
    'telefono',
    'email',
    'direccion',
    'fecha_nacimiento',
    'obra_social',
    'numero_afiliado',
    'num_afiliado',
    'afiliado',
})

# Campos de texto clínico — redacción global por nombre de campo (modelos clínicos).
_GLOBAL_CLINICAL_TEXT_FIELD_NAMES = frozenset({
    'anamnesis',
    'examen_fisico',
    'diagnostico_presuntivo',
    'diagnostico_definitivo',
    'diagnostico_ingreso',
    'diagnostico_preoperatorio',
    'diagnostico_postoperatorio',
    'plan_manejo',
    'plan_tratamiento',
    'notas_medicas',
    'motivo_consulta_detalle',
    'motivo_ingreso',
    'informe_medico',
    'hallazgos',
    'hallazgos_operatorios',
    'protocolo_quirurgico',
    'medicacion_actual',
    'alergias',
    'descripcion_tratamiento',
    'nombre_diagnostico',
    'descripcion_diagnostico',
    'descripcion',
    'contenido',
    'texto',
    'observaciones',
    'observaciones_generales',
    'observaciones_medicas',
    'complicaciones',
})

# Prefijos de nombre de campo que indican texto clínico libre.
_CLINICAL_FIELD_NAME_PREFIXES = (
    'antecedentes_',
    'motivo_',
    'diagnostico_',
    'notas_',
)

# Redacción por modelo — PII / demografía (incluye nombre/apellido de paciente).
_REDACT_MODEL_FIELDS_PII: dict[str, frozenset[str]] = {
    'pacientes.Paciente': frozenset({
        'nombre',
        'apellido',
        'dni',
        'fecha_nacimiento',
        'telefono',
        'email',
        'direccion',
        'obra_social',
        'numero_afiliado',
        'antecedentes_personales',
        'antecedentes_familiares',
        'observaciones',
    }),
}

# Redacción por modelo — texto clínico adicional no cubierto por globales.
_REDACT_MODEL_FIELDS_CLINICAL: dict[str, frozenset[str]] = {
    'historias_clinicas.Consulta': frozenset({
        'motivo_consulta_detalle',
        'anamnesis',
        'examen_fisico',
        'diagnostico_presuntivo',
        'plan_manejo',
        'notas_medicas',
    }),
    'turnos.Atencion': frozenset({'observaciones_generales'}),
    'turnos.ConsultaAmbulatoria': frozenset({
        'anamnesis',
        'examen_fisico',
        'diagnostico_presuntivo',
        'plan_manejo',
        'antecedentes_relevantes',
        'alergias',
        'medicacion_actual',
        'diagnostico_definitivo',
        'observaciones_medicas',
    }),
    'solicitudes.Solicitud': frozenset({'descripcion', 'observaciones'}),
}

# Texto clínico / observaciones microbiológicas — no persistir en snapshot genérico (LIMS B3-audit).
_REDACT_MICRO_TEXT_FIELDS = frozenset({
    ('laboratorio.EstudioMicrobiologia', 'observaciones'),
    ('laboratorio.EstudioMicrobiologia', 'motivo_cancelacion'),
    ('laboratorio.SiembraMicrobiologia', 'observaciones'),
    ('laboratorio.LecturaCultivo', 'descripcion_colonias'),
    ('laboratorio.LecturaCultivo', 'tincion_gram'),
    ('laboratorio.LecturaCultivo', 'observaciones'),
    ('laboratorio.AisladoMicrobiologico', 'descripcion'),
    ('laboratorio.AisladoMicrobiologico', 'cantidad'),
    ('laboratorio.AisladoMicrobiologico', 'observaciones'),
    ('laboratorio.AisladoMicrobiologico', 'motivo_descarte'),
    ('laboratorio.IdentificacionMicroorganismo', 'metodo'),
    ('laboratorio.IdentificacionMicroorganismo', 'resultado'),
    ('laboratorio.IdentificacionMicroorganismo', 'observaciones'),
    ('laboratorio.Antibiograma', 'observaciones'),
    ('laboratorio.Antibiograma', 'motivo_cancelacion'),
    ('laboratorio.Antibiograma', 'metodo'),
    ('laboratorio.ResultadoAntibiotico', 'observaciones'),
    ('laboratorio.InformeMicrobiologia', 'texto'),
    ('laboratorio.InformeMicrobiologia', 'observaciones'),
    ('laboratorio.InformeMicrobiologia', 'motivo_anulacion'),
})

# CIM/diámetro/interpretación S/I/R y valores numéricos microbiológicos sensibles.
_REDACT_MICRO_RESULT_FIELDS = frozenset({
    ('laboratorio.ResultadoAntibiotico', 'halo_mm'),
    ('laboratorio.ResultadoAntibiotico', 'interpretacion'),
    ('laboratorio.ResultadoAntibiotico', 'mic'),
    ('laboratorio.IdentificacionMicroorganismo', 'confianza'),
})


class SnapshotTooLarge(ValidationError):
    """Snapshot rechazado por superar tamaño tras serialización mínima."""

    pass


def _snapshot_redaction_placeholder(label: str, field_name: str) -> str | None:
    """Devuelve placeholder si el campo debe redactarse en auditoría genérica."""
    if (label, field_name) in _REDACT_LONG_TEXT_FIELDS:
        return _CLINICAL_TEXT_REDACTED
    if (label, field_name) in _REDACT_MICRO_TEXT_FIELDS:
        return _CLINICAL_TEXT_REDACTED
    if (label, field_name) in _REDACT_MICRO_RESULT_FIELDS:
        return _MICRO_RESULT_PLACEHOLDER

    model_pii = _REDACT_MODEL_FIELDS_PII.get(label)
    if model_pii and field_name in model_pii:
        return _SENSITIVE_DATA_PLACEHOLDER

    model_clinical = _REDACT_MODEL_FIELDS_CLINICAL.get(label)
    if model_clinical and field_name in model_clinical:
        return _CLINICAL_TEXT_REDACTED

    if field_name in _GLOBAL_PII_FIELD_NAMES:
        return _SENSITIVE_DATA_PLACEHOLDER

    if field_name in _GLOBAL_CLINICAL_TEXT_FIELD_NAMES:
        return _CLINICAL_TEXT_REDACTED

    for prefix in _CLINICAL_FIELD_NAME_PREFIXES:
        if field_name.startswith(prefix):
            return _CLINICAL_TEXT_REDACTED

    return None


def safe_entity_repr(instance) -> str:
    """Representación técnica sin PHI para ``AuditEvent.entity_repr``."""
    if instance is None:
        return ""

    label = getattr(getattr(instance, '_meta', None), 'label', '')
    pk = getattr(instance, 'pk', None)

    if label == 'pacientes.Paciente':
        return f'Paciente #{pk}'[:255]
    if label == 'historias_clinicas.Consulta':
        return f'Consulta #{pk}'[:255]
    if label == 'turnos.Atencion':
        estado = getattr(instance, 'estado_clinico', '') or ''
        return f'Atención #{pk} ({estado})'[:255]
    if label == 'solicitudes.Solicitud':
        tipo = getattr(instance, 'tipo_solicitud', '') or ''
        estado = getattr(instance, 'estado', '') or ''
        return f'Solicitud #{pk} ({tipo}/{estado})'[:255]
    if label == 'turnos.Turno':
        estado = getattr(instance, 'estado', '') or ''
        return f'Turno #{pk} ({estado})'[:255]

    class_name = instance.__class__.__name__
    return f'{class_name} #{pk}'[:255] if pk is not None else class_name[:255]


def _json_bytes(obj: object) -> int:
    try:
        return len(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        return _JSON_MAX_BYTES_DEFAULT + 1


def safe_model_snapshot(
    instance,
    *,
    include_nulls: bool = False,
    max_json_bytes: int = _JSON_MAX_BYTES_DEFAULT,
) -> dict:
    """Representación JSON-serializable y acotada de un modelo Django."""
    if instance is None:
        return {}

    opts = getattr(instance, "_meta", None)
    if opts is None:
        return {}

    recursion_guard = [_MAX_RECURSION]

    def to_jsonable(value):  # noqa: ANN001
        recursion_guard[0] -= 1
        if recursion_guard[0] <= 0:
            return "<max depth>"

        if value is None:
            return None
        if isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            if len(value) > _LEAF_STRING_MAX_CHARS:
                return value[: _LEAF_STRING_MAX_CHARS // 2] + "...<truncado>"
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            return "<binary>"
        if isinstance(value, dict):
            return {str(k): to_jsonable(v) for k, v in list(value.items())[:200]}
        if isinstance(value, (list, tuple, set, frozenset)):
            out = [to_jsonable(v) for v in value]
            return out[:500] if len(out) > 500 else out
        try:
            if hasattr(value, "isoformat"):
                return value.isoformat()
        except Exception:
            pass
        return repr(value)[:2000]

    state = {}

    for field in getattr(opts, "concrete_fields", ()):
        # Evitar puntero de herencia multi-tabla; no omitir AutoField/PK normal.
        if getattr(field, "auto_created", False) and getattr(getattr(field, "remote_field", None), "parent_link", False):
            continue

        if isinstance(field, (models.FileField, models.ImageField)):
            val = getattr(instance, field.name, None)
            redact_name = getattr(opts, 'label', '') in _CLINICAL_FILE_MODEL_LABELS
            if val:
                if redact_name:
                    state[field.name] = "<file presente>"
                elif getattr(val, "name", None):
                    state[field.name] = f"<file: {getattr(val, 'name', '?')}>"
                else:
                    state[field.name] = "<file presente>"
            elif include_nulls:
                state[field.name] = None
            continue

        if isinstance(field, models.BinaryField):
            raw = getattr(instance, field.name, None)
            if raw:
                state[field.name] = "<binary>"
            elif include_nulls:
                state[field.name] = None
            continue

        if getattr(field, "many_to_many", False):
            continue

        if field.is_relation and field.many_to_one:
            val = getattr(instance, field.attname, None)
            if val is not None:
                state[field.attname] = val
            elif include_nulls:
                state[field.attname] = None
            continue

        value = getattr(instance, field.attname, None)

        if value is None and not include_nulls:
            continue

        label = getattr(opts, 'label', '')

        if label == 'laboratorio.ResultadoExamen' and field.name in _REDACT_RESULTADO_EXAMEN_FIELDS:
            if value is not None and value != '':
                state[field.name] = _CLINICAL_VALUE_PLACEHOLDER
            elif include_nulls:
                state[field.name] = None
            continue

        placeholder = _snapshot_redaction_placeholder(label, field.name)
        if placeholder is not None:
            if value is not None and value != '':
                state[field.name] = placeholder
            elif include_nulls:
                state[field.name] = None
            continue

        state[field.name] = to_jsonable(value)

    for mf in getattr(opts, "many_to_many", ()):
        try:
            rel = mf.remote_field.model
            label = getattr(rel, "__name__", "?")
        except Exception:
            label = "?"
        state[mf.name + "_m2m"] = f"<many_to_many:{label} no serializado>"

    out = {k: v for k, v in state.items() if include_nulls or v is not None}

    if _json_bytes(out) > max_json_bytes:
        minimal = {
            "__snapshot_error__": "payload demasiado grande tras serialización",
            "model": opts.label,
            "pk": getattr(instance, "pk", None),
        }
        if _json_bytes(minimal) > max_json_bytes:
            raise SnapshotTooLarge("No se pudo acotar el snapshot al límite configurado.")
        return minimal

    return out
