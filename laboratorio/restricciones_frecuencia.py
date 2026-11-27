"""Restricciones de frecuencia / cobertura de ensayos (obra social).

Política unificada (como ionograma + SEROS):
- **Al pedir** (médico u otros): **no** se bloquea. El pedido puede crearse/
  ampliarse; el paciente puede abonar en particular si la OS no cubre.
- **Al imprimir etiquetas/talón**: el laboratorio recibe alertas y decide
  continuar o quitar ensayos.

Guardia: el catálogo pedible por el médico lo fija
``restricciones_guardia_catalogo`` (modal). Cualquier otro examen queda fuera
del allowlist; no se usa esta capa de frecuencia para eso.

``assert_puede_agregar_ensayos`` queda como no-op (compat call sites).
``restricciones_ensayos_para`` reporta ``bloqueado: false`` + ``aviso``/``mensaje``
para que el FE avise al médico al enviar sin impedir el pedido.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable

from django.db.models import Q
from django.utils import timezone

from laboratorio.models import SolicitudExamen, TipoExamen
from pacientes.models import Paciente
from usuarios.roles import puede_escribir_lims

# --- Códigos ---
CODIGO_PROBNP = "PROBNP"
CODIGO_PSA = "PSA"
CODIGO_VITD = "VITD"
CODIGO_HBA1C = "HBA1C"
CODIGO_LPA = "LPA"
CODIGO_T4 = "T4"
CODIGO_PAN_IONO = "PAN_IONO"
CODIGOS_TIROIDES = frozenset({"TSH", "T3", "T4", "T4L"})
# Componentes del ionograma plasmático (panel PAN_IONO). No incluye urinarios.
CODIGOS_IONOGRAMA_COMPONENTES = frozenset({"NA", "K", "CL"})
CODIGOS_IONOGRAMA = frozenset({CODIGO_PAN_IONO, *CODIGOS_IONOGRAMA_COMPONENTES})
CODIGOS_UNA_VEZ_ANIO = frozenset({CODIGO_PSA, CODIGO_VITD})
# Compat: antes HBA1C/LPA bloqueaban en todos los orígenes al pedir.
CODIGOS_VENTANA_90_SIEMPRE = frozenset({CODIGO_HBA1C, CODIGO_LPA})
CODIGOS_RESTRINGIDOS = frozenset(
    {
        CODIGO_PROBNP,
        CODIGO_PSA,
        CODIGO_VITD,
        CODIGO_HBA1C,
        CODIGO_LPA,
        CODIGO_PAN_IONO,
        *CODIGOS_TIROIDES,
    }
)
# Todas las reglas de este módulo son solo aviso al imprimir (ninguna bloquea al pedir).
CODIGOS_SOLO_ALERTA_IMPRESION = frozenset(CODIGOS_RESTRINGIDOS)


def origen_exige_bloqueo_frecuencia(origen: str | None) -> bool:
    """
    Clasifica origen: True = internación/guardia/desconocido; False = ambulatorio/externo.

    Ya **no** implica bloqueo al pedir (política unificada = alerta al imprimir).
    Se conserva por callers/tests que distinguen el origen.
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
VENTANA_DIAS_LPA = 90  # 3 meses
MIN_DIAS_ENTRE_TIROIDES = 60  # 2 meses
MAX_TIROIDES_POR_ANIO = 2
OBRA_SOCIAL_SEROS = "SEROS"

MENSAJE_CONSULTAR_LAB = (
    "De necesitarla de todas maneras, comuníquese con el Laboratorio."
)

MENSAJE_PROBNP_FRECUENCIA = (
    "La Obra Social no le permite realizar la determinación de proBNP debido a "
    "que tiene ya una realizada hace menos de 1 mes. "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
)

MENSAJE_HBA1C_FRECUENCIA = (
    "La Obra Social exige un intervalo mínimo de 3 meses entre determinaciones "
    "de hemoglobina glicosilada (HbA1c). "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
)

MENSAJE_LPA_FRECUENCIA = (
    "La Obra Social exige un intervalo mínimo de 3 meses entre determinaciones "
    "de Lipoproteína A (Lp(a)). "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
)

MENSAJE_PSA_ANUAL = (
    "La Obra Social solo permite realizar PSA una vez al año. "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
)

MENSAJE_VITD_ANUAL = (
    "La Obra Social solo permite realizar Vitamina D una vez al año. "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
)

MENSAJE_T4_SEROS = (
    "La Obra Social SEROS no cubre la determinación de T4. "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
)

MENSAJE_IONO_SEROS_ANUAL = (
    "La Obra Social SEROS solo cubre ionograma plasmático una vez al año. "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
)

MENSAJE_TIROIDES_ANUAL = (
    "La Obra Social solo permite realizar {nombre} dos veces al año. "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
)

MENSAJE_TIROIDES_INTERVALO = (
    "La Obra Social exige un intervalo mínimo de 2 meses entre determinaciones "
    "de {nombre}. "
    "Si el paciente abona en forma particular puede continuar; "
    "si no, quitar el ensayo de la orden."
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
    CODIGO_LPA: "Lipoproteína A (Lp(a))",
    CODIGO_PAN_IONO: "ionograma plasmático",
}


class RestriccionFrecuenciaError(ValueError):
    """Reservado por compatibilidad; ya no se lanza en el flujo de pedido."""


def usuario_exento_restricciones_ensayos(user: Any) -> bool:
    """Roles con escritura LIMS (admin, laboratorio, bioquímico, …)."""
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


def paciente_tiene_lpa_reciente(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> bool:
    desde = timezone.now() - timedelta(days=VENTANA_DIAS_LPA)
    return (
        _qs_pedidos_con_codigo(
            paciente_id, CODIGO_LPA, exclude_solicitud_id=exclude_solicitud_id
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


def count_pedidos_ionograma_anio_calendario(
    paciente_id: int,
    *,
    anio: int | None = None,
    exclude_solicitud_id: int | None = None,
) -> int:
    """Pedidos con ionograma plasmático (panel PAN_IONO o componentes Na/K/Cl)."""
    anio = anio if anio is not None else _anio_calendario()
    inicio, fin = _inicio_fin_anio(anio)
    qs = SolicitudExamen.objects.filter(
        paciente_id=paciente_id,
        fecha_solicitud__gte=inicio,
        fecha_solicitud__lte=fin,
    ).filter(
        Q(paneles__codigo=CODIGO_PAN_IONO)
        | Q(tipos_examen__codigo__in=CODIGOS_IONOGRAMA_COMPONENTES)
    )
    if exclude_solicitud_id is not None:
        qs = qs.exclude(pk=exclude_solicitud_id)
    return qs.distinct().count()


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


def _mensaje_alerta_hba1c(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> str | None:
    """HBA1C: alerta si hay pedido en los últimos 90 días (no bloquea al pedir)."""
    if paciente_tiene_hba1c_reciente(
        paciente_id, exclude_solicitud_id=exclude_solicitud_id
    ):
        return MENSAJE_HBA1C_FRECUENCIA
    return None


def _mensaje_alerta_lpa(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> str | None:
    """LPA: alerta si hay pedido en los últimos 90 días (no bloquea al pedir)."""
    if paciente_tiene_lpa_reciente(
        paciente_id, exclude_solicitud_id=exclude_solicitud_id
    ):
        return MENSAJE_LPA_FRECUENCIA
    return None


def _mensaje_alerta_ionograma_seros(
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
) -> str | None:
    """SEROS: máx. 1 ionograma plasmático por año calendario."""
    if not paciente_obra_social_es_seros(paciente_id):
        return None
    if count_pedidos_ionograma_anio_calendario(
        paciente_id, exclude_solicitud_id=exclude_solicitud_id
    ) >= 1:
        return MENSAJE_IONO_SEROS_ANUAL
    return None


def _mensaje_bloqueo_codigo(
    codigo: str,
    paciente_id: int,
    *,
    exclude_solicitud_id: int | None = None,
    origen_solicitud: str | None = None,
) -> str | None:
    """
    Mensaje de alerta de frecuencia/cobertura para un código, o None si no aplica.

    El nombre histórico «bloqueo» se conserva; **no** se usa para rechazar pedidos.
    ``origen_solicitud`` se acepta por compat de callers (ya no altera HBA1C/LPA).
    """
    del origen_solicitud  # catálogo de guardia es otra capa; no aplica acá

    if codigo == CODIGO_T4 and paciente_obra_social_es_seros(paciente_id):
        return MENSAJE_T4_SEROS

    if codigo == CODIGO_PAN_IONO or codigo in CODIGOS_IONOGRAMA_COMPONENTES:
        return _mensaje_alerta_ionograma_seros(
            paciente_id, exclude_solicitud_id=exclude_solicitud_id
        )

    if codigo == CODIGO_PROBNP:
        if paciente_tiene_probnp_reciente(
            paciente_id, exclude_solicitud_id=exclude_solicitud_id
        ):
            return MENSAJE_PROBNP_FRECUENCIA
        return None

    if codigo == CODIGO_HBA1C:
        return _mensaje_alerta_hba1c(
            paciente_id, exclude_solicitud_id=exclude_solicitud_id
        )

    if codigo == CODIGO_LPA:
        return _mensaje_alerta_lpa(
            paciente_id, exclude_solicitud_id=exclude_solicitud_id
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
    No-op: las reglas de frecuencia **no** bloquean al crear/agregar.

    La revisión es ``alertas_frecuencia_para_solicitud`` al imprimir etiquetas/talón.
    Firma conservada por call sites (pedidos-completos, serializers, views).
    """
    del user, paciente_id, tipo_examen_ids, exclude_solicitud_id, origen_solicitud
    return


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
    Payload UX: mapa código → {bloqueado, aviso, mensaje}.

    - ``bloqueado`` siempre False (no impide tildar/enviar).
    - ``aviso`` + ``mensaje`` si la política de OS/frecuencia aplica: el FE
      muestra confirmación al enviar; el lab vuelve a verlo al imprimir.
    """
    del user  # ya no hay exención de aviso: lab también puede ver el mapa
    out: dict[str, dict[str, Any]] = {}
    # Incluir Na/K/Cl sueltos (mismo aviso que PAN_IONO) para selección por componente.
    codigos = set(CODIGOS_RESTRINGIDOS) | set(CODIGOS_IONOGRAMA_COMPONENTES)
    for codigo in sorted(codigos):
        msg = _mensaje_bloqueo_codigo(
            codigo, paciente_id, origen_solicitud=origen_solicitud
        )
        out[codigo] = {
            "bloqueado": False,
            "aviso": bool(msg),
            "mensaje": msg,
        }
    return out


def alertas_frecuencia_para_solicitud(solicitud) -> list[dict[str, Any]]:
    """
    Alertas de frecuencia para ensayos ya cargados en la orden.
    Puerta de impresión de etiquetas/talón (cualquier origen).
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
    codigos_check = set(por_codigo) & CODIGOS_RESTRINGIDOS
    # Ionograma llega como componentes (NA/K/Cl); unificar alerta bajo PAN_IONO.
    if set(por_codigo) & CODIGOS_IONOGRAMA_COMPONENTES:
        codigos_check.add(CODIGO_PAN_IONO)
    for codigo in sorted(codigos_check):
        msg = _mensaje_bloqueo_codigo(
            codigo,
            paciente_id,
            exclude_solicitud_id=exclude_id,
            origen_solicitud=origen,
        )
        if not msg:
            continue
        if codigo == CODIGO_PAN_IONO and codigo not in por_codigo:
            tipo_id = None
            for c_comp in ("NA", "K", "CL"):
                if c_comp in por_codigo:
                    tipo_id = por_codigo[c_comp][0]
                    break
            nombre = _NOMBRES.get(CODIGO_PAN_IONO, CODIGO_PAN_IONO)
        else:
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
