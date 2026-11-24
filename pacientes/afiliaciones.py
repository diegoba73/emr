"""Helpers de afiliaciones de obra social (catálogo ObraSocial)."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from pacientes.obras_sociales import resolve_obra_social
from pacientes.texto import normalizar_texto_paciente


def sync_paciente_desde_principal(paciente) -> None:
    """Copia la afiliación principal activa a ``Paciente.obra_social`` / afiliado / plan."""
    from pacientes.models import PacienteAfiliacion

    principal = (
        PacienteAfiliacion.objects.filter(
            paciente_id=paciente.pk, activo=True, es_principal=True
        )
        .select_related('obra_social')
        .order_by('id')
        .first()
    )
    if principal is None:
        os_obj, afil, plan = None, '', ''
    else:
        os_obj = principal.obra_social
        afil = (principal.numero_afiliado or '').strip()
        plan = (principal.plan or '').strip()

    update_fields: list[str] = []
    if paciente.obra_social_id != (os_obj.pk if os_obj else None):
        paciente.obra_social = os_obj
        update_fields.append('obra_social')
    if (paciente.numero_afiliado or '') != afil:
        paciente.numero_afiliado = afil or None
        update_fields.append('numero_afiliado')
    if (paciente.plan_obra_social or '') != plan:
        paciente.plan_obra_social = plan
        update_fields.append('plan_obra_social')
    if update_fields:
        paciente.save(update_fields=update_fields)


def asegurar_unica_principal(afiliacion) -> None:
    """Si ``afiliacion`` es principal activa, quita el flag a las demás."""
    if not afiliacion.es_principal or not afiliacion.activo:
        return
    from pacientes.models import PacienteAfiliacion

    PacienteAfiliacion.objects.filter(
        paciente_id=afiliacion.paciente_id,
        es_principal=True,
        activo=True,
    ).exclude(pk=afiliacion.pk).update(es_principal=False)


@transaction.atomic
def upsert_afiliacion(
    paciente,
    *,
    obra_social: Any,
    numero_afiliado: str | None = '',
    plan: str | None = None,
    marcar_principal: bool = True,
) -> Any | None:
    """Crea o reutiliza afiliación por OS+afiliado. Vacío → None (no toca).

    ``obra_social`` puede ser id, código o instancia ``ObraSocial``.
    ``plan`` None = no tocar el plan existente; str = setear (puede ser vacío).
    """
    from pacientes.models import PacienteAfiliacion

    os_obj = resolve_obra_social(obra_social)
    afil_norm = normalizar_texto_paciente(numero_afiliado) or ''
    if os_obj is None:
        return None

    existing = (
        PacienteAfiliacion.objects.select_for_update()
        .filter(
            paciente_id=paciente.pk,
            obra_social_id=os_obj.pk,
            numero_afiliado=afil_norm,
            activo=True,
        )
        .order_by('-es_principal', 'id')
        .first()
    )
    if existing is None:
        existing = (
            PacienteAfiliacion.objects.select_for_update()
            .filter(
                paciente_id=paciente.pk,
                obra_social_id=os_obj.pk,
                numero_afiliado=afil_norm,
                activo=False,
            )
            .order_by('id')
            .first()
        )

    has_principal = PacienteAfiliacion.objects.filter(
        paciente_id=paciente.pk, activo=True, es_principal=True
    ).exists()
    want_principal = bool(marcar_principal) or not has_principal

    if want_principal:
        PacienteAfiliacion.objects.filter(
            paciente_id=paciente.pk, es_principal=True, activo=True
        ).update(es_principal=False)

    plan_norm = None if plan is None else (normalizar_texto_paciente(plan) or '')

    if existing is not None:
        existing.activo = True
        existing.es_principal = want_principal or existing.es_principal
        if want_principal:
            existing.es_principal = True
        if plan_norm is not None:
            existing.plan = plan_norm
        existing.save()
    else:
        existing = PacienteAfiliacion(
            paciente=paciente,
            obra_social=os_obj,
            numero_afiliado=afil_norm,
            plan=plan_norm or '',
            es_principal=want_principal,
            activo=True,
        )
        existing.save()

    if existing.es_principal:
        sync_paciente_desde_principal(paciente)
    return existing


@transaction.atomic
def sync_principal_desde_paciente_fields(paciente) -> Any | None:
    """Tras PATCH demográfico: refleja obra_social/afiliado/plan en afiliaciones."""
    if not paciente.obra_social_id:
        return None
    afil_norm = normalizar_texto_paciente(paciente.numero_afiliado) or ''
    plan_norm = normalizar_texto_paciente(paciente.plan_obra_social) or ''
    return upsert_afiliacion(
        paciente,
        obra_social=paciente.obra_social,
        numero_afiliado=afil_norm,
        plan=plan_norm,
        marcar_principal=True,
    )


def normalizar_snapshot_os(
    obra_social: Any,
    numero_afiliado: str | None = '',
) -> tuple[str, str]:
    """Devuelve (label OS, afiliado) para snapshot LIMS; OS vacío → ('', '')."""
    from pacientes.models import ObraSocial
    from pacientes.obras_sociales import label_obra_social

    if isinstance(obra_social, ObraSocial):
        os_label = label_obra_social(obra_social)
    else:
        os_obj = resolve_obra_social(obra_social, allow_inactive=True)
        if os_obj is not None:
            os_label = label_obra_social(os_obj)
        else:
            os_label = normalizar_texto_paciente(obra_social) or ''
    if not os_label:
        return '', ''
    afil_norm = normalizar_texto_paciente(numero_afiliado) or ''
    return os_label, afil_norm
