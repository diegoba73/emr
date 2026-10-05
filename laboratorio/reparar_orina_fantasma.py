"""
Reparación quirúrgica: quita prácticas de orina fantasma sin resultado clínico.

No toca creatininemia ni paneles de sangre. No toca filas con valor real,
validación o muestra asociada. LAB-2026-00119 queda fuera del default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from django.db import transaction

from laboratorio.audit_paneles_fantasma import (
    NUMEROS_REPARAR_ORINA,
    _norm,
    _valor_sin_resultado_clinico,
)
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen

# Solo orina / clearance urinario. Nunca CREATI ni NA/K/CL plasmáticos.
CODIGOS_ORINA_FANTASMA = frozenset(
    {
        "NA_U",
        "K_U",
        "CL_U",
        "NA_U24",
        "K_U24",
        "CL_U24",
        "DIUR",
        "CREA_U",
        "CLEAR_CREA",
        "MICROALB",
        "MICROALB_24",
        "PROT_U_EQ",
        "PROT_U_24",
        "PROT_U_AZ",
    }
)


@dataclass
class AccionFila:
    resultado_id: int
    codigo: str
    valor: str
    accion: str  # borrar | conservar_resultado | conservar_validado | conservar_muestra | fuera_de_alcance
    detalle: str = ""


@dataclass
class PlanOrden:
    id: int
    numero: str
    estado: str
    acciones: list[AccionFila] = field(default_factory=list)
    tipos_a_quitar: list[str] = field(default_factory=list)

    @property
    def a_borrar(self) -> list[AccionFila]:
        return [a for a in self.acciones if a.accion == "borrar"]


def planificar_orden(solicitud: SolicitudExamen) -> PlanOrden:
    plan = PlanOrden(
        id=solicitud.pk,
        numero=solicitud.numero or "",
        estado=solicitud.estado or "",
    )
    resultados = list(
        solicitud.resultados.select_related("tipo_examen").all()
    )
    codigos_borrar: set[str] = set()

    for r in resultados:
        codigo = _norm(r.tipo_examen.codigo) if r.tipo_examen_id else ""
        if not codigo:
            continue
        if codigo not in CODIGOS_ORINA_FANTASMA:
            plan.acciones.append(
                AccionFila(
                    resultado_id=r.pk,
                    codigo=codigo,
                    valor=r.valor_obtenido or "",
                    accion="fuera_de_alcance",
                    detalle="no es práctica de orina del set fantasma",
                )
            )
            continue

        valor = r.valor_obtenido or ""
        if r.validado_por_id or r.fecha_validacion:
            plan.acciones.append(
                AccionFila(
                    resultado_id=r.pk,
                    codigo=codigo,
                    valor=valor,
                    accion="conservar_validado",
                    detalle="validado: no se borra",
                )
            )
            continue
        if r.muestra_id:
            plan.acciones.append(
                AccionFila(
                    resultado_id=r.pk,
                    codigo=codigo,
                    valor=valor,
                    accion="conservar_muestra",
                    detalle=f"tiene muestra_id={r.muestra_id}: no se borra",
                )
            )
            continue
        if not _valor_sin_resultado_clinico(valor):
            plan.acciones.append(
                AccionFila(
                    resultado_id=r.pk,
                    codigo=codigo,
                    valor=valor,
                    accion="conservar_resultado",
                    detalle="tiene valor clínico: no se borra",
                )
            )
            continue

        plan.acciones.append(
            AccionFila(
                resultado_id=r.pk,
                codigo=codigo,
                valor=valor,
                accion="borrar",
                detalle="orina fantasma sin resultado/muestra/validación",
            )
        )
        codigos_borrar.add(codigo)

    # Quitar del M2M solo códigos que vamos a borrar por completo en la orden.
    tipos_en_orden = {
        _norm(te.codigo): te
        for te in solicitud.tipos_examen.all()
        if _norm(te.codigo)
    }
    for codigo in sorted(codigos_borrar):
        if codigo in tipos_en_orden:
            plan.tipos_a_quitar.append(codigo)

    return plan


def planificar_por_numeros(numeros: Iterable[str]) -> list[PlanOrden]:
    nums = [n.strip() for n in numeros if n and n.strip()]
    if not nums:
        return []
    qs = (
        SolicitudExamen.objects.filter(numero__in=nums)
        .prefetch_related("tipos_examen", "resultados__tipo_examen")
    )
    by_num = {s.numero: s for s in qs}
    out: list[PlanOrden] = []
    for num in nums:
        sol = by_num.get(num)
        if sol is None:
            out.append(PlanOrden(id=0, numero=num, estado="NO_ENCONTRADA"))
            continue
        out.append(planificar_orden(sol))
    return out


def aplicar_plan(planes: Iterable[PlanOrden]) -> dict[str, int]:
    """Aplica borrados. Devuelve contadores. No hace dry-run."""
    stats = {
        "ordenes": 0,
        "resultados_borrados": 0,
        "tipos_desvinculados": 0,
        "omitidas": 0,
        "bloqueados_recheck": 0,
    }
    with transaction.atomic():
        for plan in planes:
            if plan.estado == "NO_ENCONTRADA" or plan.id == 0:
                stats["omitidas"] += 1
                continue
            ids_plan = [a.resultado_id for a in plan.a_borrar]
            if not ids_plan and not plan.tipos_a_quitar:
                continue
            sol = SolicitudExamen.objects.select_for_update().get(pk=plan.id)
            borrados_codigos: set[str] = set()
            for rid in ids_plan:
                try:
                    r = ResultadoExamen.objects.select_for_update().get(
                        pk=rid, solicitud_id=sol.pk
                    )
                except ResultadoExamen.DoesNotExist:
                    stats["bloqueados_recheck"] += 1
                    continue
                codigo = _norm(r.tipo_examen.codigo)
                if codigo not in CODIGOS_ORINA_FANTASMA:
                    stats["bloqueados_recheck"] += 1
                    continue
                if r.muestra_id or r.validado_por_id or r.fecha_validacion:
                    stats["bloqueados_recheck"] += 1
                    continue
                if not _valor_sin_resultado_clinico(r.valor_obtenido):
                    stats["bloqueados_recheck"] += 1
                    continue
                r.delete()
                stats["resultados_borrados"] += 1
                borrados_codigos.add(codigo)
            if borrados_codigos:
                tipos = list(
                    TipoExamen.objects.filter(codigo__in=borrados_codigos)
                )
                before = sol.tipos_examen.filter(
                    codigo__in=borrados_codigos
                ).count()
                if tipos:
                    sol.tipos_examen.remove(*tipos)
                stats["tipos_desvinculados"] += before
            stats["ordenes"] += 1
    return stats


def numeros_default_reparacion() -> tuple[str, ...]:
    return NUMEROS_REPARAR_ORINA
