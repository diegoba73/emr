"""Token de entrega pública del PDF de informe LIMS (opaco en BD + compat. firmado)."""
from __future__ import annotations

import secrets
from datetime import timedelta

from django.core import signing
from django.utils import timezone

from laboratorio.models import SolicitudExamen

_SALT = "lims-informe-entrega-v1"
_MAX_AGE_SECONDS = 72 * 3600  # 72 h
_TOKEN_VIDA = timedelta(hours=72)


class InformeEntregaTokenError(ValueError):
    """Token inválido o expirado."""


def asignar_token_entrega(solicitud: SolicitudExamen, *, renovar: bool = False) -> str:
    """
    Asigna un token URL-safe en la solicitud (sin guardar).
    Con ``renovar=True`` siempre emite uno nuevo válido por 72 h.
    """
    now = timezone.now()
    if (
        not renovar
        and solicitud.informe_entrega_token
        and solicitud.informe_entrega_token_expira
        and solicitud.informe_entrega_token_expira > now
    ):
        return solicitud.informe_entrega_token

    token = secrets.token_urlsafe(32)
    solicitud.informe_entrega_token = token
    solicitud.informe_entrega_token_expira = now + _TOKEN_VIDA
    return token


def _verificar_token_firmado_legacy(token: str) -> int:
    try:
        data = signing.loads(token, salt=_SALT, max_age=_MAX_AGE_SECONDS)
    except signing.BadSignature as exc:
        raise InformeEntregaTokenError("Enlace de informe inválido o expirado.") from exc
    sid = data.get("sid")
    if not sid:
        raise InformeEntregaTokenError("Enlace de informe inválido.")
    return int(sid)


def _verificar_token_almacenado(token: str) -> int:
    solicitud_id = (
        SolicitudExamen.objects.filter(
            informe_entrega_token=token,
            informe_entrega_token_expira__gt=timezone.now(),
        )
        .values_list("pk", flat=True)
        .first()
    )
    if not solicitud_id:
        raise InformeEntregaTokenError("Enlace de informe inválido o expirado.")
    return int(solicitud_id)


def verificar_token_entrega_informe(token: str) -> int:
    """Resuelve la solicitud desde token opaco (actual) o firmado (legacy)."""
    token = (token or "").strip()
    if not token:
        raise InformeEntregaTokenError("Enlace de informe inválido.")
    if ":" in token:
        return _verificar_token_firmado_legacy(token)
    return _verificar_token_almacenado(token)


def crear_token_entrega_informe(solicitud_id: int) -> str:
    """Legacy: token firmado (solo tests / enlaces antiguos)."""
    return signing.dumps({"sid": int(solicitud_id), "v": 1}, salt=_SALT, compress=True)


def ruta_informe_entrega() -> str:
    return "/api/lab/solicitudes/informe-entrega/"


def construir_url_entrega_informe(base_url: str, solicitud: SolicitudExamen) -> str:
    base = (base_url or "").rstrip("/")
    token = solicitud.informe_entrega_token or asignar_token_entrega(
        solicitud, renovar=True
    )
    return f"{base}{ruta_informe_entrega()}?t={token}"
