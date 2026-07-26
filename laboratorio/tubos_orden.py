"""
Cálculo de tubos físicos necesarios para una SolicitudExamen.

Regla general: máximo MAX_EXAMENES_POR_TUBO exámenes por tipo de contenedor;
cantidad = ceil(n / MAX).

Excepciones (cuentan como 1 unidad hacia el tope, no como N componentes):
- Hemograma (PAN_HEMO) → un EDTA
- Orina completa (PAN_ORI) → un frasco de orina
- Química de rutina → un heparina (plasma ~200 µL)
- Orina 24 hs (clearance, proteinuria 24h, ionograma 24h, etc.) → un bidón
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from laboratorio.models import SolicitudExamen, TipoMuestra
from laboratorio.models_catalog import Muestra, TipoContenedor
from laboratorio.panel_componentes_orden import PANEL_COMPONENTES_BY_CODIGO
from laboratorio.tubos_catalogo import (
    BIDON_ORINA_24H,
    MUESTRA_ORINA_24H,
    PANELES_ORINA_24H,
    _EAB_JERINGA_INDIVIDUAL,
    _ORINA_24H,
    _ORINA_DUAL,
    _QUIMICA_RUTINA,
    es_muestra_orina_24h,
)

MAX_EXAMENES_POR_TUBO = 10
PANEL_HEMOGRAMA_CODIGO = "PAN_HEMO"
PANEL_ORINA_COMPLETA_CODIGO = "PAN_ORI"
_CODIGOS_HEMOGRAMA = frozenset(PANEL_COMPONENTES_BY_CODIGO.get(PANEL_HEMOGRAMA_CODIGO, ()))
_CODIGOS_ORINA_COMPLETA = frozenset(
    PANEL_COMPONENTES_BY_CODIGO.get(PANEL_ORINA_COMPLETA_CODIGO, ())
)
_CODIGOS_QUIMICA_RUTINA = frozenset(_QUIMICA_RUTINA)
_CODIGOS_ORINA_24H = frozenset(_ORINA_24H)

_MUESTRA_ESTADOS_TERMINALES = frozenset({"RECHAZADA", "DESCARTADA", "CANCELADA"})


@dataclass
class TuboOrdenGrupo:
    tipo_muestra_id: int
    tipo_contenedor_id: int
    tipo_contenedor_codigo: str
    tipo_contenedor_nombre: str
    examenes: list[str] = field(default_factory=list)
    cantidad: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "tipo_muestra_id": self.tipo_muestra_id,
            "tipo_contenedor_id": self.tipo_contenedor_id,
            "tipo_contenedor_codigo": self.tipo_contenedor_codigo,
            "tipo_contenedor_nombre": self.tipo_contenedor_nombre,
            "examenes": list(self.examenes),
            "cantidad": self.cantidad,
            "examenes_count": len(self.examenes),
        }


class TubosOrdenError(Exception):
    """Error al resolver tubos de una orden."""


def cantidad_tubos_por_examenes(n_examenes: int, *, max_por_tubo: int = MAX_EXAMENES_POR_TUBO) -> int:
    if n_examenes <= 0:
        return 0
    return int(math.ceil(n_examenes / max_por_tubo))


def es_codigo_hemograma(codigo: str | None) -> bool:
    return bool(codigo) and codigo in _CODIGOS_HEMOGRAMA


def es_codigo_orina_completa(codigo: str | None) -> bool:
    return bool(codigo) and codigo in _CODIGOS_ORINA_COMPLETA


def es_codigo_quimica_rutina(codigo: str | None) -> bool:
    return bool(codigo) and codigo in _CODIGOS_QUIMICA_RUTINA


def es_codigo_orina_24h(codigo: str | None) -> bool:
    return bool(codigo) and codigo in _CODIGOS_ORINA_24H


def unidades_para_calculo_tubos(examenes) -> int:
    """
    Unidades hacia el tope de exámenes/tubo.

    Cada examen cuenta 1, excepto bloques: hemograma, orina completa,
    química rutina y orina 24 hs fija (1 unidad c/u).
    """
    tiene_hemo = False
    tiene_orina = False
    tiene_quimica = False
    tiene_orina_24 = False
    otros = 0
    for ex in examenes:
        codigo = getattr(ex, "codigo", None) or ""
        if es_codigo_hemograma(codigo):
            tiene_hemo = True
        elif es_codigo_orina_completa(codigo):
            tiene_orina = True
        elif es_codigo_quimica_rutina(codigo):
            tiene_quimica = True
        elif es_codigo_orina_24h(codigo):
            tiene_orina_24 = True
        else:
            otros += 1
    return (
        otros
        + (1 if tiene_hemo else 0)
        + (1 if tiene_orina else 0)
        + (1 if tiene_quimica else 0)
        + (1 if tiene_orina_24 else 0)
    )


def _tipos_examen_para_tubos(solicitud: SolicitudExamen):
    """
    Exámenes a considerar para cálculo de tubos.

    Incluye ``tipos_examen`` directos y componentes de paneles (órdenes
    solo-panel no poblaban el M2M histórico). Fallback: resultados creados.
    """
    from laboratorio.models import TipoExamen

    by_id: dict[int, TipoExamen] = {}
    for te in solicitud.tipos_examen.select_related(
        "tipo_contenedor", "tipo_muestra_requerida"
    ).all():
        by_id[te.pk] = te

    for panel in solicitud.paneles.prefetch_related(
        "tipos_examen__tipo_contenedor",
        "tipos_examen__tipo_muestra_requerida",
    ).all():
        for te in panel.tipos_examen.all():
            by_id.setdefault(te.pk, te)

    if not by_id:
        for te in TipoExamen.objects.filter(resultados__solicitud_id=solicitud.pk).select_related(
            "tipo_contenedor", "tipo_muestra_requerida"
        ).distinct():
            by_id[te.pk] = te

    return list(by_id.values())


def _orden_requiere_orina_24h(solicitud: SolicitudExamen, examenes) -> bool:
    """True si la orden pide recolección de orina de 24 horas."""
    paneles = {p.codigo for p in solicitud.paneles.all()}
    if paneles & PANELES_ORINA_24H:
        return True
    for ex in examenes:
        codigo = getattr(ex, "codigo", None) or ""
        if codigo in _ORINA_24H:
            return True
        tm = getattr(ex, "tipo_muestra_requerida", None)
        if tm and es_muestra_orina_24h(tm.codigo, tm.nombre):
            return True
        tc = getattr(ex, "tipo_contenedor", None)
        if tc and tc.codigo == BIDON_ORINA_24H:
            return True
    return False


def _resolver_bidon_y_muestra_24h():
    bidon = TipoContenedor.objects.filter(codigo=BIDON_ORINA_24H, activo=True).first()
    muestra, _ = TipoMuestra.objects.get_or_create(
        codigo=MUESTRA_ORINA_24H,
        defaults={"nombre": "Orina 24 hs", "color_tubo": "Ámbar", "activo": True},
    )
    return bidon, muestra


def resolver_tubos_para_solicitud(solicitud: SolicitudExamen) -> list[TuboOrdenGrupo]:
    """
    Agrupa por (tipo_contenedor, tipo_muestra) efectivo y calcula tubos físicos.

    Orina 24 hs (incl. duales NA_U/CREA_U/MICROALB cuando la orden tiene
    contexto 24 hs) van al bidón; orina completa/al azar quedan en frasco.
    Todos los de 24 hs juntos → cantidad 1 (un bidón).
    """
    examenes = _tipos_examen_para_tubos(solicitud)
    if not examenes:
        return []

    con_tubo = [e for e in examenes if e.tipo_contenedor_id]
    sin_tubo = [e for e in examenes if not e.tipo_contenedor_id]
    if not con_tubo:
        return []
    if sin_tubo:
        codigos = ", ".join(e.codigo for e in sin_tubo[:8])
        extra = f" (+{len(sin_tubo) - 8})" if len(sin_tubo) > 8 else ""
        raise TubosOrdenError(
            f"Hay exámenes sin tipo de tubo asignado: {codigos}{extra}. "
            "Configúrelos en el catálogo de exámenes antes de tomar muestra."
        )

    requiere_24h = _orden_requiere_orina_24h(solicitud, con_tubo)
    bidon, muestra_24h = (None, None)
    if requiere_24h:
        bidon, muestra_24h = _resolver_bidon_y_muestra_24h()
        if bidon is None:
            raise TubosOrdenError(
                "Falta el tipo de contenedor BIDON_ORINA_24H en el catálogo."
            )

    by_key: dict[tuple, list] = {}
    meta: dict[tuple, TuboOrdenGrupo] = {}
    for ex in con_tubo:
        tc = ex.tipo_contenedor
        assert tc is not None
        if not tc.activo:
            raise TubosOrdenError(f"El tipo de tubo {tc.codigo} está inactivo.")

        codigo = ex.codigo or ""
        tm = ex.tipo_muestra_requerida
        tm_id = ex.tipo_muestra_requerida_id
        tc_eff = tc
        if requiere_24h and bidon is not None and muestra_24h is not None:
            if (
                codigo in _ORINA_24H
                or codigo in _ORINA_DUAL
                or tc.codigo == BIDON_ORINA_24H
                or (tm and es_muestra_orina_24h(tm.codigo, tm.nombre))
            ):
                tc_eff = bidon
                tm_id = muestra_24h.pk

        if not tc_eff.activo:
            raise TubosOrdenError(f"El tipo de tubo {tc_eff.codigo} está inactivo.")

        # EAB art/ven: jeringas distintas aunque compartan heparina
        split = codigo if codigo in _EAB_JERINGA_INDIVIDUAL else ""
        key = (tc_eff.pk, tm_id, split)
        if key in meta:
            meta[key].examenes.append(ex.nombre)
            by_key[key].append(ex)
        else:
            meta[key] = TuboOrdenGrupo(
                tipo_muestra_id=tm_id,
                tipo_contenedor_id=tc_eff.pk,
                tipo_contenedor_codigo=tc_eff.codigo,
                tipo_contenedor_nombre=tc_eff.nombre,
                examenes=[ex.nombre],
            )
            by_key[key] = [ex]

    result: list[TuboOrdenGrupo] = []
    for key, g in meta.items():
        if g.tipo_contenedor_codigo == BIDON_ORINA_24H:
            g.cantidad = 1
        elif key[2]:  # EAB individual
            g.cantidad = 1
        else:
            g.cantidad = cantidad_tubos_por_examenes(unidades_para_calculo_tubos(by_key[key]))
        result.append(g)
    result.sort(key=lambda x: (x.tipo_contenedor_codigo, x.tipo_muestra_id, x.examenes[0] if x.examenes else ""))
    return result


def expandir_items_crear_muestras(
    solicitud: SolicitudExamen,
    grupos: list[TuboOrdenGrupo] | None = None,
) -> list[dict[str, Any]]:
    """
    Expande grupos a ítems 1:1 de creación de Muestra, omitiendo tubos ya
    existentes (activos) para ese (contenedor, muestra) en la orden.

    Si varios grupos comparten el mismo (contenedor, muestra) — p. ej. EAB art+ven
    antes de diferenciar muestras — se suma la cantidad pedida.
    """
    if grupos is None:
        grupos = resolver_tubos_para_solicitud(solicitud)

    from collections import defaultdict

    needed: dict[tuple[int, int], int] = defaultdict(int)
    for g in grupos:
        needed[(g.tipo_contenedor_id, g.tipo_muestra_id)] += g.cantidad

    items: list[dict[str, Any]] = []
    for (tc_id, tm_id), cantidad in needed.items():
        existentes = Muestra.objects.filter(
            solicitud_id=solicitud.pk,
            tipo_contenedor_id=tc_id,
            tipo_muestra_id=tm_id,
        ).exclude(estado__in=_MUESTRA_ESTADOS_TERMINALES).count()
        faltan = max(0, cantidad - existentes)
        for _ in range(faltan):
            items.append(
                {
                    "tipo_muestra_id": tm_id,
                    "tipo_contenedor_id": tc_id,
                    "observaciones": "",
                }
            )
    return items


def preview_tubos_solicitud(solicitud: SolicitudExamen) -> list[dict[str, Any]]:
    return [g.as_dict() for g in resolver_tubos_para_solicitud(solicitud)]
