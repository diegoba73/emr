"""
Validadores para archivos médicos.
Implementa lógica de validación reutilizable siguiendo Clean Architecture.
"""
from django.core.exceptions import ValidationError
import os


def validar_tamanio_archivo(archivo):
    """
    Valida que el tamaño del archivo no exceda 10MB.
    
    Args:
        archivo: El archivo a validar (FileField)
    
    Raises:
        ValidationError: Si el archivo es mayor a 10MB
    """
    MAX_TAMANIO_MB = 10
    MAX_TAMANIO_BYTES = MAX_TAMANIO_MB * 1024 * 1024  # 10MB en bytes
    
    if archivo.size > MAX_TAMANIO_BYTES:
        tamanio_mb = archivo.size / (1024 * 1024)
        raise ValidationError(
            f'El archivo es demasiado grande ({tamanio_mb:.2f} MB). '
            f'El tamaño máximo permitido es {MAX_TAMANIO_MB} MB.'
        )


def validar_extension_archivo(archivo):
    """
    Valida que la extensión del archivo esté en la lista permitida.
    
    Extensiones permitidas:
    - .dcm, .nii, .nii.gz (imágenes médicas)
    - .jpg, .jpeg, .png, .tif, .tiff (imágenes)
    - .pdf, .doc, .docx, .txt (documentos)
    
    Args:
        archivo: El archivo a validar (FileField)
    
    Raises:
        ValidationError: Si la extensión no está permitida
    """
    EXTENSIONES_PERMITIDAS = [
        '.dcm',      # DICOM
        '.nii',      # NIFTI
        '.nii.gz',   # NIFTI comprimido
        '.jpg',
        '.jpeg',
        '.png',
        '.tif',
        '.tiff',
        '.pdf',
        '.doc',
        '.docx',
        '.txt',
    ]
    
    # Obtener el nombre del archivo
    nombre_archivo = archivo.name
    
    # Obtener la extensión (incluyendo .nii.gz)
    nombre_lower = nombre_archivo.lower()
    
    # Verificar primero .nii.gz (extensión compuesta)
    if nombre_lower.endswith('.nii.gz'):
        extension = '.nii.gz'
    else:
        # Obtener la extensión normal
        _, extension = os.path.splitext(nombre_lower)
    
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValidationError(
            f'La extensión "{extension}" no está permitida. '
            f'Extensiones permitidas: {", ".join(EXTENSIONES_PERMITIDAS)}'
        )



