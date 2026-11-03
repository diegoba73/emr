#!/usr/bin/env python3
"""Avisa si EMR_LAN_IPS no parece la IP LAN actual (solo diagnóstico)."""
from __future__ import annotations

import os
import socket
import sys


def guess_lan_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('192.168.1.1', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith('192.168.') or ip.startswith('10.'):
            return ip
    except OSError:
        pass
    return None


def main() -> int:
    configured = (os.environ.get('EMR_LAN_IPS') or '').split(',')[0].strip()
    guessed = guess_lan_ip()
    if not configured:
        print('WARN: EMR_LAN_IPS vacío')
        return 1
    if guessed and guessed != configured:
        print(
            f'WARN: EMR_LAN_IPS={configured} pero la IP local parece {guessed}. '
            'En Windows: powershell -File scripts/sync_lan_ip.ps1'
        )
        return 2
    print(f'OK: EMR_LAN_IPS={configured}' + (f' (local={guessed})' if guessed else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
