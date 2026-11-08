"""Catálogo permitido en pedidos LIMS de origen GUARDIA.

Nombres canónicos del seed (`catalogo_solicitud_papel`): se valida por
**código**, no por etiqueta clínica coloquial.

| Pedido clínico        | Código      | Nombre almacenado              |
|-----------------------|-------------|-------------------------------|
| Hemograma             | PAN_HEMO    | Hemograma                     |
| Ionograma             | PAN_IONO    | Ionograma plasmático          |
| Glucosa               | GLU         | Glucemia                      |
| Urea                  | UREA        | Uremia                        |
| Creatinina            | CREATI      | Creatininemia                 |
| Hepatograma           | PAN_HEP     | Hepatograma                   |
| Troponina US          | TROP_US     | Troponina I ultrasensible     |
| Troponina I           | TROP_I      | Troponina I                   |
| CK-MB                 | CPK_MB      | CPK-MB                        |
| CPK                   | CPK         | CPK                           |
| Mioglobina            | MIOG        | Mioglobina                    |
| Gases arteriales      | PAN_EAB_ART | EAB arterial                  |
| Gases venosos         | PAN_EAB_VEN | EAB venoso                    |

Notas de naming:

- Urea → ``UREA`` / «Uremia» (sí en allowlist de guardia)
- Ácido úrico → ``AU`` / «Uricemia» (no forma parte del allowlist de guardia)
"""
from __future__ import annotations

from typing import Iterable

from laboratorio.catalogo_solicitud_papel import (
    COMPONENTES_EAB_ART,
    COMPONENTES_EAB_VEN,
    PANELES,
)
from laboratorio.origen_solicitud import GUARDIA, normalizar_origen_solicitud

# Paneles explícitamente pedibles en guardia.
PANELES_GUARDIA_PERMITIDOS = frozenset(
    {
        "PAN_HEMO",
        "PAN_IONO",
        "PAN_HEP",
        "PAN_EAB_ART",
        "PAN_EAB_VEN",
    }
)

# Exámenes sueltos pedibles en guardia (códigos TipoExamen).
EXAMENES_GUARDIA_PERMITIDOS = frozenset(
    {
        "GLU",
        "UREA",
        "CREATI",
        "TROP_US",
        "TROP_I",
        "CPK_MB",
        "CPK",
        "MIOG",
    }
)


def _componentes_de_paneles_permitidos() -> frozenset[str]:
    """Componentes de paneles del allowlist (p. ej. tras expansión)."""
    by_code = {p["codigo"]: p for p in PANELES}
    out: set[str] = set()
    for codigo in PANELES_GUARDIA_PERMITIDOS:
        panel = by_code.get(codigo)
        if not panel:
            continue
        for c in panel.get("componentes") or []:
            out.add(str(c).strip().upper())
    # EAB: listas canónicas (FIO2 compartido).
    out.update(c.upper() for c in COMPONENTES_EAB_ART)
    out.update(c.upper() for c in COMPONENTES_EAB_VEN)
    return frozenset(out)


COMPONENTES_GUARDIA_PERMITIDOS = _componentes_de_paneles_permitidos()

MENSAJE_EXAMEN_NO_PERMITIDO_GUARDIA = (
    "En guardia solo se pueden pedir: hemograma, ionograma plasmático, "
    "glucemia, uremia, creatininemia, hepatograma, enzimas cardíacas "
    "(troponina I ultrasensible, troponina I, CPK-MB, CPK, mioglobina) "
    "y EAB arterial/venoso. No permitido: {codigos}."
)


class GuardiaCatalogoError(ValueError):
    """Pedido con exámenes/paneles fuera del catálogo de guardia."""


def origen_es_guardia(origen: str | None) -> bool:
    o = normalizar_origen_solicitud(origen) or (origen or "")
    return (o or "").strip().upper() == GUARDIA


def assert_examenes_permitidos_en_guardia(
    *,
    origen_solicitud: str | None,
    examenes_ids: Iterable[int] | None = None,
    paneles_ids: Iterable[int] | None = None,
) -> None:
    """
    Fail-closed si origen es GUARDIA y hay paneles/exámenes fuera del allowlist.

    No-op si el origen no es guardia o no hay ítems.
    """
    if not origen_es_guardia(origen_solicitud):
        return

    from laboratorio.models import PanelExamen, TipoExamen

    exam_ids = {int(x) for x in (examenes_ids or []) if x is not None}
    panel_ids = {int(x) for x in (paneles_ids or []) if x is not None}
    if not exam_ids and not panel_ids:
        return

    rechazados: list[str] = []

    if panel_ids:
        for panel in PanelExamen.objects.filter(pk__in=panel_ids).only("id", "codigo", "nombre"):
            codigo = (panel.codigo or "").strip().upper()
            if codigo not in PANELES_GUARDIA_PERMITIDOS:
                rechazados.append(codigo or f"panel#{panel.pk}")

    if exam_ids:
        for te in TipoExamen.objects.filter(pk__in=exam_ids).only("id", "codigo", "nombre"):
            codigo = (te.codigo or "").strip().upper()
            if (
                codigo in EXAMENES_GUARDIA_PERMITIDOS
                or codigo in COMPONENTES_GUARDIA_PERMITIDOS
                or codigo in PANELES_GUARDIA_PERMITIDOS
            ):
                continue
            rechazados.append(codigo or f"examen#{te.pk}")

    if rechazados:
        uniq = sorted(set(rechazados))
        raise GuardiaCatalogoError(
            MENSAJE_EXAMEN_NO_PERMITIDO_GUARDIA.format(codigos=", ".join(uniq[:12]))
        )
