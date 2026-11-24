"""Resolución de login por username o DNI (portal paciente).

El producto promete ingresar con DNI. El registro público ya fuerza
``User.username == Paciente.dni``, pero altas de secretaría a menudo usan
otro username. Este módulo autentica por username exacto y, si falla,
por ficha de paciente vinculada al DNI (normalizado).
"""
from __future__ import annotations

import re

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q

User = get_user_model()


def normalize_login_identifier(raw: str | None) -> str:
    """Trim; si parece documento, quita puntos/guiones/espacios."""
    text = (raw or '').strip()
    if not text:
        return ''
    digits = re.sub(r'[.\-\s]', '', text)
    if digits.isdigit() and len(digits) >= 6:
        return digits
    return text


def _usernames_for_dni(dni_normalized: str, raw: str) -> list[str]:
    """Usernames de pacientes vinculados cuyo DNI coincide (exacto o normalizado)."""
    from pacientes.models import Paciente

    if not dni_normalized and not raw:
        return []

    dni_variants = {v for v in (dni_normalized, raw, (raw or '').strip()) if v}
    qs = (
        Paciente.objects.filter(user__isnull=False)
        .filter(Q(dni__in=dni_variants) | Q(user__username__in=dni_variants))
        .select_related('user')
        .order_by('id')
    )
    found: list[str] = []
    seen: set[str] = set()
    for pac in qs[:20]:
        uname = (getattr(pac.user, 'username', None) or '').strip()
        if uname and uname not in seen:
            seen.add(uname)
            found.append(uname)
        # Ficha con DNI formateado distinto al tipeado (p. ej. 30.123.456 vs 30123456).
        if normalize_login_identifier(pac.dni) == dni_normalized and uname and uname not in seen:
            seen.add(uname)
            found.append(uname)
    if found:
        return found

    # Fallback acotado: DNIs con separadores en DB que no matchean exacto.
    if dni_normalized and dni_normalized.isdigit():
        for pac in (
            Paciente.objects.filter(user__isnull=False, dni__icontains=dni_normalized[:4])
            .select_related('user')
            .order_by('id')[:200]
        ):
            if normalize_login_identifier(pac.dni) == dni_normalized:
                uname = (getattr(pac.user, 'username', None) or '').strip()
                if uname and uname not in seen:
                    seen.add(uname)
                    found.append(uname)
                break
    return found


def username_candidates(identifier: str | None) -> list[str]:
    """Candidatos de username a probar, sin duplicados."""
    raw = (identifier or '').strip()
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []

    def add(value: str) -> None:
        v = (value or '').strip()
        if not v or v in seen:
            return
        seen.add(v)
        out.append(v)

    add(raw)
    normalized = normalize_login_identifier(raw)
    add(normalized)
    if normalized and normalized.isdigit():
        for uname in _usernames_for_dni(normalized, raw):
            add(uname)
    return out


def authenticate_with_identifier(request, identifier: str | None, password: str | None):
    """Autentica con username literal o DNI de paciente vinculado.

    Devuelve el mismo ``None`` opaco que ``authenticate`` (sin enumerar cuentas).
    """
    if not identifier or password is None:
        return None
    password = str(password)
    if password == '':
        return None

    for username in username_candidates(str(identifier)):
        user = authenticate(request=request, username=username, password=password)
        if user is not None:
            return user
    return None
