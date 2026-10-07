"""Helpers de afiliaciones de obra social (fase 1, texto libre)."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from pacientes.texto import normalizar_texto_paciente


def sync_paciente_desde_principal(paciente) -> None:
    """Copia la afiliación principal activa a ``Paciente.obra_social`` / afiliado."""
    from pacientes.models import PacienteAfiliacion

    principal = (
        PacienteAfiliacion.objects.filter(
            paciente_id=paciente.pk, activo=True, es_principal=True
        )
        .order_by("id")
        .first()
    )
    if principal is None:
        os_val, afil = "", ""
    else:
        os_val = (principal.obra_social or "").strip()
        afil = (principal.numero_afiliado or "").strip()

    update_fields: list[str] = []
    if (paciente.obra_social or "") != os_val:
        paciente.obra_social = os_val or None
        update_fields.append("obra_social")
    if (paciente.numero_afiliado or "") != afil:
        paciente.numero_afiliado = afil or None
        update_fields.append("numero_afiliado")
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
    obra_social: str | None,
    numero_afiliado: str | None = "",
    marcar_principal: bool = True,
) -> Any | None:
    """Crea o reutiliza afiliación por OS+afiliado. Vacío → None (no toca).

    Si ``marcar_principal``, la deja como principal y sincroniza el paciente.
    """
    from pacientes.models import PacienteAfiliacion

    os_norm = normalizar_texto_paciente(obra_social) or ""
    afil_norm = normalizar_texto_paciente(numero_afiliado) or ""
    if not os_norm:
        return None

    existing = (
        PacienteAfiliacion.objects.select_for_update()
        .filter(
            paciente_id=paciente.pk,
            obra_social=os_norm,
            numero_afiliado=afil_norm,
            activo=True,
        )
        .order_by("-es_principal", "id")
        .first()
    )
    if existing is None:
        # Reactivar inactiva igual si existe.
        existing = (
            PacienteAfiliacion.objects.select_for_update()
            .filter(
                paciente_id=paciente.pk,
                obra_social=os_norm,
                numero_afiliado=afil_norm,
                activo=False,
            )
            .order_by("id")
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

    if existing is not None:
        existing.activo = True
        existing.es_principal = want_principal or existing.es_principal
        if want_principal:
            existing.es_principal = True
        existing.save()
    else:
        existing = PacienteAfiliacion(
            paciente=paciente,
            obra_social=os_norm,
            numero_afiliado=afil_norm,
            es_principal=want_principal,
            activo=True,
        )
        existing.save()

    if existing.es_principal:
        sync_paciente_desde_principal(paciente)
    return existing

@transaction.atomic
def sync_principal_desde_paciente_fields(paciente) -> Any | None:
    """Tras PATCH demográfico legacy: refleja obra_social/afiliado en afiliaciones."""
    os_norm = normalizar_texto_paciente(paciente.obra_social) or ""
    afil_norm = normalizar_texto_paciente(paciente.numero_afiliado) or ""
    if not os_norm:
        return None
    return upsert_afiliacion(
        paciente,
        obra_social=os_norm,
        numero_afiliado=afil_norm,
        marcar_principal=True,
    )


def normalizar_snapshot_os(
    obra_social: str | None,
    numero_afiliado: str | None = "",
) -> tuple[str, str]:
    """Devuelve (obra_social, afiliado) normalizados; OS vacío → ('', '')."""
    os_norm = normalizar_texto_paciente(obra_social) or ""
    if not os_norm:
        return "", ""
    afil_norm = normalizar_texto_paciente(numero_afiliado) or ""
    return os_norm, afil_norm
