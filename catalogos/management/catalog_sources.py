"""Utilidades compartidas para descargar fuentes oficiales de catálogos."""
from __future__ import annotations

import tempfile
from pathlib import Path

import requests
from django.conf import settings


def data_dir() -> Path:
    path = Path(settings.BASE_DIR) / 'data'
    path.mkdir(exist_ok=True)
    return path


def download_to_cache(url: str, cache_name: str, timeout: int = 180) -> str:
    cache_path = data_dir() / cache_name
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    cache_path.write_bytes(response.content)
    return str(cache_path)


def resolve_file(*, local_path: str | None, url: str, cache_name: str) -> str:
    if local_path:
        path = Path(local_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f'No existe: {path}')
        return str(path)
    try:
        return download_to_cache(url, cache_name)
    except Exception:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(cache_name).suffix)
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        tmp.write(response.content)
        tmp.close()
        return tmp.name
