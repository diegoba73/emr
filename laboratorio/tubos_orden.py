"""
Cálculo de tubos físicos necesarios para una SolicitudExamen.

Regla general: máximo MAX_EXAMENES_POR_TUBO exámenes por tipo de contenedor;
cantidad = ceil(n / MAX).

Excepción: los componentes del hemograma (PAN_HEMO) caben en un solo tubo EDTA
y cuentan como 1 unidad hacia ese tope, no como N exámenes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from laboratorio.models import SolicitudExamen
from laboratorio.models_catalog import Muestra
from laboratorio.panel_componentes_orden import PANEL_COMPONENTES_BY_CODIGO

MAX_EXAMENES_POR_TUBO = 10
PANEL_HEMOGRAMA_CODIGO = "PAN_HEMO"
_CODIGOS_HEMOGRAMA = frozenset(PANEL_COMPONENTES_BY_CODIGO.get(PANEL_HEMOGRAMA_CODIGO, ()))

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


def unidades_para_calculo_tubos(examenes) -> int:
    """
    Unidades hacia el tope de exámenes/tubo.

    Cada examen cuenta 1, excepto el bloque hemograma completo que cuenta 1
    aunque tenga muchos componentes (todos en el mismo EDTA).
    """
    tiene_hemo = False
    otros = 0
    for ex in examenes:
        codigo = getattr(ex, "codigo", None) or ""
        if es_codigo_hemograma(codigo):
            tiene_hemo = True
        else:
            otros += 1
    return otros + (1 if tiene_hemo else 0)


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


def resolver_tubos_para_solicitud(solicitud: SolicitudExamen) -> list[TuboOrdenGrupo]:
    """
    Agrupa los tipos de examen de la orden por tipo_contenedor y calcula
    cuántos tubos físicos hacen falta (ceil(unidades / 10), con hemograma = 1).
    """
    examenes = _tipos_examen_para_tubos(solicitud)
    if not examenes:
        return []

    con_tubo = [e for e in examenes if e.tipo_contenedor_id]
    sin_tubo = [e for e in examenes if not e.tipo_contenedor_id]
    # Catálogo aún sin tubos: no exigir (compatibilidad). Mezcla parcial → error.
    if not con_tubo:
        return []
    if sin_tubo:
        codigos = ", ".join(e.codigo for e in sin_tubo[:8])
        extra = f" (+{len(sin_tubo) - 8})" if len(sin_tubo) > 8 else ""
        raise TubosOrdenError(
            f"Hay exámenes sin tipo de tubo asignado: {codigos}{extra}. "
            "Configúrelos en el catálogo de exámenes antes de tomar muestra."
        )

    by_cont: dict[int, list] = {}
    meta: dict[int, TuboOrdenGrupo] = {}
    for ex in con_tubo:
        tc = ex.tipo_contenedor
        assert tc is not None
        if not tc.activo:
            raise TubosOrdenError(f"El tipo de tubo {tc.codigo} está inactivo.")
        tm_id = ex.tipo_muestra_requerida_id
        if tc.pk in meta:
            g = meta[tc.pk]
            if g.tipo_muestra_id != tm_id:
                raise TubosOrdenError(
                    f"El tubo {tc.codigo} está asociado a exámenes con distintos tipos "
                    f"de muestra biológica en esta orden."
                )
            g.examenes.append(ex.nombre)
            by_cont[tc.pk].append(ex)
        else:
            meta[tc.pk] = TuboOrdenGrupo(
                tipo_muestra_id=tm_id,
                tipo_contenedor_id=tc.pk,
                tipo_contenedor_codigo=tc.codigo,
                tipo_contenedor_nombre=tc.nombre,
                examenes=[ex.nombre],
            )
            by_cont[tc.pk] = [ex]

    result: list[TuboOrdenGrupo] = []
    for tc_pk, g in meta.items():
        g.cantidad = cantidad_tubos_por_examenes(unidades_para_calculo_tubos(by_cont[tc_pk]))
        result.append(g)
    result.sort(key=lambda x: x.tipo_contenedor_codigo)
    return result


def expandir_items_crear_muestras(
    solicitud: SolicitudExamen,
    grupos: list[TuboOrdenGrupo] | None = None,
) -> list[dict[str, Any]]:
    """
    Expande grupos a ítems 1:1 de creación de Muestra, omitiendo tubos ya
    existentes (activos) para ese contenedor en la orden.
    """
    if grupos is None:
        grupos = resolver_tubos_para_solicitud(solicitud)
    items: list[dict[str, Any]] = []
    for g in grupos:
        existentes = Muestra.objects.filter(
            solicitud_id=solicitud.pk,
            tipo_contenedor_id=g.tipo_contenedor_id,
        ).exclude(estado__in=_MUESTRA_ESTADOS_TERMINALES).count()
        faltan = max(0, g.cantidad - existentes)
        for _ in range(faltan):
            items.append(
                {
                    "tipo_muestra_id": g.tipo_muestra_id,
                    "tipo_contenedor_id": g.tipo_contenedor_id,
                    "observaciones": "",
                }
            )
    return items


def preview_tubos_solicitud(solicitud: SolicitudExamen) -> list[dict[str, Any]]:
    return [g.as_dict() for g in resolver_tubos_para_solicitud(solicitud)]
