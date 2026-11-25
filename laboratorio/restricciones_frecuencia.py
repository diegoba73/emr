"""Restricciones de frecuencia / cobertura de ensayos (obra social).

Bloqueo duro al pedir (códigos generales): internación y guardia.
Ambulatorio / externo: pedir libre; al imprimir etiquetas el lab revisa alertas.

Excepción HBA1C:
- Guardia: el médico no puede pedirla nunca.
- Internación / ambulatorio / externo: bloqueo duro si hay pedido en los últimos 90 días.
Admin / laboratorio / bioquímico (LIMS-write) siguen exentos.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable

from django.utils import timezone

from laboratorio.models import SolicitudExamen, TipoExamen
from pacientes.models import Paciente
from usuarios.roles import puede_escribir_lims

# --- Códigos ---
CODIGO_PROBNP = "PROBNP"
CODIGO_PSA = "PSA"
CODIGO_VITD = "VITD"
CODIGO_HBA1C = "HBA1C"
CODIGO_T4 = "T4"
CODIGOS_TIROIDES = frozenset({"TSH", "T3", "T4", "T4L"})
CODIGOS_UNA_VEZ_ANIO = frozenset({CODIGO_PSA, CODIGO_VITD})
CODIGOS_RESTRINGIDOS = frozenset(
    {CODIGO_PROBNP, CODIGO_PSA, CODIGO_VITD, CODIGO_HBA1C, *CODIGOS_TIROIDES}
)


def origen_exige_bloqueo_frecuencia(origen: str | None) -> bool:
    """
    True = bloquear al crear/agregar (internación, guardia, origen vacío/desconocido).
    False = ambulatorio / externo: pedir libre; revisión al imprimir etiquetas.
    (HBA1c tiene reglas propias; ver ``_mensaje_bloqueo_hba1c``.)
    """
    o = (origen or "").strip().upper()
    if o.startswith("AMBULATORIO") or o.startswith("EXTERNO"):
        return False
    return True


def origen_es_guardia(origen: str | None) -> bool:
    o = (origen or "").strip().upper()
    return o == "GUARDIA" or o.startswith("GUARDIA")

VENTANA_DIAS_PROBNP = 31
VENTANA_DIAS_HBA1C = 90  # 3 meses
MIN_DIAS_ENTRE_TIROIDES = 60  # 2 meses
MAX_TIROIDES_POR_ANIO = 2
OBRA_SOCIAL_SEROS = "SEROS"

MENSAJE_CONSULTAR_LAB = (
    "De necesitarla de todas maneras, comuníquese con el Laboratorio."
)

MENSAJE_PROBNP_FRECUENCIA = (
    "La Obra Social no le permite realizar la determinación de proBNP debido a "
    "que tiene ya una realizada hace menos de 1 mes. "
    + MENSAJE_CONSULTAR_LAB
)

MENSAJE_HBA1C_GUARDIA = (
    "La determinación de hemoglobina glicosilada (HbA1c) no se puede pedir en Guardia. "
    + MENSAJE_CONSULTAR_LAB
)

MENSAJE_HBA1C_FRECUENCIA = (
    "La Obra Social exige un intervalo mínimo de 3 meses entre determinaciones "
    "de hemoglobina glicosilada (HbA1c). "
    + MENSAJE_CONSULTAR_LAB
)

MENSAJE_PSA_ANUAL = (
    "La Obra Social solo permite realizar PSA una vez al año. "
    + MENSAJE_CONSULTAR_LAB
)

MENSAJE_VITD_ANUAL = (
    "La Obra Social solo permite realizar Vitamina D una vez al año. "
    + MENSAJE_CONSULTAR_LAB
)

MENSAJE_T4_SEROS = (
    "La Obra Social SEROS no cubre la determinación de T4. "
    + MENSAJE_CONSULTAR_LAB
)

MENSAJE_TIROIDES_ANUAL = (
    "La Obra Social solo permite realizar {nombre} dos veces al año. "
    + MENSAJE_CONSULTAR_LAB
)

MENSAJE_TIROIDES_INTERVALO = (
    "La Obra Social exige un intervalo mínimo de 2 meses entre determinaciones "
    "de {nombre}. "
    + MENSAJE_CONSULTAR_LAB
)

_NOMBRES = {
    "TSH": "TSH",
    "T3": "T3",
    "T4": "T4",
    "T4L": "T4 libre",
    CODIGO_PROBNP: "proBNP",
    CODIGO_PSA: "PSA",
    CODIGO_VITD: "Vitamina D",
    CODIGO_HBA1C: "hemoglobina glicosilada (HbA1c)",
}


class RestriccionFrecuenciaError(ValueError):
    """El usuario no puede agregar el ensayo por política de frecuencia/cobertura."""


def usuario_exento_restricciones_ensayos(user: Any) -> bool:
    """
    Roles con escritura LIMS quedan exentos (admin, laboratorio, bioquímico,
    secretaría lab). El médico (y roles sin LIMS-write) sí están sujetos a
    las restricciones, incluida HBA1C.
    """
    return puede_escribir_lims(user)


def _anio_calendario(ref: date | datetime | None = None) -> int:
    if ref is None:
        return timezone.localdate().year
    if isinstance(ref, datetime):
        return timezone.localtime(ref).year if timezone.is_aware(ref) else ref.year
    return ref.year


def _inicio_fin_anio(anio: int) -> tuple[datetime, datetime]:
    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime(anio, 1, 1, 0, 0, 0), tz)
    fin = timezone.make_aware(datetime(anio, 12, 31, 23, 59, 59, 999999), tz)
    return inicio, fin


def _codigos_de_tipos(tipo_examen_ids: Iterable[int]) -> set[str]:
    ids = list(tipo_examen_ids)
    if not ids:
        return set()
    return set(
        TipoExamen.objects.filter(pk__in=ids).values_list("codigo", flat=True)
    )


def _qs_pedidos_con_codigo(
    paciente_id: int,
    codigo: str,
    *,
    exclude_solicitud_id: int | None = None,
):
    qs = SolicitudExamen.objects.filter(
        paciente_id=paciente_id,
        tipos_examen__codigo=codigo,
    )
    if exclude_solicitud_id is not None:
        qs = qs.exclude(pk=exclude_solicitud_id)
    return qs


def paciente_tiene_probnp_reciente(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> bool:
    desde = timezone.now() - timedelta(days=VENTANA_DIAS_PROBNP)
    return (
        _qs_pedidos_con_codigo(
            paciente_id, CODIGO_PROBNP, exclude_solicitud_id=exclude_solicitud_id
        )
        .filter(fecha_solicitud__gte=desde)
        .exists()
    )


def paciente_tiene_hba1c_reciente(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> bool:
    desde = timezone.now() - timedelta(days=VENTANA_DIAS_HBA1C)
    return (
        _qs_pedidos_con_codigo(
            paciente_id, CODIGO_HBA1C, exclude_solicitud_id=exclude_solicitud_id
        )
        .filter(fecha_solicitud__gte=desde)
        .exists()
    )


def count_pedidos_codigo_anio_calendario(
    paciente_id: int,
    codigo: str,
    *,
    anio: int | None = None,
    exclude_solicitud_id: int | None = None,
) -> int:
    anio = anio if anio is not None else _anio_calendario()
    inicio, fin = _inicio_fin_anio(anio)
    return (
        _qs_pedidos_con_codigo(
            paciente_id, codigo, exclude_solicitud_id=exclude_solicitud_id
        )
        .filter(fecha_solicitud__gte=inicio, fecha_solicitud__lte=fin)
        .distinct()
        .count()
    )


def ultima_fecha_pedido_codigo(
    paciente_id: int,
    codigo: str,
    *,
    exclude_solicitud_id: int | None = None,
) -> datetime | None:
    return (
        _qs_pedidos_con_codigo(
            paciente_id, codigo, exclude_solicitud_id=exclude_solicitud_id
        )
        .order_by("-fecha_solicitud")
        .values_list("fecha_solicitud", flat=True)
        .first()
    )


def paciente_obra_social_es_seros(paciente_id: int) -> bool:
    os_val = (
        Paciente.objects.filter(pk=paciente_id)
        .values_list("obra_social__codigo", flat=True)
        .first()
    )
    if not os_val:
        return False
    return str(os_val).strip().upper() == OBRA_SOCIAL_SEROS


def _mensaje_bloqueo_hba1c(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
    origen_solicitud: str | None = None,
) -> str | None:
    """
    HBA1C: prohibida en guardia; en internación/ambulatorio/externo exige ≥90 días
    desde el último pedido.
    """
    if origen_es_guardia(origen_solicitud):
        return MENSAJE_HBA1C_GUARDIA
    if paciente_tiene_hba1c_reciente(
        paciente_id, exclude_solicitud_id=exclude_solicitud_id
    ):
        return MENSAJE_HBA1C_FRECUENCIA
    return None


def _mensaje_bloqueo_codigo(
    codigo: str,
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
    origen_solicitud: str | None = None,
) -> str | None:
    """Devuelve mensaje de bloqueo para un código, o None si está permitido."""
    if codigo == CODIGO_T4 and paciente_obra_social_es_seros(paciente_id):
        return MENSAJE_T4_SEROS

    if codigo == CODIGO_PROBNP:
        if paciente_tiene_probnp_reciente(
            paciente_id, exclude_solicitud_id=exclude_solicitud_id
        ):
            return MENSAJE_PROBNP_FRECUENCIA
        return None

    if codigo == CODIGO_HBA1C:
        return _mensaje_bloqueo_hba1c(
            paciente_id,
            exclude_solicitud_id=exclude_solicitud_id,
            origen_solicitud=origen_solicitud,
        )

    if codigo == CODIGO_PSA:
        if count_pedidos_codigo_anio_calendario(
            paciente_id, CODIGO_PSA, exclude_solicitud_id=exclude_solicitud_id
        ) >= 1:
            return MENSAJE_PSA_ANUAL
        return None

    if codigo == CODIGO_VITD:
        if count_pedidos_codigo_anio_calendario(
            paciente_id, CODIGO_VITD, exclude_solicitud_id=exclude_solicitud_id
        ) >= 1:
            return MENSAJE_VITD_ANUAL
        return None

    if codigo in CODIGOS_TIROIDES:
        nombre = _NOMBRES.get(codigo, codigo)
        n = count_pedidos_codigo_anio_calendario(
            paciente_id, codigo, exclude_solicitud_id=exclude_solicitud_id
        )
        if n >= MAX_TIROIDES_POR_ANIO:
            return MENSAJE_TIROIDES_ANUAL.format(nombre=nombre)
        ultima = ultima_fecha_pedido_codigo(
            paciente_id, codigo, exclude_solicitud_id=exclude_solicitud_id
        )
        if ultima is not None:
            delta = timezone.now() - ultima
            if delta < timedelta(days=MIN_DIAS_ENTRE_TIROIDES):
                return MENSAJE_TIROIDES_INTERVALO.format(nombre=nombre)
        return None

    return None


def assert_puede_agregar_ensayos(
    user: Any,
    paciente_id: int,
    tipo_examen_ids: Iterable[int],
    *,
    exclude_solicitud_id: int | None = None,
    origen_solicitud: str | None = None,
) -> None:
    """
    Bloquea ensayos restringidos en internación/guardia (salvo lab/bio/admin).
    Ambulatorio/externo: no bloquea al pedir (revisión al imprimir etiquetas),
    salvo HBA1C (prohibida en guardia; 90 días en internación/ambulatorio/externo).
    """
    if usuario_exento_restricciones_ensayos(user):
        return
    codigos = _codigos_de_tipos(tipo_examen_ids)
    if not codigos:
        return

    # HBA1C aplica en todos los orígenes (regla propia).
    bloqueo_general = origen_exige_bloqueo_frecuencia(origen_solicitud)
    if not bloqueo_general and CODIGO_HBA1C not in codigos:
        return

    # Orden preferido de mensajes si hay varios en el mismo request
    candidatos: list[str] = []
    if CODIGO_HBA1C in codigos:
        candidatos.append(CODIGO_HBA1C)
    if bloqueo_general:
        if CODIGO_T4 in codigos:
            candidatos.append(CODIGO_T4)
        if CODIGO_PROBNP in codigos:
            candidatos.append(CODIGO_PROBNP)
        for c in (CODIGO_PSA, CODIGO_VITD, "TSH", "T3", "T4L"):
            if c in codigos and c not in candidatos:
                candidatos.append(c)

    for codigo in candidatos:
        msg = _mensaje_bloqueo_codigo(
            codigo,
            paciente_id,
            exclude_solicitud_id=exclude_solicitud_id,
            origen_solicitud=origen_solicitud,
        )
        if msg:
            raise RestriccionFrecuenciaError(msg)


# Compat: callers antiguos
def assert_puede_agregar_probnp(
    user: Any,
    paciente_id: int,
    tipo_examen_ids: Iterable[int],
    *,
    exclude_solicitud_id: int | None = None,
    origen_solicitud: str | None = None,
) -> None:
    assert_puede_agregar_ensayos(
        user,
        paciente_id,
        tipo_examen_ids,
        exclude_solicitud_id=exclude_solicitud_id,
        origen_solicitud=origen_solicitud,
    )


def restricciones_ensayos_para(
    user: Any,
    paciente_id: int,
    *,
    origen_solicitud: str | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Payload UX: mapa código → {bloqueado, mensaje}.
    Ambulatorio/externo: sin bloqueo general; HBA1C sí se evalúa siempre.
    """
    out: dict[str, dict[str, Any]] = {}
    if usuario_exento_restricciones_ensayos(user):
        for codigo in sorted(CODIGOS_RESTRINGIDOS):
            out[codigo] = {"bloqueado": False, "mensaje": None}
        return out

    bloqueo_general = origen_exige_bloqueo_frecuencia(origen_solicitud)
    for codigo in sorted(CODIGOS_RESTRINGIDOS):
        if codigo == CODIGO_HBA1C:
            msg = _mensaje_bloqueo_hba1c(
                paciente_id, origen_solicitud=origen_solicitud
            )
        elif bloqueo_general:
            msg = _mensaje_bloqueo_codigo(
                codigo, paciente_id, origen_solicitud=origen_solicitud
            )
        else:
            msg = None
        out[codigo] = {
            "bloqueado": bool(msg),
            "mensaje": msg,
        }
    return out


def alertas_frecuencia_para_solicitud(solicitud) -> list[dict[str, Any]]:
    """
    Alertas de frecuencia para ensayos ya cargados en la orden.
    Pensado para la puerta de impresión de etiquetas (ambulatorio).
    No depende del rol: lab/bioquímico decide si dejar o quitar.
    """
    paciente_id = getattr(solicitud, "paciente_id", None)
    if not paciente_id:
        return []
    exclude_id = getattr(solicitud, "pk", None)

    # codigo → (tipo_examen_id, nombre) desde la orden (no catálogo global).
    por_codigo: dict[str, tuple[int | None, str]] = {}
    for tid, codigo, nombre in solicitud.tipos_examen.values_list(
        "id", "codigo", "nombre"
    ):
        c = (codigo or "").strip().upper()
        if not c:
            continue
        por_codigo[c] = (tid, (nombre or c).strip())
    if hasattr(solicitud, "resultados"):
        for tid, codigo, nombre in solicitud.resultados.values_list(
            "tipo_examen_id", "tipo_examen__codigo", "tipo_examen__nombre"
        ):
            c = (codigo or "").strip().upper()
            if not c or c in por_codigo:
                continue
            por_codigo[c] = (tid, (nombre or c).strip())

    origen = getattr(solicitud, "origen_solicitud", None)
    alertas: list[dict[str, Any]] = []
    for codigo in sorted(set(por_codigo) & CODIGOS_RESTRINGIDOS):
        msg = _mensaje_bloqueo_codigo(
            codigo,
            paciente_id,
            exclude_solicitud_id=exclude_id,
            origen_solicitud=origen,
        )
        if not msg:
            continue
        tipo_id, nombre = por_codigo[codigo]
        alertas.append(
            {
                "codigo": codigo,
                "nombre": nombre or _NOMBRES.get(codigo, codigo),
                "mensaje": msg,
                "tipo_examen_id": tipo_id,
            }
        )
    return alertas
