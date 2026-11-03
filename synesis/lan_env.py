"""
Orígenes del kiosco / recepción (QR) y red LAN opcional.

Producción (CEHTA/ICPL — mismo EMR):
  PUBLIC_API_BASE_URL=https://emr.icpueblodeluis.com.ar:8080
  (opcional) EMR_KIOSCO_PUBLIC_ORIGIN=https://emr.icpueblodeluis.com.ar:8080

Desarrollo local (solo Wi‑Fi de la PC, opcional):
  EMR_LAN_IPS=192.168.1.25
  EMR_KIOSCO_LAN_ORIGIN=http://192.168.1.25:3000
  EMR_KIOSCO_LAN_ORIGINS=...
  EMR_KIOSCO_FRONTEND_PORT=3000
  EMR_API_PORT=8000
"""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse

from .env_config import parse_csv_env


def _frontend_port() -> str:
    return (os.getenv('EMR_KIOSCO_FRONTEND_PORT') or '3000').strip() or '3000'


def _api_port() -> str:
    return (os.getenv('EMR_API_PORT') or '8000').strip() or '8000'


def _norm_origin(raw: str) -> str:
    t = (raw or '').strip().rstrip('/')
    if not t:
        return ''
    if not t.lower().startswith(('http://', 'https://')):
        t = f'http://{t}'
    return t


def _host_only(value: str) -> str:
    v = (value or '').strip()
    if not v:
        return ''
    if '://' in v:
        return (urlparse(v).hostname or '').lower()
    return v.split('/')[0].split(':')[0].lower()


def is_usable_lan_ip(host: str) -> bool:
    host = (host or '').strip().lower()
    if not host or host in ('localhost', '127.0.0.1', '::1', '0.0.0.0', 'backend'):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.is_loopback or ip.is_link_local or not ip.is_private:
        return False
    if isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network('172.17.0.0/16'):
        return False
    return True


def parse_lan_ips() -> list[str]:
    """IPs LAN explícitas + hosts extraídos de orígenes de kiosco."""
    seen: list[str] = []
    for raw in parse_csv_env('EMR_LAN_IPS'):
        h = _host_only(raw)
        if is_usable_lan_ip(h) and h not in seen:
            seen.append(h)
    for raw in parse_csv_env('EMR_KIOSCO_LAN_ORIGINS'):
        h = _host_only(raw)
        if is_usable_lan_ip(h) and h not in seen:
            seen.append(h)
    single = os.getenv('EMR_KIOSCO_LAN_ORIGIN') or ''
    if single.strip():
        h = _host_only(single)
        if is_usable_lan_ip(h) and h not in seen:
            seen.append(h)
    return seen


def parse_kiosco_lan_origins() -> list[str]:
    """
    Orígenes absolutos para QR / CORS frontend.
    Primario: EMR_KIOSCO_LAN_ORIGIN; luego ORIGINS; luego derivados de EMR_LAN_IPS.
    """
    origins: list[str] = []
    single = _norm_origin(os.getenv('EMR_KIOSCO_LAN_ORIGIN') or '')
    if single and is_usable_lan_ip(_host_only(single)):
        origins.append(single)
    for raw in parse_csv_env('EMR_KIOSCO_LAN_ORIGINS'):
        o = _norm_origin(raw)
        if o and is_usable_lan_ip(_host_only(o)) and o not in origins:
            origins.append(o)
    fe = _frontend_port()
    for ip in parse_lan_ips():
        o = _norm_origin(f'http://{ip}') if fe in ('80', '443') else _norm_origin(f'http://{ip}:{fe}')
        if o not in origins:
            origins.append(o)
    return origins


def primary_kiosco_lan_origin() -> str:
    origins = parse_kiosco_lan_origins()
    return origins[0] if origins else ''


def public_emr_origin() -> str:
    """
    Origen HTTPS (o http) alcanzable desde Internet / celular fuera de la LAN del servidor.
    Prioridad: EMR_KIOSCO_PUBLIC_ORIGIN → PUBLIC_API_BASE_URL.
    """
    for key in ('EMR_KIOSCO_PUBLIC_ORIGIN', 'PUBLIC_API_BASE_URL'):
        o = _norm_origin(os.getenv(key) or '')
        if not o:
            continue
        host = _host_only(o)
        if not host or host in ('localhost', '127.0.0.1', '::1', '0.0.0.0', 'backend'):
            continue
        # Acepta dominio público o IP; el QR de CEHTA usa el dominio del EMR.
        return o
    return ''


def primary_kiosco_origin() -> str:
    """Primario para QR: URL pública del EMR; si no hay, LAN de desarrollo."""
    return public_emr_origin() or primary_kiosco_lan_origin()


def lan_csrf_and_cors_origins() -> list[str]:
    """Orígenes http://IP:frontend y http://IP:api para CSRF/CORS."""
    out: list[str] = []
    fe = _frontend_port()
    api = _api_port()
    for ip in parse_lan_ips():
        for port in (fe, api):
            if port in ('80', '443'):
                o = f'http://{ip}'
            else:
                o = f'http://{ip}:{port}'
            if o not in out:
                out.append(o)
    for o in parse_kiosco_lan_origins():
        if o not in out:
            out.append(o)
    return out


def merge_unique(base: list[str], extra: list[str]) -> list[str]:
    out = list(base)
    for item in extra:
        if item and item not in out:
            out.append(item)
    return out
