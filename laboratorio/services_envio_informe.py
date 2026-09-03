"""
Envío de informes LIMS por correo y WhatsApp (PDF adjunto / enlace firmado).

Destinatarios: paciente y/o médico solicitante (interno vinculado a la orden).
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
    email_destinos: list[str] = field(default_factory=list)
    email_adjunto_pdf: bool = False
    whatsapp_enviado: bool = False
    whatsapp_telefono: str | None = None
    whatsapp_enlace: str | None = None
    whatsapp_enlaces: list[dict] = field(default_factory=list)
    whatsapp_pdf_adjunto: bool = False
    informe_enlace_descarga: str | None = None
    advertencias: list[str] = field(default_factory=list)


def _role_operacion(actor) -> str:
    if getattr(actor, "is_superuser", False):
        return "admin"
    return getattr(actor, "rol", "laboratorio") or "laboratorio"


def resolver_base_url_publica(*, public_base_url: str | None = None) -> str:
    """URL para enlaces de descarga del PDF (mail / WhatsApp).

    Prioridad: ``PUBLIC_API_BASE_URL`` (settings/env) sobre el host del request.
    El request suele ser localhost o IP interna; el celular del paciente no lo alcanza.
    """
    configured = (getattr(settings, "PUBLIC_API_BASE_URL", None) or "").strip().rstrip("/")
    if configured:
        return configured
    env_url = (os.getenv("PUBLIC_API_BASE_URL", "") or "").strip().rstrip("/")
    if env_url:
        return env_url
    return (public_base_url or "").strip().rstrip("/")


def url_alcanzable_por_destinatario(url: str | None) -> str | None:
    """None si el celular/WhatsApp no podría abrirla (localhost, IP privada, host Docker)."""
    from urllib.parse import urlparse
    import ipaddress

    raw = (url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return None
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1", "backend"}:
        return None
    if host.endswith(".local") or host.endswith(".localhost"):
        return None
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return None
    except ValueError:
        pass
    return raw


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


def _mensaje_whatsapp_con_enlace(intro: str, enlace: str | None, fallback: str) -> str:
    """El URL va solo en la última línea: así WhatsApp lo vuelve enlace tocable."""
    if enlace:
        return f"{intro}\n\n{enlace.strip()}"
    return f"{intro} {fallback}"


def _mensaje_whatsapp_paciente(solicitud: SolicitudExamen, enlace_descarga: str | None) -> str:
    numero = solicitud.numero or f"#{solicitud.pk}"
    intro = (
        f"Hola, le informamos que los resultados de laboratorio de su orden {numero} "
        f"ya están disponibles."
    )
    return _mensaje_whatsapp_con_enlace(
        intro, enlace_descarga, "Puede solicitarlo en la institución."
    )


def _mensaje_whatsapp_medico(solicitud: SolicitudExamen, enlace_descarga: str | None) -> str:
    numero = solicitud.numero or f"#{solicitud.pk}"
    paciente_nombre = ""
    if solicitud.paciente_id:
        paciente_nombre = getattr(solicitud.paciente, "nombre_completo", "") or ""
    intro = (
        f"Hola, los resultados de laboratorio de la orden {numero}"
        + (f" del paciente {paciente_nombre}" if paciente_nombre else "")
        + " ya están disponibles."
    )
    return _mensaje_whatsapp_con_enlace(
        intro, enlace_descarga, "Puede consultarlo en el sistema."
    )


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
        # Sin Twilio: el frontend abre wa.me. No es un error para el operador.
        return False, None
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


def _medico_contacto(solicitud: SolicitudExamen) -> tuple[str | None, str | None, str | None]:
    """Devuelve (nombre, email, telefono) del médico interno, si existe."""
    medico = getattr(solicitud, "medico_interno", None)
    if not medico:
        return None, None, None
    nombre = getattr(medico, "nombre_completo", None) or str(medico)
    email = (getattr(medico, "email", None) or "").strip() or None
    telefono = (getattr(medico, "telefono", None) or "").strip() or None
    return nombre, email, telefono


def _enviar_email_pdf(
    *,
    destino: str,
    solicitud: SolicitudExamen,
    pdf_bytes: bytes,
    filename: str,
    enlace_descarga: str | None,
    destinatario_label: str,
) -> None:
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@localhost"
    asunto = f"Informe de laboratorio — {solicitud.numero or solicitud.pk}"
    cuerpo = (
        f"Adjuntamos el informe PDF de laboratorio de la orden "
        f"{solicitud.numero or solicitud.pk}"
    )
    if destinatario_label == "medico" and solicitud.paciente_id:
        nombre_pac = getattr(solicitud.paciente, "nombre_completo", "") or ""
        if nombre_pac:
            cuerpo += f" (paciente {nombre_pac})"
    cuerpo += ".\n\n"
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


def enviar_informe_solicitud(
    solicitud: SolicitudExamen,
    *,
    enviar_email: bool = False,
    enviar_whatsapp: bool = False,
    enviar_email_medico: bool = False,
    enviar_whatsapp_medico: bool = False,
    actor: AbstractUser | None,
    view: str,
    public_base_url: str | None = None,
) -> ResultadoEnvioInforme:
    if solicitud.estado != "FINALIZADO":
        raise EnvioInformeError(
            "Solo se puede enviar el informe de una orden validada (FINALIZADO)."
        )
    if not solicitud_tiene_algun_resultado(solicitud):
        raise EnvioInformeError(
            "No hay resultados cargados para generar el informe."
        )
    if not (
        enviar_email
        or enviar_whatsapp
        or enviar_email_medico
        or enviar_whatsapp_medico
    ):
        raise EnvioInformeError(
            "Indique al menos un canal: email o whatsapp (paciente y/o médico)."
        )

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
    enlace_wa = url_alcanzable_por_destinatario(enlace_descarga)

    if not base_url:
        resultado.advertencias.append(
            "PUBLIC_API_BASE_URL no configurada: el mensaje de WhatsApp no incluirá "
            "un enlace de descarga. Se abre el chat y se descarga el PDF para adjuntarlo."
        )
    elif enlace_descarga and not enlace_wa:
        resultado.advertencias.append(
            "El enlace de descarga es local (localhost): WhatsApp no lo vuelve clicable "
            "y el celular no podría abrirlo. Adjuntá el PDF descargado al chat. "
            "En el servidor público el mensaje sí lleva el link."
        )

    before = safe_model_snapshot(solicitud)
    update_fields: list[str] = []
    medico_nombre, medico_email, medico_tel_raw = _medico_contacto(solicitud)

    # --- Email paciente ---
    if enviar_email:
        destino = (paciente.email or "").strip()
        if not destino:
            resultado.advertencias.append("El paciente no tiene email registrado.")
        else:
            _enviar_email_pdf(
                destino=destino,
                solicitud=solicitud,
                pdf_bytes=pdf_bytes,
                filename=filename,
                enlace_descarga=enlace_wa,
                destinatario_label="paciente",
            )
            resultado.email_enviado = True
            resultado.email_destinos.append(destino)
            resultado.email_adjunto_pdf = True
            solicitud.informe_enviado_email = True
            update_fields.append("informe_enviado_email")

    # --- Email médico ---
    if enviar_email_medico:
        if not solicitud.medico_interno_id:
            resultado.advertencias.append(
                "La orden no tiene médico interno: no se puede enviar al solicitante."
            )
        elif not medico_email:
            resultado.advertencias.append(
                "El médico solicitante no tiene email registrado "
                f"({medico_nombre or 'sin nombre'})."
            )
        else:
            _enviar_email_pdf(
                destino=medico_email,
                solicitud=solicitud,
                pdf_bytes=pdf_bytes,
                filename=filename,
                enlace_descarga=enlace_wa,
                destinatario_label="medico",
            )
            resultado.email_enviado = True
            resultado.email_destinos.append(medico_email)
            resultado.email_adjunto_pdf = True
            solicitud.informe_enviado_email = True
            update_fields.append("informe_enviado_email")

    if resultado.email_destinos:
        resultado.email_destino = ", ".join(resultado.email_destinos)

    def _enviar_wa(
        *,
        telefono_raw: str | None,
        mensaje: str,
        rol: str,
        sin_tel_msg: str,
    ) -> None:
        telefono = _normalize_whatsapp_phone(telefono_raw)
        if not telefono:
            resultado.advertencias.append(sin_tel_msg)
            return
        media_url = enlace_wa
        enviado_api, error_api = _intentar_twilio_whatsapp(
            telefono,
            mensaje,
            media_url=media_url,
        )
        enlace = _enlace_whatsapp_web(telefono, mensaje)
        resultado.whatsapp_enlaces.append(
            {"rol": rol, "telefono": telefono, "enlace": enlace}
        )
        if not resultado.whatsapp_telefono:
            resultado.whatsapp_telefono = telefono
        if not resultado.whatsapp_enlace:
            resultado.whatsapp_enlace = enlace

        if enviado_api:
            resultado.whatsapp_enviado = True
            resultado.whatsapp_pdf_adjunto = bool(media_url) or resultado.whatsapp_pdf_adjunto
            solicitud.informe_enviado_whatsapp = True
            update_fields.append("informe_enviado_whatsapp")
            if not media_url:
                resultado.advertencias.append(
                    f"WhatsApp ({rol}) enviado solo como texto (sin URL pública para el PDF)."
                )
        else:
            if error_api and error_api not in resultado.advertencias:
                resultado.advertencias.append(error_api)
            resultado.advertencias.append(
                f"Se abrirá WhatsApp ({rol}): confirmá Enviar. "
                "El PDF se descarga para adjuntarlo si hace falta."
            )

    if enviar_whatsapp:
        _enviar_wa(
            telefono_raw=paciente.telefono,
            mensaje=_mensaje_whatsapp_paciente(solicitud, enlace_wa),
            rol="paciente",
            sin_tel_msg="El paciente no tiene teléfono registrado.",
        )

    if enviar_whatsapp_medico:
        if not solicitud.medico_interno_id:
            resultado.advertencias.append(
                "La orden no tiene médico interno: no se puede enviar WhatsApp al solicitante."
            )
        else:
            _enviar_wa(
                telefono_raw=medico_tel_raw,
                mensaje=_mensaje_whatsapp_medico(solicitud, enlace_wa),
                rol="medico",
                sin_tel_msg=(
                    "El médico solicitante no tiene teléfono registrado "
                    f"({medico_nombre or 'sin nombre'})."
                ),
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
                "email_destinos": resultado.email_destinos,
                "whatsapp": resultado.whatsapp_enviado,
                "whatsapp_pdf_adjunto": resultado.whatsapp_pdf_adjunto,
                "whatsapp_roles": [e.get("rol") for e in resultado.whatsapp_enlaces],
                "solicitud_id": solicitud.pk,
            },
        )

    tiene_fallback_wa = bool(resultado.whatsapp_enlaces)
    if (
        not resultado.email_enviado
        and not resultado.whatsapp_enviado
        and not tiene_fallback_wa
    ):
        raise EnvioInformeError(
            "No hay datos de contacto del paciente ni del médico para enviar el informe."
        )

    return resultado


def _medico_contacto_estudio(estudio) -> tuple[str | None, str | None, str | None]:
    medico = getattr(estudio, "medico_interno", None)
    if not medico:
        return None, None, None
    nombre = getattr(medico, "nombre_completo", None) or str(medico)
    email = (getattr(medico, "email", None) or "").strip() or None
    telefono = (getattr(medico, "telefono", None) or "").strip() or None
    return nombre, email, telefono


def _enviar_email_pdf_micro(
    *,
    destino: str,
    estudio,
    pdf_bytes: bytes,
    filename: str,
    enlace_descarga: str | None,
    destinatario_label: str,
) -> None:
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@localhost"
    numero = estudio.numero or f"#{estudio.pk}"
    asunto = f"Informe de microbiología — {numero}"
    cuerpo = f"Adjuntamos el informe PDF de microbiología del estudio {numero}"
    if destinatario_label == "medico" and estudio.paciente_id:
        nombre_pac = getattr(estudio.paciente, "nombre_completo", "") or ""
        if nombre_pac:
            cuerpo += f" (paciente {nombre_pac})"
    cuerpo += ".\n\n"
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
    except (TimeoutError, socket.timeout) as exc:
        logger.exception("Timeout enviando email informe micro")
        raise EnvioInformeError(
            "El servidor de correo no respondió a tiempo. Verifique la configuración SMTP "
            "y la conexión de red (puerto 587)."
        ) from exc
    except OSError as exc:
        if "timed out" in str(exc).lower():
            raise EnvioInformeError(
                "El servidor de correo no respondió a tiempo. Verifique la configuración SMTP "
                "y la conexión de red (puerto 587)."
            ) from exc
        raise EnvioInformeError(
            "No se pudo conectar al servidor de correo. Verifique SMTP y red."
        ) from exc
    except Exception as exc:
        logger.exception("Error enviando email informe micro")
        raise EnvioInformeError(
            "No se pudo enviar el correo. Verifique la configuración SMTP del servidor."
        ) from exc


def _mensaje_whatsapp_paciente_micro(estudio, enlace_descarga: str | None) -> str:
    numero = estudio.numero or f"#{estudio.pk}"
    intro = (
        f"Hola, le informamos que el informe de microbiología de su estudio {numero} "
        f"ya está disponible."
    )
    return _mensaje_whatsapp_con_enlace(
        intro, enlace_descarga, "Puede solicitarlo en la institución."
    )


def _mensaje_whatsapp_medico_micro(estudio, enlace_descarga: str | None) -> str:
    numero = estudio.numero or f"#{estudio.pk}"
    paciente_nombre = ""
    if estudio.paciente_id:
        paciente_nombre = getattr(estudio.paciente, "nombre_completo", "") or ""
    intro = f"Informe de microbiología {numero}"
    if paciente_nombre:
        intro += f" (paciente {paciente_nombre})"
    intro += " disponible."
    return _mensaje_whatsapp_con_enlace(intro, enlace_descarga, "Puede consultarlo en el sistema.")


def enviar_informe_estudio_micro(
    estudio,
    *,
    enviar_email: bool = False,
    enviar_whatsapp: bool = False,
    enviar_email_medico: bool = False,
    enviar_whatsapp_medico: bool = False,
    actor: AbstractUser | None,
    view: str,
    public_base_url: str | None = None,
) -> ResultadoEnvioInforme:
    """Envía el PDF del informe FINAL micro **VALIDADO** por email y/o WhatsApp."""
    from laboratorio.informe_entrega_token import construir_url_entrega_informe_micro
    from laboratorio.models_microbiologia import InformeMicrobiologia
    from laboratorio.services_informes_micro_pdf import (
        InformeMicroPdfError,
        assert_estudio_puede_generar_pdf,
        generar_informe_micro_pdf_bytes,
        nombre_archivo_pdf_micro,
    )

    if not InformeMicrobiologia.objects.filter(
        estudio_id=estudio.pk,
        tipo="FINAL",
        estado="VALIDADO",
    ).exists():
        raise EnvioInformeError(
            "Solo se puede enviar un informe FINAL validado por el bioquímico."
        )

    try:
        assert_estudio_puede_generar_pdf(estudio)
    except InformeMicroPdfError as exc:
        raise EnvioInformeError(str(exc)) from exc

    if not (
        enviar_email
        or enviar_whatsapp
        or enviar_email_medico
        or enviar_whatsapp_medico
    ):
        raise EnvioInformeError(
            "Indique al menos un canal: email o whatsapp (paciente y/o médico)."
        )

    paciente = estudio.paciente
    if paciente is None:
        raise EnvioInformeError("El estudio no tiene paciente asociado.")

    pdf_bytes = generar_informe_micro_pdf_bytes(estudio)
    filename = nombre_archivo_pdf_micro(estudio.pk)
    resultado = ResultadoEnvioInforme()

    base_url = resolver_base_url_publica(public_base_url=public_base_url)
    if base_url:
        enlace_descarga = construir_url_entrega_informe_micro(base_url, estudio.pk)
    else:
        enlace_descarga = None
    resultado.informe_enlace_descarga = enlace_descarga
    enlace_wa = url_alcanzable_por_destinatario(enlace_descarga)

    if not base_url:
        resultado.advertencias.append(
            "PUBLIC_API_BASE_URL no configurada: el mensaje de WhatsApp no incluirá "
            "un enlace de descarga. Se abre el chat y se descarga el PDF para adjuntarlo."
        )
    elif enlace_descarga and not enlace_wa:
        resultado.advertencias.append(
            "El enlace de descarga es local (localhost): WhatsApp no lo vuelve clicable "
            "y el celular no podría abrirlo. Adjuntá el PDF descargado al chat. "
            "En el servidor público el mensaje sí lleva el link."
        )

    medico_nombre, medico_email, medico_tel_raw = _medico_contacto_estudio(estudio)

    if enviar_email:
        destino = (paciente.email or "").strip()
        if not destino:
            resultado.advertencias.append("El paciente no tiene email registrado.")
        else:
            _enviar_email_pdf_micro(
                destino=destino,
                estudio=estudio,
                pdf_bytes=pdf_bytes,
                filename=filename,
                enlace_descarga=enlace_wa,
                destinatario_label="paciente",
            )
            resultado.email_enviado = True
            resultado.email_destinos.append(destino)
            resultado.email_adjunto_pdf = True

    if enviar_email_medico:
        if not estudio.medico_interno_id:
            resultado.advertencias.append(
                "El estudio no tiene médico interno: no se puede enviar al solicitante."
            )
        elif not medico_email:
            resultado.advertencias.append(
                "El médico solicitante no tiene email registrado "
                f"({medico_nombre or 'sin nombre'})."
            )
        else:
            _enviar_email_pdf_micro(
                destino=medico_email,
                estudio=estudio,
                pdf_bytes=pdf_bytes,
                filename=filename,
                enlace_descarga=enlace_wa,
                destinatario_label="medico",
            )
            resultado.email_enviado = True
            resultado.email_destinos.append(medico_email)
            resultado.email_adjunto_pdf = True

    if resultado.email_destinos:
        resultado.email_destino = ", ".join(resultado.email_destinos)

    def _enviar_wa(
        *,
        telefono_raw: str | None,
        mensaje: str,
        rol: str,
        sin_tel_msg: str,
    ) -> None:
        telefono = _normalize_whatsapp_phone(telefono_raw)
        if not telefono:
            resultado.advertencias.append(sin_tel_msg)
            return
        media_url = enlace_wa
        enviado_api, error_api = _intentar_twilio_whatsapp(
            telefono,
            mensaje,
            media_url=media_url,
        )
        enlace = _enlace_whatsapp_web(telefono, mensaje)
        resultado.whatsapp_enlaces.append(
            {"rol": rol, "telefono": telefono, "enlace": enlace}
        )
        if not resultado.whatsapp_telefono:
            resultado.whatsapp_telefono = telefono
        if not resultado.whatsapp_enlace:
            resultado.whatsapp_enlace = enlace

        if enviado_api:
            resultado.whatsapp_enviado = True
            resultado.whatsapp_pdf_adjunto = bool(media_url) or resultado.whatsapp_pdf_adjunto
            if not media_url:
                resultado.advertencias.append(
                    f"WhatsApp ({rol}) enviado solo como texto (sin URL pública para el PDF)."
                )
        else:
            if error_api and error_api not in resultado.advertencias:
                resultado.advertencias.append(error_api)
            resultado.advertencias.append(
                f"Se abrirá WhatsApp ({rol}): confirmá Enviar. "
                "El PDF se descarga para adjuntarlo si hace falta."
            )

    if enviar_whatsapp:
        _enviar_wa(
            telefono_raw=getattr(paciente, "telefono", None),
            mensaje=_mensaje_whatsapp_paciente_micro(estudio, enlace_wa),
            rol="paciente",
            sin_tel_msg="El paciente no tiene teléfono registrado para WhatsApp.",
        )

    if enviar_whatsapp_medico:
        if not estudio.medico_interno_id:
            resultado.advertencias.append(
                "El estudio no tiene médico interno: no se puede enviar WhatsApp al solicitante."
            )
        else:
            _enviar_wa(
                telefono_raw=medico_tel_raw,
                mensaje=_mensaje_whatsapp_medico_micro(estudio, enlace_wa),
                rol="medico",
                sin_tel_msg=(
                    "El médico solicitante no tiene teléfono registrado para WhatsApp "
                    f"({medico_nombre or 'sin nombre'})."
                ),
            )

    tiene_fallback_wa = bool(resultado.whatsapp_enlaces)
    if (
        not resultado.email_enviado
        and not resultado.whatsapp_enviado
        and not tiene_fallback_wa
    ):
        raise EnvioInformeError(
            "No hay datos de contacto del paciente ni del médico para enviar el informe."
        )

    before = safe_model_snapshot(estudio)
    log_update(
        actor=actor,
        entity=estudio,
        before=before,
        module="laboratorio",
        metadata={
            "accion": "enviar_informe_micro",
            "view": view,
            "email": resultado.email_enviado,
            "email_adjunto_pdf": resultado.email_adjunto_pdf,
            "email_destinos": resultado.email_destinos,
            "whatsapp": resultado.whatsapp_enviado,
            "whatsapp_pdf_adjunto": resultado.whatsapp_pdf_adjunto,
            "whatsapp_roles": [e.get("rol") for e in resultado.whatsapp_enlaces],
            "estudio_id": estudio.pk,
            "numero_estudio": estudio.numero,
        },
    )
    return resultado
