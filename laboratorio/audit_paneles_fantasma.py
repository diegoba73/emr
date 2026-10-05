"""
Análisis (solo lectura) de expansión fantasma de paneles por componentes compartidos.

Detecta resultados típicos del bug corregido en ``asegurar_resultados_paneles_derivados``
(O5): p. ej. ionograma orina → ionograma 24 hs; microalb azar → 24 hs; creatinina → clearance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from laboratorio.models import SolicitudExamen
from laboratorio.panel_componentes_orden import PANEL_COMPONENTES_BY_CODIGO

# Paneles que el bug expandía al ver un componente compartido.
PANELES_RIESGO = (
    "PAN_IONO_U24",
    "PAN_MALB24",
    "PAN_CLEAR",
    "PAN_PROT24",
)

# Marcadores casi exclusivos de cada panel de riesgo (no se piden sueltos en la práctica).
FIRMAS_POR_PANEL: dict[str, frozenset[str]] = {
    "PAN_IONO_U24": frozenset({"NA_U24", "K_U24", "CL_U24"}),
    "PAN_MALB24": frozenset({"MICROALB_24"}),
    "PAN_CLEAR": frozenset({"CLEAR_CREA"}),
    "PAN_PROT24": frozenset({"PROT_U_24"}),
}

# Pedidos típicos que disparaban el bug; no marcarlos como arrastre a borrar.
SEMILLAS_PEDIDO = frozenset(
    {
        "CREATI",
        "NA_U",
        "K_U",
        "CL_U",
        "MICROALB",
        "PROT_U_EQ",
    }
)

NUMEROS_DEFAULT = (
    "LAB-2026-00107",
    "LAB-2026-00109",
    "LAB-2026-00113",
    "LAB-2026-00116",
    "LAB-2026-00119",
    "LAB-2026-00122",
    "LAB-2026-00123",
)

# Reparación automática: sin 00119 (requiere revisión especial).
NUMEROS_REPARAR_ORINA = (
    "LAB-2026-00107",
    "LAB-2026-00109",
    "LAB-2026-00113",
    "LAB-2026-00116",
    "LAB-2026-00122",
    "LAB-2026-00123",
)


def _norm(codigo: str | None) -> str:
    return (codigo or "").strip().upper()


def codigos_justificados_por_paneles(paneles: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for panel in paneles:
        for c in PANEL_COMPONENTES_BY_CODIGO.get(_norm(panel), []) or []:
            if c:
                out.add(_norm(c))
    return out


def _valor_sin_resultado_clinico(valor: str | None) -> bool:
    """Vacío o placeholder de cálculo automático (no es resultado cargado)."""
    from laboratorio.calculos_derivados import RESULTADO_NO_CALCULABLE

    texto = (valor or "").strip()
    if not texto:
        return True
    return texto == RESULTADO_NO_CALCULABLE


def _valor_vacio(valor: str | None) -> bool:
    return _valor_sin_resultado_clinico(valor)


@dataclass
class FilaResultado:
    id: int
    codigo: str
    valor: str
    tiene_muestra: bool
    muestra_id: int | None
    validado: bool
    en_tipos_examen: bool
    clasificacion: str  # candidato_borrar | revisar_manual | justificado | compartido_revisar


@dataclass
class SospechaPanel:
    panel: str
    firmas_presentes: list[str]
    componentes_presentes: list[str]
    exclusivos_no_justificados: list[str]


@dataclass
class AuditoriaOrden:
    id: int
    numero: str
    estado: str
    paneles: list[str]
    justificados: list[str]
    sospechas: list[SospechaPanel] = field(default_factory=list)
    filas: list[FilaResultado] = field(default_factory=list)
    tubos: list[str] = field(default_factory=list)
    hallazgo: bool = False


def auditar_solicitud(solicitud: SolicitudExamen) -> AuditoriaOrden:
    paneles = sorted(
        {_norm(p.codigo) for p in solicitud.paneles.all() if _norm(p.codigo)}
    )
    justificados = codigos_justificados_por_paneles(paneles)
    tipos = {_norm(te.codigo) for te in solicitud.tipos_examen.all() if _norm(te.codigo)}

    resultados = list(
        solicitud.resultados.select_related("tipo_examen", "muestra").all()
    )
    codigos_res = {
        _norm(r.tipo_examen.codigo)
        for r in resultados
        if r.tipo_examen_id and _norm(r.tipo_examen.codigo)
    }

    sospechas: list[SospechaPanel] = []
    firmas_fantasma: set[str] = set()
    exclusivos_fantasma: set[str] = set()

    for panel in PANELES_RIESGO:
        if panel in paneles:
            continue
        comps = {_norm(c) for c in (PANEL_COMPONENTES_BY_CODIGO.get(panel) or []) if c}
        firmas = set(FIRMAS_POR_PANEL.get(panel, frozenset()))
        firmas_presentes = sorted(firmas & codigos_res)
        if not firmas_presentes:
            continue
        presentes = sorted(comps & codigos_res)
        exclusivos = sorted(c for c in presentes if c not in justificados)
        firmas_fantasma |= set(firmas_presentes)
        exclusivos_fantasma |= set(exclusivos)
        sospechas.append(
            SospechaPanel(
                panel=panel,
                firmas_presentes=firmas_presentes,
                componentes_presentes=presentes,
                exclusivos_no_justificados=exclusivos,
            )
        )

    filas: list[FilaResultado] = []
    for r in sorted(
        resultados,
        key=lambda x: _norm(x.tipo_examen.codigo) if x.tipo_examen_id else "",
    ):
        codigo = _norm(r.tipo_examen.codigo) if r.tipo_examen_id else ""
        if not codigo:
            continue
        valor = r.valor_obtenido or ""
        tiene_muestra = bool(r.muestra_id)
        validado = bool(r.validado_por_id or r.fecha_validacion)
        vacio = _valor_vacio(valor)

        if codigo in justificados:
            clasif = "justificado"
        elif codigo in firmas_fantasma:
            clasif = (
                "candidato_borrar"
                if vacio and not tiene_muestra and not validado
                else "revisar_manual"
            )
        elif codigo in exclusivos_fantasma and codigo not in SEMILLAS_PEDIDO:
            # Compartido arrastrado (DIUR, CREA_U, …) sin panel que lo justifique.
            clasif = "compartido_revisar"
        else:
            # Pedido suelto / semilla / otro panel no listado como riesgo.
            clasif = "justificado"

        filas.append(
            FilaResultado(
                id=r.pk,
                codigo=codigo,
                valor=valor,
                tiene_muestra=tiene_muestra,
                muestra_id=r.muestra_id,
                validado=validado,
                en_tipos_examen=codigo in tipos,
                clasificacion=clasif,
            )
        )

    tubos: list[str] = []
    for m in solicitud.muestras.select_related("tipo_contenedor", "tipo_muestra").all():
        cont = getattr(m.tipo_contenedor, "codigo", None) or "—"
        tm = getattr(m.tipo_muestra, "codigo", None) or "—"
        tubos.append(
            f"id={m.pk} barra={m.codigo_barra or '—'} estado={m.estado} "
            f"muestra={tm} tubo={cont}"
        )

    return AuditoriaOrden(
        id=solicitud.pk,
        numero=solicitud.numero or "",
        estado=solicitud.estado or "",
        paneles=paneles,
        justificados=sorted(justificados),
        sospechas=sospechas,
        filas=filas,
        tubos=tubos,
        hallazgo=bool(sospechas),
    )


def auditar_por_numeros(numeros: Iterable[str]) -> list[AuditoriaOrden]:
    nums = [n.strip() for n in numeros if n and n.strip()]
    if not nums:
        return []
    qs = (
        SolicitudExamen.objects.filter(numero__in=nums)
        .prefetch_related(
            "paneles",
            "tipos_examen",
            "resultados__tipo_examen",
            "muestras__tipo_contenedor",
            "muestras__tipo_muestra",
        )
        .order_by("numero")
    )
    by_num = {s.numero: s for s in qs}
    out: list[AuditoriaOrden] = []
    for num in nums:
        sol = by_num.get(num)
        if sol is None:
            out.append(
                AuditoriaOrden(
                    id=0,
                    numero=num,
                    estado="NO_ENCONTRADA",
                    paneles=[],
                    justificados=[],
                    hallazgo=False,
                )
            )
            continue
        out.append(auditar_solicitud(sol))
    return out
