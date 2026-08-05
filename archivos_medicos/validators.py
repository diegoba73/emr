"""
Validadores para archivos médicos.
"""
from __future__ import annotations

import os

from django.core.exceptions import ValidationError

# Extensiones globales permitidas (cualquier tipo_archivo).
EXTENSIONES_PERMITIDAS = [
    '.dcm',
    '.nii',
    '.nii.gz',
    '.jpg',
    '.jpeg',
    '.png',
    '.tif',
    '.tiff',
    '.webp',
    '.pdf',
    '.doc',
    '.docx',
    '.txt',
]

# Extensiones esperadas por categoría clínica.
EXTENSIONES_POR_TIPO = {
    'DICOM': ['.dcm'],
    'NIFTI': ['.nii', '.nii.gz'],
    'RAYOS_X': ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.dcm', '.pdf'],
    'TOMOGRAFIA': ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.dcm', '.nii', '.nii.gz', '.pdf'],
    'RESONANCIA': ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.dcm', '.nii', '.nii.gz', '.pdf'],
    'ULTRASONIDO': ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.dcm', '.pdf'],
    'FOTO_CLINICA': ['.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'],
    'PATOLOGIA': ['.tif', '.tiff', '.png', '.jpg', '.jpeg'],
    'PDF': ['.pdf'],
    'OTRO': list(EXTENSIONES_PERMITIDAS),
}


def extension_archivo(nombre_archivo: str) -> str:
    """Obtiene la extensión (incluye .nii.gz)."""
    nombre_lower = (nombre_archivo or '').lower()
    if nombre_lower.endswith('.nii.gz'):
        return '.nii.gz'
    _, extension = os.path.splitext(nombre_lower)
    return extension


def validar_tamanio_archivo(archivo):
    """Valida que el tamaño del archivo no exceda 10MB."""
    max_mb = 10
    max_bytes = max_mb * 1024 * 1024
    if archivo.size > max_bytes:
        tamanio_mb = archivo.size / (1024 * 1024)
        raise ValidationError(
            f'El archivo es demasiado grande ({tamanio_mb:.2f} MB). '
            f'El tamaño máximo permitido es {max_mb} MB.'
        )


def validar_extension_archivo(archivo):
    """Valida que la extensión del archivo esté en la lista permitida."""
    extension = extension_archivo(getattr(archivo, 'name', '') or '')
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValidationError(
            f'La extensión "{extension}" no está permitida. '
            f'Extensiones permitidas: {", ".join(EXTENSIONES_PERMITIDAS)}'
        )


def validar_extension_para_tipo(nombre_archivo: str, tipo_archivo: str) -> None:
    """Valida que la extensión sea coherente con el tipo_archivo elegido."""
    extension = extension_archivo(nombre_archivo)
    permitidas = EXTENSIONES_POR_TIPO.get(tipo_archivo) or EXTENSIONES_PERMITIDAS
    if extension not in permitidas:
        raise ValidationError(
            f'Para el tipo «{tipo_archivo}» se esperan archivos '
            f'{", ".join(permitidas)}. Recibido: «{extension or "(sin extensión)"}».'
        )
