"""Validación de cobertura (OS + afiliado + plan) para reserva/registro app."""
from __future__ import annotations

from typing import Any

from rest_framework.exceptions import ValidationError

from pacientes.obras_sociales import codigo_obra_social, resolve_obra_social
from pacientes.texto import normalizar_texto_paciente


def es_particular(obra_social: Any) -> bool:
    os_obj = resolve_obra_social(obra_social, allow_inactive=True) if obra_social else None
    if os_obj is None and isinstance(obra_social, str):
        return (obra_social or '').strip().upper() == 'PARTICULAR'
    return codigo_obra_social(os_obj) == 'PARTICULAR'


def cobertura_completa_para_reserva(paciente) -> tuple[bool, str]:
    """
    PARTICULAR: OK sin afiliado/plan.
    Otra OS: exige número de afiliado y plan (espejo o afiliación principal).
    """
    if paciente is None:
        return False, 'No hay ficha de paciente vinculada.'
    os_obj = getattr(paciente, 'obra_social', None)
    if os_obj is None:
        return False, 'Completá tu obra social en la ficha antes de reservar.'
    if es_particular(os_obj):
        return True, ''

    afiliado = (getattr(paciente, 'numero_afiliado', None) or '').strip()
    plan = (getattr(paciente, 'plan_obra_social', None) or '').strip()
    if not plan:
        # Fallback: plan en afiliación principal activa.
        try:
            from pacientes.models import PacienteAfiliacion

            principal = (
                PacienteAfiliacion.objects.filter(
                    paciente_id=paciente.pk, activo=True, es_principal=True
                )
                .only('plan', 'numero_afiliado')
                .first()
            )
            if principal is not None:
                plan = (principal.plan or '').strip()
                if not afiliado:
                    afiliado = (principal.numero_afiliado or '').strip()
        except Exception:
            pass

    if not afiliado:
        return (
            False,
            'Tu ficha de obra social está incompleta: falta el número de afiliado. '
            'Completalo en registro/ajustes o contactá a secretaría.',
        )
    if not plan:
        return (
            False,
            'Tu ficha de obra social está incompleta: falta el plan. '
            'Completalo en registro/ajustes o contactá a secretaría.',
        )
    return True, ''


def assert_cobertura_para_reserva(paciente) -> None:
    ok, msg = cobertura_completa_para_reserva(paciente)
    if not ok:
        raise ValidationError({'detail': msg, 'cobertura_incompleta': True})


def validar_campos_cobertura_registro(
    *,
    obra_social: Any,
    numero_afiliado: str | None = '',
    plan: str | None = '',
) -> dict[str, str]:
    """Devuelve dict de errores de campo; vacío si OK."""
    errors: dict[str, str] = {}
    if es_particular(obra_social):
        return errors
    afil = normalizar_texto_paciente(numero_afiliado) or ''
    plan_n = normalizar_texto_paciente(plan) or ''
    if not afil:
        errors['numero_afiliado'] = (
            'El número de afiliado es obligatorio si no sos particular.'
        )
    if not plan_n:
        errors['plan'] = 'El plan es obligatorio si no sos particular.'
    return errors
