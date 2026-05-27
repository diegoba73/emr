"""
Validación coordinada ResultadoExamen ↔ Muestra (LIMS Fase B2).

Integridad referencial y estados terminales inválidos: modelo (`ResultadoExamen.clean`).
Estados operativos para **carga** de valor (RECIBIDA / EN_PROCESO): acción `cargar-resultados`.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError

from laboratorio.models_catalog import Muestra

# Muestras que nunca deben vincularse a un resultado (integridad clínica).
MUESTRA_ESTADOS_TERMINALES_SIN_RESULTADO = frozenset(
    {"RECHAZADA", "DESCARTADA", "CANCELADA"}
)

# Para cargar resultados vía API: material en laboratorio listo para procesar.
MUESTRA_ESTADOS_ACEPTADOS_CARGA_RESULTADO = frozenset(
    {"RECIBIDA", "CONSERVADA", "EN_PROCESO"}
)

# Al validar orden: resultado con muestra pendiente/tomada o terminal inválida bloquea.
MUESTRA_ESTADOS_INVALIDOS_VALIDACION_ORDEN = frozenset(
    {"RECHAZADA", "DESCARTADA", "CANCELADA", "PENDIENTE_TOMA", "TOMADA"}
)


def validate_muestra_integridad_resultado(
    *,
    solicitud_id: int,
    paciente_solicitud_id: int,
    muestra: Muestra | None,
) -> None:
    """
    Validación de integridad si hay muestra (usada desde `ResultadoExamen.clean`).
    No incluye estado operativo RECIBIDA/EN_PROCESO (eso es responsabilidad de la carga).
    """
    if muestra is None:
        return
    if muestra.solicitud_id != solicitud_id:
        raise ValidationError(
            {"muestra": "La muestra debe pertenecer a la misma solicitud que el resultado."}
        )
    if muestra.paciente_id != paciente_solicitud_id:
        raise ValidationError(
            {"muestra": "La muestra debe corresponder al mismo paciente que la solicitud."}
        )
    if muestra.estado in MUESTRA_ESTADOS_TERMINALES_SIN_RESULTADO:
        raise ValidationError(
            {
                "muestra": "No se puede vincular un resultado a una muestra rechazada, descartada o cancelada."
            }
        )


def assert_muestra_estado_carga_resultado(muestra: Muestra) -> None:
    """Regla operativa: solo RECIBIDA o EN_PROCESO al asignar muestra al cargar valores."""
    if muestra.estado not in MUESTRA_ESTADOS_ACEPTADOS_CARGA_RESULTADO:
        raise ValueError(
            "La muestra debe estar en estado RECIBIDA, CONSERVADA o EN_PROCESO para asociar un resultado."
        )


MSG_REQUIERE_MUESTRA = "Este tipo de examen requiere una muestra asociada."
MSG_TIPO_MUESTRA_INCORRECTO = (
    "La muestra no corresponde al tipo requerido para este examen."
)


def assert_tipo_examen_muestra_carga(
    *,
    tipo_examen,
    resultado_muestra: Muestra | None,
    muestra_id_en_payload: bool,
    raw_muestra_id,
) -> None:
    """
    Obligatoriedad progresiva (LIMS B2-B) al cargar resultados.

    - ``requiere_muestra``: exige muestra efectiva (payload o FK previa).
    - ``tipo_muestra_requerida`` (catálogo): si hay muestra, debe coincidir el tipo.
    """
    if not getattr(tipo_examen, "requiere_muestra", False):
        return

    if muestra_id_en_payload and raw_muestra_id is None:
        raise ValueError(MSG_REQUIERE_MUESTRA)

    if resultado_muestra is None:
        raise ValueError(MSG_REQUIERE_MUESTRA)

    tipo_req_id = getattr(tipo_examen, "tipo_muestra_requerida_id", None)
    if tipo_req_id is not None and resultado_muestra.tipo_muestra_id != tipo_req_id:
        raise ValueError(MSG_TIPO_MUESTRA_INCORRECTO)
