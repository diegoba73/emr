"""Helpers de lista de problemas clínicos (diagnóstico unificado)."""
from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone


def texto_problema_display(problema) -> str:
    if problema is None:
        return ""
    return (problema.display_texto() or "").strip()


def problema_principal_activo(paciente_id: int | None):
    """Problema ACTIVO marcado como principal, o None."""
    if not paciente_id:
        return None
    from pacientes.models import ProblemaClinico

    return (
        ProblemaClinico.objects.filter(
            paciente_id=paciente_id,
            estado=ProblemaClinico.ESTADO_ACTIVO,
            es_principal=True,
        )
        .select_related("diagnostico_cie")
        .order_by("id")
        .first()
    )


def diagnostico_vigente_texto(paciente_id: int | None) -> str:
    """Texto del principal activo (pedidos/OS). Vacío si no hay."""
    return texto_problema_display(problema_principal_activo(paciente_id))


def diagnostico_vigente_snapshot(paciente_id: int | None) -> tuple[str, int | None]:
    """(texto, cie_id) del principal activo para congelar en una orden."""
    prob = problema_principal_activo(paciente_id)
    if prob is None:
        return "", None
    return texto_problema_display(prob), getattr(prob, "diagnostico_cie_id", None)


def asegurar_unica_principal(problema) -> None:
    """Si el problema es principal activo, quita el flag a los demás activos."""
    from pacientes.models import ProblemaClinico

    if not problema.es_principal or problema.estado != ProblemaClinico.ESTADO_ACTIVO:
        return
    ProblemaClinico.objects.filter(
        paciente_id=problema.paciente_id,
        es_principal=True,
        estado=ProblemaClinico.ESTADO_ACTIVO,
    ).exclude(pk=problema.pk).update(es_principal=False)


@transaction.atomic
def crear_problema(
    paciente,
    *,
    texto: str,
    diagnostico_cie=None,
    es_principal: bool = False,
    notas: str = "",
    actor=None,
) -> Any:
    from pacientes.models import ProblemaClinico

    texto_norm = " ".join((texto or "").split()).strip()
    if not texto_norm:
        raise ValueError("El texto del problema es obligatorio.")

    has_principal = ProblemaClinico.objects.filter(
        paciente_id=paciente.pk,
        estado=ProblemaClinico.ESTADO_ACTIVO,
        es_principal=True,
    ).exists()
    if not has_principal:
        es_principal = True

    if es_principal:
        ProblemaClinico.objects.filter(
            paciente_id=paciente.pk,
            es_principal=True,
            estado=ProblemaClinico.ESTADO_ACTIVO,
        ).update(es_principal=False)

    problema = ProblemaClinico(
        paciente=paciente,
        texto=texto_norm,
        diagnostico_cie=diagnostico_cie,
        estado=ProblemaClinico.ESTADO_ACTIVO,
        es_principal=bool(es_principal),
        notas=(notas or "").strip(),
        creado_por=actor if getattr(actor, "is_authenticated", False) else None,
        modificado_por=actor if getattr(actor, "is_authenticated", False) else None,
    )
    problema.save()
    return problema


@transaction.atomic
def actualizar_problema(
    problema,
    *,
    texto: str | None = None,
    diagnostico_cie=...,
    es_principal: bool | None = None,
    estado: str | None = None,
    notas: str | None = None,
    actor=None,
) -> Any:
    from pacientes.models import ProblemaClinico

    if texto is not None:
        texto_norm = " ".join(texto.split()).strip()
        if not texto_norm:
            raise ValueError("El texto del problema no puede quedar vacío.")
        problema.texto = texto_norm
    if diagnostico_cie is not ...:
        problema.diagnostico_cie = diagnostico_cie
    if notas is not None:
        problema.notas = (notas or "").strip()
    if estado is not None:
        if estado not in {ProblemaClinico.ESTADO_ACTIVO, ProblemaClinico.ESTADO_RESUELTO}:
            raise ValueError("Estado de problema inválido.")
        problema.estado = estado
        if estado == ProblemaClinico.ESTADO_RESUELTO:
            problema.es_principal = False
            if problema.resuelto_en is None:
                problema.resuelto_en = timezone.now()
        elif estado == ProblemaClinico.ESTADO_ACTIVO:
            problema.resuelto_en = None
    if es_principal is not None and problema.estado == ProblemaClinico.ESTADO_ACTIVO:
        problema.es_principal = bool(es_principal)

    if getattr(actor, "is_authenticated", False):
        problema.modificado_por = actor

    if problema.es_principal and problema.estado == ProblemaClinico.ESTADO_ACTIVO:
        ProblemaClinico.objects.filter(
            paciente_id=problema.paciente_id,
            es_principal=True,
            estado=ProblemaClinico.ESTADO_ACTIVO,
        ).exclude(pk=problema.pk).update(es_principal=False)

    problema.save()

    # Si no queda principal activo, promover el más reciente activo.
    if not ProblemaClinico.objects.filter(
        paciente_id=problema.paciente_id,
        estado=ProblemaClinico.ESTADO_ACTIVO,
        es_principal=True,
    ).exists():
        otro = (
            ProblemaClinico.objects.filter(
                paciente_id=problema.paciente_id,
                estado=ProblemaClinico.ESTADO_ACTIVO,
            )
            .order_by("-actualizado_en", "id")
            .first()
        )
        if otro is not None:
            otro.es_principal = True
            otro.save(update_fields=["es_principal", "actualizado_en"])
    return problema


@transaction.atomic
def establecer_principal_desde_texto(
    paciente,
    *,
    texto: str,
    diagnostico_cie=None,
    actor=None,
    notas: str = "",
) -> Any:
    """Alta/egreso: crea o actualiza el principal activo con el texto dado."""
    from pacientes.models import ProblemaClinico

    texto_norm = " ".join((texto or "").split()).strip()
    if not texto_norm and diagnostico_cie is not None:
        codigo = (getattr(diagnostico_cie, "codigo", None) or "").strip()
        desc = (getattr(diagnostico_cie, "descripcion", None) or "").strip()
        texto_norm = f"{codigo} - {desc}".strip(" -") if (codigo or desc) else ""
    if not texto_norm:
        raise ValueError("Se requiere texto o CIE para el diagnóstico principal.")

    actual = problema_principal_activo(paciente.pk)
    if actual is not None:
        return actualizar_problema(
            actual,
            texto=texto_norm,
            diagnostico_cie=diagnostico_cie if diagnostico_cie is not None else actual.diagnostico_cie,
            es_principal=True,
            estado=ProblemaClinico.ESTADO_ACTIVO,
            notas=notas if notas else None,
            actor=actor,
        )
    return crear_problema(
        paciente,
        texto=texto_norm,
        diagnostico_cie=diagnostico_cie,
        es_principal=True,
        notas=notas,
        actor=actor,
    )
