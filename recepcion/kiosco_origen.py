"""Origen del QR del kiosco: URL pública del EMR (prod) o LAN (dev)."""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

from synesis.lan_env import (
    is_usable_lan_ip,
    parse_kiosco_lan_origins,
    primary_kiosco_lan_origin,
    primary_kiosco_origin,
    public_emr_origin,
)


def _norm_origin(raw: str) -> str:
    t = (raw or '').strip().rstrip('/')
    if not t:
        return ''
    if not t.lower().startswith(('http://', 'https://')):
        t = f'http://{t}'
    return t


def _host_from_url_or_host(value: str) -> str:
    v = (value or '').strip()
    if not v:
        return ''
    if '://' in v:
        return (urlparse(v).hostname or '').lower()
    return v.split('/')[0].split(':')[0].lower()


def _frontend_port() -> str:
    return (os.getenv('EMR_KIOSCO_FRONTEND_PORT') or '3000').strip() or '3000'


def _origin_from_lan_host(host: str, *, scheme: str = 'http') -> str:
    host = (host or '').strip()
    if not host:
        return ''
    if ':' in host and not host.startswith('['):
        return _norm_origin(f'{scheme}://{host}')
    port = _frontend_port()
    if port in ('80', '443'):
        return _norm_origin(f'{scheme}://{host}')
    return _norm_origin(f'{scheme}://{host}:{port}')


def _guess_lan_ipv4() -> str:
    if os.path.exists('/.dockerenv'):
        return ''
    for probe in ('192.168.1.1', '10.0.0.1', '172.16.0.1'):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            s.connect((probe, 1))
            ip = s.getsockname()[0]
            s.close()
            if is_usable_lan_ip(ip):
                return ip
        except Exception:
            continue
    return ''


def _origin_from_request_headers(request) -> str:
    origin = request.META.get('HTTP_ORIGIN') or ''
    referer = request.META.get('HTTP_REFERER') or ''
    xf_host = request.META.get('HTTP_X_FORWARDED_HOST') or ''
    host = request.META.get('HTTP_HOST') or ''
    for raw in (origin, referer, xf_host, host):
        if raw.startswith('http'):
            p = urlparse(raw)
            if p.hostname and is_usable_lan_ip(p.hostname):
                return _norm_origin(f'{p.scheme}://{p.netloc}')
        h = _host_from_url_or_host(raw)
        if is_usable_lan_ip(h):
            return _origin_from_lan_host(h)
    return ''


def resolver_origen_espera_kiosco(request=None) -> dict:
    """
    Prioridad del enlace del QR / anuncio:
    1. URL pública del EMR (PUBLIC_API_BASE_URL / EMR_KIOSCO_PUBLIC_ORIGIN) — CEHTA/prod
    2. EMR_KIOSCO_LAN_* / EMR_LAN_IPS — desarrollo local
    3. Request si ya se abrió por IP LAN
    4. Detección host (fuera de Docker)
    """
    public = public_emr_origin()
    if public:
        lan = parse_kiosco_lan_origins()
        origins = [public] + [o for o in lan if o != public]
        return {
            'espera_origin': public,
            'espera_origins': origins,
            'fuente': 'public',
            'es_lan': False,
            'lan_ips': [_host_from_url_or_host(o) for o in lan],
        }

    configured = parse_kiosco_lan_origins()
    primary = primary_kiosco_lan_origin() or primary_kiosco_origin()
    if primary:
        return {
            'espera_origin': primary,
            'espera_origins': configured or [primary],
            'fuente': 'env',
            'es_lan': True,
            'lan_ips': [_host_from_url_or_host(o) for o in configured],
        }

    if request is not None:
        from_req = _origin_from_request_headers(request)
        if from_req:
            return {
                'espera_origin': from_req,
                'espera_origins': [from_req],
                'fuente': 'request',
                'es_lan': True,
                'lan_ips': [_host_from_url_or_host(from_req)],
            }

    guessed = _guess_lan_ipv4()
    if guessed:
        origin = _origin_from_lan_host(guessed)
        return {
            'espera_origin': origin,
            'espera_origins': [origin],
            'fuente': 'detectado',
            'es_lan': True,
            'lan_ips': [guessed],
        }

    return {
        'espera_origin': '',
        'espera_origins': [],
        'fuente': 'ninguna',
        'es_lan': False,
        'lan_ips': [],
    }
