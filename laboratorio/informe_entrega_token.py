"""Token de entrega pública del PDF de informe LIMS (opaco en BD + compat. firmado).

Los enlaces no caducan: el token permanece válido mientras exista en BD (química)
o mientras no cambie SECRET_KEY (firmados / microbiología).
"""
from __future__ import annotations

import secrets

from django.core import signing

from laboratorio.models import SolicitudExamen

_SALT = "lims-informe-entrega-v1"
_SALT_MICRO = "lims-micro-informe-entrega-v1"


class InformeEntregaTokenError(ValueError):
    """Token inválido."""


def asignar_token_entrega(solicitud: SolicitudExamen, *, renovar: bool = False) -> str:
    """
    Asigna un token URL-safe en la solicitud (sin guardar).
    Los tokens no caducan. Con ``renovar=False`` reutiliza el existente si hay.
    Con ``renovar=True`` emite uno nuevo (invalida el enlace anterior).
    """
    if not renovar and solicitud.informe_entrega_token:
        # Limpiar expiración legada (72 h) para dejar el enlace permanente.
        if solicitud.informe_entrega_token_expira is not None:
            solicitud.informe_entrega_token_expira = None
        return solicitud.informe_entrega_token

    token = secrets.token_urlsafe(32)
    solicitud.informe_entrega_token = token
    solicitud.informe_entrega_token_expira = None
    return token


def _verificar_token_firmado_legacy(token: str) -> int:
    try:
        data = signing.loads(token, salt=_SALT)
    except signing.BadSignature as exc:
        raise InformeEntregaTokenError("Enlace de informe inválido.") from exc
    sid = data.get("sid")
    if not sid:
        raise InformeEntregaTokenError("Enlace de informe inválido.")
    return int(sid)


def _verificar_token_almacenado(token: str) -> int:
    solicitud_id = (
        SolicitudExamen.objects.filter(
            informe_entrega_token=token,
        )
        .values_list("pk", flat=True)
        .first()
    )
    if not solicitud_id:
        raise InformeEntregaTokenError("Enlace de informe inválido.")
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
    """URL de descarga sin query string: WhatsApp no autolinkea `?t=` en el chat."""
    base = (base_url or "").rstrip("/")
    token = solicitud.informe_entrega_token or asignar_token_entrega(
        solicitud, renovar=False
    )
    return f"{base}{ruta_informe_entrega()}{token}/"


# --- Entrega pública informe microbiológico (token firmado por estudio) ---


def crear_token_entrega_informe_micro(estudio_id: int) -> str:
    return signing.dumps(
        {"mid": int(estudio_id), "v": 1},
        salt=_SALT_MICRO,
        compress=True,
    )


def verificar_token_entrega_informe_micro(token: str) -> int:
    token = (token or "").strip()
    if not token:
        raise InformeEntregaTokenError("Enlace de informe inválido.")
    try:
        data = signing.loads(token, salt=_SALT_MICRO)
    except signing.BadSignature as exc:
        raise InformeEntregaTokenError("Enlace de informe inválido.") from exc
    mid = data.get("mid")
    if not mid:
        raise InformeEntregaTokenError("Enlace de informe inválido.")
    return int(mid)


def ruta_informe_entrega_micro() -> str:
    return "/api/lab/microbiologia/estudios/informe-entrega/"


def segmento_path_token_micro(token: str) -> str:
    """El token firmado trae ':'; WhatsApp corta el enlace ahí. Va en base64 url-safe."""
    from base64 import urlsafe_b64encode

    return urlsafe_b64encode((token or "").encode("ascii")).decode("ascii").rstrip("=")


def token_micro_desde_segmento(segmento: str) -> str:
    from base64 import urlsafe_b64decode

    raw = (segmento or "").strip()
    if not raw:
        return raw
    if ":" in raw:
        return raw
    try:
        pad = "=" * (-len(raw) % 4)
        decoded = urlsafe_b64decode(raw + pad).decode("ascii")
    except Exception:
        return raw
    return decoded if decoded else raw


def construir_url_entrega_informe_micro(base_url: str, estudio_id: int) -> str:
    base = (base_url or "").rstrip("/")
    token = crear_token_entrega_informe_micro(estudio_id)
    return f"{base}{ruta_informe_entrega_micro()}{segmento_path_token_micro(token)}/"
