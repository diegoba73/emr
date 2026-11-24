"""Catálogo formal de obras sociales: seeds, resolve y etiquetas."""
from __future__ import annotations

import re
from typing import Any

from django.db.models import Q

# Seeds mínimos (codigo, nombre). PARTICULAR = sin cobertura / particular.
SEED_OBRAS_SOCIALES: tuple[tuple[str, str], ...] = (
    ('PARTICULAR', 'Particular'),
    ('OSDE', 'OSDE'),
    ('PAMI', 'PAMI'),
    ('SEROS', 'SEROS'),
    ('SWISS_MEDICAL', 'Swiss Medical'),
    ('GALENO', 'Galeno'),
    ('MEDICUS', 'Medicus'),
    ('IOMA', 'IOMA'),
    ('OSECAC', 'OSECAC'),
)


def normalizar_codigo_os(value: Any) -> str:
    text = (str(value) if value is not None else '').strip().upper()
    return text


def codigo_desde_texto_libre(text: str) -> str:
    """Deriva un código único-ish desde texto legacy (migración)."""
    raw = normalizar_codigo_os(text)
    code = re.sub(r'[^A-Z0-9]+', '_', raw).strip('_')[:80]
    return code or 'LEGACY'


def label_obra_social(obra) -> str:
    """Texto para API/LIMS/PDF: nombre si hay, si no código."""
    if obra is None:
        return ''
    if hasattr(obra, 'nombre'):
        return (obra.nombre or obra.codigo or '').strip()
    return str(obra).strip()


def codigo_obra_social(obra) -> str:
    if obra is None:
        return ''
    if hasattr(obra, 'codigo'):
        return (obra.codigo or '').strip()
    return str(obra).strip().upper()


def ensure_seed_obras_sociales() -> None:
    from pacientes.models import ObraSocial

    for codigo, nombre in SEED_OBRAS_SOCIALES:
        ObraSocial.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'activo': True},
        )


def resolve_obra_social(
    value: Any,
    *,
    allow_inactive: bool = False,
    create_legacy: bool = False,
):
    """Resuelve id / código / nombre a ``ObraSocial``.

    - ``None`` / '' → ``None``
    - int / str dígitos → PK
    - str → match codigo o nombre (upper)
    - ``create_legacy=True``: si no hay match, crea fila legacy (solo migración)
    """
    from pacientes.models import ObraSocial

    if value is None:
        return None
    if isinstance(value, ObraSocial):
        return value

    if isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit()):
        qs = ObraSocial.objects.all()
        if not allow_inactive:
            qs = qs.filter(activo=True)
        try:
            return qs.get(pk=int(value))
        except (ObraSocial.DoesNotExist, TypeError, ValueError):
            return None

    text = normalizar_codigo_os(value)
    if not text:
        return None

    qs = ObraSocial.objects.all()
    if not allow_inactive:
        qs = qs.filter(activo=True)
    found = qs.filter(Q(codigo=text) | Q(nombre__iexact=text)).order_by('id').first()
    if found is not None:
        return found

    if not create_legacy:
        return None

    codigo = codigo_desde_texto_libre(text)
    base = codigo
    n = 2
    while ObraSocial.objects.filter(codigo=codigo).exists():
        codigo = f'{base}_{n}'[:80]
        n += 1
    return ObraSocial.objects.create(codigo=codigo, nombre=text, activo=True)
