"""
Orden de grupos (paneles y exámenes sueltos) en el informe PDF y la UI LIMS.

Reglas por defecto:
- Orden del formulario papel «Solicitud de análisis» (fila a fila, izq → der).
- Determinaciones de orina (ionograma urinario, clearance, microalbuminuria,
  proteinurias, orina completa, etc.) van al **final** del informe.
- Dentro del bloque orina, **orina completa (PAN_ORI)** va siempre al final.
- Perfiles/paneles agrupan sus componentes; si no hay panel pedido, se infiere
  por códigos del catálogo cuando hay suficientes analitos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, TypeVar

from laboratorio.catalogo_solicitud_papel import ORDEN_FORMULARIO_PAPEL, PANELES
from laboratorio.panel_componentes_orden import ordenar_resultados_por_panel

T = TypeVar("T")

PANEL_HEMOGRAMA = "PAN_HEMO"
PANEL_ORINA_COMPLETA = "PAN_ORI"

# Perfiles/paneles de orina (bloque final del informe).
PANELES_ORINA = frozenset(
    {
        "PAN_ORI",
        "PAN_IONO_U",
        "PAN_IONO_U24",
        "PAN_MALB_AZ",
        "PAN_MALB24",
        "PAN_CLEAR",
    }
)
CODIGOS_ORINA_SUELTOS = frozenset({"PROT_U_24", "PROT_U_AZ"})
MUESTRAS_ORINA = frozenset({"ORINA", "ORINA_24_H"})

ORDEN_PAPEL_RANK: dict[str, int] = {
    codigo: idx for idx, codigo in enumerate(ORDEN_FORMULARIO_PAPEL)
}


def grupo_key_panel(panel_id: int) -> str:
    return f"panel-{panel_id}"


def grupo_key_resultado(resultado_id: int) -> str:
    return f"resultado-{resultado_id}"


def grupo_key_inferido(panel_codigo: str) -> str:
    return f"inferido-{panel_codigo}"


@dataclass
class GrupoInformeSpec:
    key: str
    titulo: str
    panel_codigo: str | None = None
    resultados: list = field(default_factory=list)

    @property
    def es_perfil(self) -> bool:
        """True si el bloque es un panel/perfil (lleva encabezado en el PDF)."""
        return bool(self.panel_codigo)


def _es_orina_panel(codigo: str | None) -> bool:
    return bool(codigo and codigo in PANELES_ORINA)


def _codigo_tipo_examen(res) -> str:
    te = getattr(res, "tipo_examen", None)
    if te is not None and hasattr(te, "codigo"):
        return str(te.codigo or "").strip().upper()
    if hasattr(res, "tipo_examen_codigo"):
        return str(res.tipo_examen_codigo or "").strip().upper()
    return ""


def _codigo_muestra_resultado(res) -> str:
    te = getattr(res, "tipo_examen", None)
    tm = getattr(te, "tipo_muestra_requerida", None) if te else None
    if tm is not None:
        return str(getattr(tm, "codigo", None) or "").strip().upper()
    if hasattr(res, "tipo_examen_muestra_codigo"):
        return str(res.tipo_examen_muestra_codigo or "").strip().upper()
    return ""


def _es_orina_resultado(res) -> bool:
    codigo = _codigo_tipo_examen(res)
    if codigo in CODIGOS_ORINA_SUELTOS:
        return True
    return _codigo_muestra_resultado(res) in MUESTRAS_ORINA


def _codigo_grupo(grupo: GrupoInformeSpec) -> str:
    if grupo.panel_codigo:
        return str(grupo.panel_codigo).strip().upper()
    if grupo.resultados:
        return _codigo_tipo_examen(grupo.resultados[0])
    return ""


def es_grupo_orina(grupo: GrupoInformeSpec) -> bool:
    """True si el bloque debe ir al final del informe (muestra orina / perfil orina)."""
    if _es_orina_panel(grupo.panel_codigo):
        return True
    if grupo.resultados and _es_orina_resultado(grupo.resultados[0]):
        # Paneles mixtos no-orina no deberían caer acá (tienen panel_codigo no-orina).
        if grupo.panel_codigo and not _es_orina_panel(grupo.panel_codigo):
            return False
        return True
    return False


def prioridad_grupo_default(grupo: GrupoInformeSpec) -> tuple:
    """Clave de orden: papel → resto → bloque orina (orina completa al final)."""
    codigo = _codigo_grupo(grupo)

    if es_grupo_orina(grupo):
        # Orina completa siempre última dentro del bloque orina.
        if codigo == PANEL_ORINA_COMPLETA:
            sub = 10_000
        else:
            sub = ORDEN_PAPEL_RANK.get(codigo, 5_000)
        return (2, sub, grupo.titulo, grupo.key)

    if codigo and codigo in ORDEN_PAPEL_RANK:
        return (0, ORDEN_PAPEL_RANK[codigo], grupo.titulo, grupo.key)

    # Fuera del formulario (no orina): hemograma / paneles / sueltos.
    if grupo.panel_codigo == PANEL_HEMOGRAMA:
        bucket = 0
    elif grupo.panel_codigo:
        bucket = 1
    else:
        bucket = 2
    return (1, bucket, grupo.titulo, grupo.key)


def _inferir_perfiles_por_codigo(
    restantes: list,
    codigos_panel_ya_usados: set[str],
) -> tuple[list[GrupoInformeSpec], list]:
    """Agrupa analitos sueltos en perfiles del catálogo cuando hay match suficiente."""
    pool = list(restantes)
    grupos: list[GrupoInformeSpec] = []

    for panel_def in PANELES:
        codigo = panel_def["codigo"]
        if codigo in codigos_panel_ya_usados:
            continue
        componentes = [c.strip().upper() for c in panel_def["componentes"]]
        set_comp = set(componentes)
        match = [r for r in pool if _codigo_tipo_examen(r) in set_comp]
        umbral = min(2, len(componentes))
        if len(match) < umbral:
            continue
        match_ids = {r.id for r in match}
        rows = ordenar_resultados_por_panel(codigo, match)
        grupos.append(
            GrupoInformeSpec(
                key=grupo_key_inferido(codigo),
                titulo=panel_def["nombre"].upper(),
                panel_codigo=codigo,
                resultados=rows,
            )
        )
        pool = [r for r in pool if r.id not in match_ids]

    return grupos, pool


def construir_grupos_informe(solicitud, resultados: Iterable) -> list[GrupoInformeSpec]:
    """Agrupa resultados: un bloque por panel/perfil y un bloque por examen suelto."""
    paneles = list(solicitud.paneles.prefetch_related("tipos_examen").all())
    asignados: set[int] = set()
    grupos: list[GrupoInformeSpec] = []
    codigos_panel_usados: set[str] = set()

    for panel in paneles:
        ids_panel = {te.id for te in panel.tipos_examen.all()}
        rows = ordenar_resultados_por_panel(
            panel.codigo,
            [r for r in resultados if r.tipo_examen_id in ids_panel],
        )
        for r in rows:
            asignados.add(r.id)
        if panel.codigo:
            codigos_panel_usados.add(str(panel.codigo).strip().upper())
        if rows:
            grupos.append(
                GrupoInformeSpec(
                    key=grupo_key_panel(panel.pk),
                    titulo=panel.nombre.upper(),
                    panel_codigo=panel.codigo,
                    resultados=rows,
                )
            )

    otros = [r for r in resultados if r.id not in asignados]
    inferidos, sobrantes = _inferir_perfiles_por_codigo(otros, codigos_panel_usados)
    grupos.extend(inferidos)

    for r in sobrantes:
        te = getattr(r, "tipo_examen", None)
        titulo = (getattr(te, "nombre", None) or "EXAMEN").upper()
        grupos.append(
            GrupoInformeSpec(
                key=grupo_key_resultado(r.id),
                titulo=titulo,
                resultados=[r],
            )
        )

    return grupos


def ordenar_grupos_por_defecto(grupos: list[GrupoInformeSpec]) -> list[GrupoInformeSpec]:
    return sorted(grupos, key=prioridad_grupo_default)


def aplicar_orden_grupos(
    grupos: list[GrupoInformeSpec],
    orden_custom: list[str] | None,
) -> list[GrupoInformeSpec]:
    if not orden_custom:
        return ordenar_grupos_por_defecto(grupos)

    by_key = {g.key: g for g in grupos}
    ordered: list[GrupoInformeSpec] = []
    seen: set[str] = set()
    for key in orden_custom:
        if key in by_key and key not in seen:
            ordered.append(by_key[key])
            seen.add(key)

    rest = [g for g in grupos if g.key not in seen]
    if rest:
        ordered.extend(ordenar_grupos_por_defecto(rest))
    return ordered


def claves_grupos_validas(solicitud, resultados: Iterable) -> set[str]:
    return {g.key for g in construir_grupos_informe(solicitud, resultados)}


def validar_orden_grupos(orden: list, claves_validas: set[str]) -> list[str] | None:
    if not isinstance(orden, list):
        return None
    out: list[str] = []
    seen: set[str] = set()
    for item in orden:
        if not isinstance(item, str):
            return None
        if item not in claves_validas or item in seen:
            continue
        out.append(item)
        seen.add(item)
    return out
