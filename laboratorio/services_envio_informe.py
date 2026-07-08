"""
Envío de informes LIMS por correo y WhatsApp (PDF adjunto / enlace firmado).
"""
from __future__ import annotations

import logging
import os
import re
import socket
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot
from laboratorio.informe_entrega_token import (
    asignar_token_entrega,
    construir_url_entrega_informe,
)
from laboratorio.models import SolicitudExamen
from laboratorio.solicitud_cierre import solicitud_tiene_algun_resultado
from laboratorio.services_informes_pdf import (
    generar_informe_lims_pdf_bytes,
    nombre_archivo_pdf_seguro,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)


class EnvioInformeError(ValueError):
    """Fallo al enviar el informe."""


@dataclass
class ResultadoEnvioInforme:
    email_enviado: bool = False
    email_destino: str | None = None
    email_adjunto_pdf: bool = False
    whatsapp_enviado: bool = False
    whatsapp_telefono: str | None = None
    whatsapp_enlace: str | None = None
    whatsapp_pdf_adjunto: bool = False
    informe_enlace_descarga: str | None = None
    advertencias: list[str] = field(default_factory=list)


def _role_operacion(actor) -> str:
    if getattr(actor, "is_superuser", False):
        return "admin"
    return getattr(actor, "rol", "laboratorio") or "laboratorio"


def resolver_base_url_publica(*, public_base_url: str | None = None) -> str:
    explicit = (public_base_url or os.getenv("PUBLIC_API_BASE_URL", "")).strip().rstrip("/")
    if explicit:
        return explicit
    return getattr(settings, "PUBLIC_API_BASE_URL", "").strip().rstrip("/")


def _normalize_whatsapp_phone(telefono: str | None) -> str | None:
    if not telefono:
        return None
    digits = re.sub(r"\D", "", telefono)
    if not digits:
        return None
    if digits.startswith("0"):
        digits = "54" + digits[1:]
    elif len(digits) <= 10 and not digits.startswith("54"):
        digits = "54" + digits
    return digits


def _mensaje_whatsapp(solicitud: SolicitudExamen, enlace_descarga: str | None) -> str:
    numero = solicitud.numero or f"#{solicitud.pk}"
    texto = (
        f"Hola, le informamos que los resultados de laboratorio de su orden {numero} "
        f"ya están disponibles."
    )
    if enlace_descarga:
        texto += f" Descargue su informe PDF aquí: {enlace_descarga}"
    else:
        texto += " Puede solicitarlo en la institución."
    return texto + " Saludos."


def _enlace_whatsapp_web(telefono: str, mensaje: str) -> str:
    from urllib.parse import quote

    return f"https://wa.me/{telefono}?text={quote(mensaje)}"


def _intentar_twilio_whatsapp(
    telefono: str,
    mensaje: str,
    *,
    media_url: str | None,
) -> tuple[bool, str | None]:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_wa = os.getenv("TWILIO_WHATSAPP_FROM", "").strip()
    if not (sid and token and from_wa):
        return False, "Twilio no configurado (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM)."
    try:
        from twilio.rest import Client  # type: ignore[import-untyped]
    except ImportError:
        return False, "Paquete twilio no instalado en el servidor."

    payload: dict = {
        "from_": from_wa,
        "to": f"whatsapp:+{telefono}",
        "body": mensaje,
    }
    if media_url:
        payload["media_url"] = [media_url]

    try:
        client = Client(sid, token)
        client.messages.create(**payload)
        return True, None
    except Exception as exc:
        logger.exception("Error enviando WhatsApp vía Twilio")
        return False, f"Twilio rechazó el envío: {exc}"


def enviar_informe_solicitud(
    solicitud: SolicitudExamen,
    *,
    enviar_email: bool,
    enviar_whatsapp: bool,
    actor: AbstractUser | None,
    view: str,
    public_base_url: str | None = None,
) -> ResultadoEnvioInforme:
    if solicitud.estado not in ("FINALIZADO", "INFORMADO_PARCIAL"):
        raise EnvioInformeError(
            "Solo se puede enviar el informe de órdenes finalizadas o informadas parcialmente."
        )
    if not solicitud_tiene_algun_resultado(solicitud):
        raise EnvioInformeError(
            "No hay resultados cargados para generar el informe."
        )
    if not enviar_email and not enviar_whatsapp:
        raise EnvioInformeError("Indique al menos un canal: email o whatsapp.")

    paciente = solicitud.paciente
    role = _role_operacion(actor)
    pdf_bytes = generar_informe_lims_pdf_bytes(solicitud, role=role)
    filename = nombre_archivo_pdf_seguro(solicitud.pk)
    resultado = ResultadoEnvioInforme()

    base_url = resolver_base_url_publica(public_base_url=public_base_url)
    if base_url:
        asignar_token_entrega(solicitud, renovar=True)
        enlace_descarga = construir_url_entrega_informe(base_url, solicitud)
    else:
        enlace_descarga = None
    resultado.informe_enlace_descarga = enlace_descarga

    if not base_url:
        resultado.advertencias.append(
            "PUBLIC_API_BASE_URL no configurada: WhatsApp no podrá adjuntar el PDF "
            "automáticamente (solo enlace en el mensaje si aplica)."
        )

    before = safe_model_snapshot(solicitud)
    update_fields: list[str] = []

    if enviar_email:
        destino = (paciente.email or "").strip()
        if not destino:
            resultado.advertencias.append("El paciente no tiene email registrado.")
        else:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@localhost"
            asunto = f"Informe de laboratorio — {solicitud.numero or solicitud.pk}"
            cuerpo = (
                f"Adjuntamos el informe PDF de laboratorio de la orden "
                f"{solicitud.numero or solicitud.pk}.\n\n"
            )
            if enlace_descarga:
                cuerpo += f"También puede descargarlo desde: {enlace_descarga}\n\n"
            cuerpo += "Mensaje generado por el sistema de laboratorio."
            msg = EmailMessage(
                subject=asunto,
                body=cuerpo,
                from_email=from_email,
                to=[destino],
            )
            msg.attach(filename, pdf_bytes, "application/pdf")
            try:
                msg.send(fail_silently=False)
                resultado.email_enviado = True
                resultado.email_destino = destino
                resultado.email_adjunto_pdf = True
                solicitud.informe_enviado_email = True
                update_fields.append("informe_enviado_email")
            except (TimeoutError, socket.timeout) as exc:
                logger.exception("Timeout enviando email informe LIMS")
                raise EnvioInformeError(
                    "El servidor de correo no respondió a tiempo. Verifique la configuración SMTP "
                    "y la conexión de red (puerto 587)."
                ) from exc
            except OSError as exc:
                if "timed out" in str(exc).lower():
                    logger.exception("Timeout enviando email informe LIMS")
                    raise EnvioInformeError(
                        "El servidor de correo no respondió a tiempo. Verifique la configuración SMTP "
                        "y la conexión de red (puerto 587)."
                    ) from exc
                logger.exception("Error de red enviando email informe LIMS")
                raise EnvioInformeError(
                    "No se pudo conectar al servidor de correo. Verifique SMTP y red."
                ) from exc
            except Exception as exc:
                logger.exception("Error enviando email informe LIMS")
                raise EnvioInformeError(
                    "No se pudo enviar el correo. Verifique la configuración SMTP del servidor."
                ) from exc

    if enviar_whatsapp:
        telefono = _normalize_whatsapp_phone(paciente.telefono)
        if not telefono:
            resultado.advertencias.append("El paciente no tiene teléfono registrado.")
        else:
            mensaje = _mensaje_whatsapp(solicitud, enlace_descarga)
            media_url = enlace_descarga if enlace_descarga else None
            enviado_api, error_api = _intentar_twilio_whatsapp(
                telefono,
                mensaje,
                media_url=media_url,
            )
            resultado.whatsapp_telefono = telefono
            resultado.whatsapp_enlace = _enlace_whatsapp_web(telefono, mensaje)

            if enviado_api:
                resultado.whatsapp_enviado = True
                resultado.whatsapp_pdf_adjunto = bool(media_url)
                solicitud.informe_enviado_whatsapp = True
                update_fields.append("informe_enviado_whatsapp")
                if not media_url:
                    resultado.advertencias.append(
                        "WhatsApp enviado solo como texto (sin URL pública para el PDF)."
                    )
            else:
                if error_api:
                    resultado.advertencias.append(error_api)
                resultado.advertencias.append(
                    "Abra el enlace de WhatsApp y adjunte el PDF descargado manualmente, "
                    "o comparta el enlace de descarga del mensaje."
                )

    if resultado.email_enviado or resultado.whatsapp_enviado:
        solicitud.fecha_informe_enviado = timezone.now()
        update_fields.append("fecha_informe_enviado")
        if actor and getattr(actor, "pk", None):
            solicitud.informe_enviado_por = actor
            update_fields.append("informe_enviado_por")

    if solicitud.informe_entrega_token:
        update_fields.extend(
            ["informe_entrega_token", "informe_entrega_token_expira"]
        )

    if update_fields:
        solicitud.save(update_fields=list(dict.fromkeys(update_fields)))
        log_update(
            actor=actor,
            entity=solicitud,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "enviar_informe",
                "view": view,
                "email": resultado.email_enviado,
                "email_adjunto_pdf": resultado.email_adjunto_pdf,
                "whatsapp": resultado.whatsapp_enviado,
                "whatsapp_pdf_adjunto": resultado.whatsapp_pdf_adjunto,
                "solicitud_id": solicitud.pk,
            },
        )

    tiene_fallback_wa = bool(resultado.whatsapp_enlace and enlace_descarga)
    if (
        not resultado.email_enviado
        and not resultado.whatsapp_enviado
        and not tiene_fallback_wa
    ):
        raise EnvioInformeError(
            "No hay datos de contacto del paciente para enviar el informe."
        )

    return resultado
