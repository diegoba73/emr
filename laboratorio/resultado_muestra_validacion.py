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

# Al validar orden: resultado *con valor* no puede apuntar a muestra pendiente/tomada
# ni terminal (CANCELADA/RECHAZADA/DESCARTADA). Resultados vacíos sobre tubos
# cancelados no bloquean (ver solicitud_cierre).
# Además, cualquier tubo de la orden aún en PENDIENTE_TOMA/TOMADA bloquea listo/validar
# (aunque no tenga resultado vinculado). Cancelar/rechazar/descartar esos tubos habilita
# el cierre si los resultados exigibles de los tubos activos están completos.
# La carga de valores exige RECIBIDA/CONSERVADA/EN_PROCESO — se puede cargar el tubo recibido
# aunque queden otros pendientes.
MUESTRA_ESTADOS_INVALIDOS_VALIDACION_ORDEN = frozenset(
    {"RECHAZADA", "DESCARTADA", "CANCELADA", "PENDIENTE_TOMA", "TOMADA"}
)

# Tubos aún no recepcionados: bloquean pasar a LISTO_PARA_VALIDAR / validar.
MUESTRA_ESTADOS_PENDIENTES_RECEPCION = frozenset({"PENDIENTE_TOMA", "TOMADA"})


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


def tipo_muestra_fisica_compatible_con_examen(tipo_examen, muestra: Muestra) -> bool:
    """
    True si el material físico de la muestra satisface el catálogo del examen.

    Duales de orina (NA_U/CREA_U/…) pueden ir a frasco (ORINA) o a bidón
    (ORINA_24_H) según el contexto de la orden; el FK del catálogo no siempre
    refleja el tubo efectivo.
    """
    tipo_req_id = getattr(tipo_examen, "tipo_muestra_requerida_id", None)
    if tipo_req_id is None:
        return True
    if muestra.tipo_muestra_id == tipo_req_id:
        return True

    from laboratorio.tubos_catalogo import MUESTRA_ORINA, MUESTRA_ORINA_24H, _ORINA_DUAL

    codigo = (getattr(tipo_examen, "codigo", None) or "").strip().upper()
    if codigo not in _ORINA_DUAL:
        return False
    req = getattr(getattr(tipo_examen, "tipo_muestra_requerida", None), "codigo", None) or ""
    got = getattr(getattr(muestra, "tipo_muestra", None), "codigo", None) or ""
    pair = {MUESTRA_ORINA, MUESTRA_ORINA_24H}
    return req in pair and got in pair

from laboratorio.muestra_estado import aplicar_recibir


def asegurar_muestra_lista_para_carga(
    muestra: Muestra,
    *,
    actor,
    view: str,
) -> Muestra:
    """
    Tras tomar muestra en la orden (sin pestaña Muestras), el tubo puede quedar TOMADA.
    Al cargar resultados se recepciona automáticamente si hace falta.
    """
    if muestra.estado == "TOMADA":
        aplicar_recibir(
            muestra.pk,
            actor=actor,
            view=view,
            ubicacion_actual=muestra.ubicacion_actual or "Laboratorio",
            observaciones="Recepción automática al cargar resultados.",
        )
        muestra.refresh_from_db()
    return muestra


def assert_tipo_examen_muestra_carga(
    *,
    tipo_examen,
    resultado_muestra: Muestra | None,
    muestra_id_en_payload: bool,
    raw_muestra_id,
) -> None:
    """
    Obligatoriedad progresiva (LIMS B2-B / B2-B-A) al cargar resultados.

    - ``requiere_muestra``: exige muestra efectiva (payload o FK previa).
    - Exámenes ``CALCULADO`` (clearance, LDL, orinas 24 hs, etc.) no exigen tubo:
      el valor se deriva de medidos; la muestra vive en esos insumos.
    - ``tipo_muestra_requerida``: si hay muestra asociada, el tipo físico debe coincidir
      aunque ``requiere_muestra`` sea False.
    """
    modo = getattr(tipo_examen, "modo_entrada", None) or ""
    codigo = (getattr(tipo_examen, "codigo", None) or "").strip().upper()
    es_calculado = modo == "CALCULADO"
    if not es_calculado:
        from laboratorio.calculos_derivados import es_codigo_calculado

        es_calculado = es_codigo_calculado(codigo)
    # FiO2: dato de contexto de gases, sin tubo propio.
    sin_tubo_fisico = es_calculado or codigo == "FIO2"

    requiere_muestra = getattr(tipo_examen, "requiere_muestra", False) and not sin_tubo_fisico

    if requiere_muestra:
        if muestra_id_en_payload and raw_muestra_id is None:
            raise ValueError(MSG_REQUIERE_MUESTRA)
        if resultado_muestra is None:
            raise ValueError(MSG_REQUIERE_MUESTRA)

    if resultado_muestra is None:
        return

    if not tipo_muestra_fisica_compatible_con_examen(tipo_examen, resultado_muestra):
        raise ValueError(MSG_TIPO_MUESTRA_INCORRECTO)
