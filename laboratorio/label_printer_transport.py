"""
Transporte mínimo de ZPL a impresora de red (socket TCP).

Sin dependencias externas. Sin auto-retry (timeout ambiguo = posible impresión
ya realizada; el operador decide reimprimir explícitamente).
"""
from __future__ import annotations

import logging
import socket
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


class LabelPrinterError(Exception):
    """Error operativo de impresión (no filtrar host/credenciales al cliente)."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class LabelPrinterConfig:
    enabled: bool
    host: str
    port: int
    timeout_seconds: float
    profile_key: str


def get_label_printer_config() -> LabelPrinterConfig:
    return LabelPrinterConfig(
        enabled=bool(getattr(settings, "LIMS_LABEL_PRINTER_ENABLED", False)),
        host=(getattr(settings, "LIMS_LABEL_PRINTER_HOST", "") or "").strip(),
        port=int(getattr(settings, "LIMS_LABEL_PRINTER_PORT", 9100) or 9100),
        timeout_seconds=float(getattr(settings, "LIMS_LABEL_PRINTER_TIMEOUT_SECONDS", 5) or 5),
        profile_key=(
            getattr(settings, "LIMS_LABEL_PRINTER_PROFILE", "3nstar_ldt114_203_40x23")
            or "3nstar_ldt114_203_40x23"
        ).strip(),
    )


def send_zpl_to_network_printer(zpl: str, *, config: LabelPrinterConfig | None = None) -> None:
    """
    Envía ZPL una sola vez por TCP. Cierra siempre el socket.

    No registra el contenido ZPL ni PHI.
    """
    cfg = config or get_label_printer_config()
    if not cfg.enabled:
        raise LabelPrinterError(
            "printer_disabled",
            "Impresora de etiquetas no configurada",
        )
    if not cfg.host:
        raise LabelPrinterError(
            "printer_misconfigured",
            "Impresora de etiquetas no configurada",
        )
    if cfg.port <= 0 or cfg.port > 65535:
        raise LabelPrinterError(
            "printer_misconfigured",
            "Impresora de etiquetas no configurada",
        )

    payload = (zpl or "").encode("utf-8")
    if not payload:
        raise LabelPrinterError("empty_zpl", "No hay datos para imprimir.")

    sock: socket.socket | None = None
    try:
        sock = socket.create_connection((cfg.host, cfg.port), timeout=cfg.timeout_seconds)
        sock.settimeout(cfg.timeout_seconds)
        sock.sendall(payload)
    except TimeoutError as exc:
        logger.warning("label_printer_timeout profile=%s", cfg.profile_key)
        raise LabelPrinterError(
            "printer_timeout",
            "No se pudo confirmar la impresión. Verifique la impresora antes de reimprimir.",
        ) from exc
    except OSError as exc:
        # Incluye ConnectionRefusedError y timeouts de socket en algunas plataformas.
        errno_name = type(exc).__name__
        if "Timeout" in errno_name or isinstance(exc, socket.timeout):
            logger.warning("label_printer_timeout profile=%s", cfg.profile_key)
            raise LabelPrinterError(
                "printer_timeout",
                "No se pudo confirmar la impresión. Verifique la impresora antes de reimprimir.",
            ) from exc
        logger.warning("label_printer_connection_failed profile=%s err=%s", cfg.profile_key, errno_name)
        raise LabelPrinterError(
            "printer_unreachable",
            "No se pudo confirmar la impresión. Verifique la impresora antes de reimprimir.",
        ) from exc
    finally:
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
