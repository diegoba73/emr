"""Acceso clínico a estudios complementarios (reutiliza vínculos de archivos_medicos)."""

from __future__ import annotations

from archivos_medicos.access import medico_puede_acceder_paciente


def usuario_puede_escribir_estudio(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    rol = str(getattr(user, 'rol', '') or '').lower()
    return rol in {'admin', 'medico'}


def usuario_puede_ver_estudio(user, estudio) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    rol = str(getattr(user, 'rol', '') or '').lower()
    if rol == 'admin':
        return True
    if rol in ('secretaria', 'enfermeria', 'laboratorio'):
        return False
    if rol == 'medico':
        try:
            return medico_puede_acceder_paciente(user.medico, estudio.paciente)
        except Exception:
            return False

    return False


def usuario_puede_ver_estudio_clinico(user, estudio) -> bool:
    """Vista clínica (médico/admin): todos los estados del paciente vinculado."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    rol = str(getattr(user, 'rol', '') or '').lower()
    if rol == 'admin':
        return True
    if rol in ('secretaria', 'enfermeria', 'laboratorio'):
        return False
    if rol == 'medico':
        try:
            return medico_puede_acceder_paciente(user.medico, estudio.paciente)
        except Exception:
            return False
    if rol == 'paciente':
        try:
            if estudio.paciente_id != user.paciente.id:
                return False
            return estudio.estado == estudio.Estado.ENTREGADO
        except Exception:
            return False

    return False


def usuario_puede_descargar_archivo_estudio(user, estudio) -> bool:
    if not user.is_authenticated:
        return False
    rol = str(getattr(user, 'rol', '') or '').lower()
    if rol in ('secretaria', 'enfermeria', 'laboratorio'):
        return False
    if rol == 'paciente':
        try:
            return (
                estudio.paciente_id == user.paciente.id
                and estudio.estado == estudio.Estado.ENTREGADO
            )
        except Exception:
            return False
    return usuario_puede_ver_estudio_clinico(user, estudio)


def usuario_puede_crear_estudio(user, paciente) -> bool:
    if not usuario_puede_escribir_estudio(user):
        return False
    if user.is_superuser:
        return True
    rol = str(getattr(user, 'rol', '') or '').lower()
    if rol == 'admin':
        return True
    if rol == 'medico':
        try:
            return medico_puede_acceder_paciente(user.medico, paciente)
        except Exception:
            return False
    return False


def usuario_puede_descargar_pdf_informe(user, estudio, informe) -> bool:
    """Descarga de PDF del informe — sin filename original ni /media/."""
    if not user.is_authenticated:
        return False
    rol = str(getattr(user, 'rol', '') or '').lower()
    if rol in ('secretaria', 'enfermeria', 'laboratorio'):
        return False
    if informe.estudio_id != estudio.pk:
        return False
    if rol == 'paciente':
        try:
            return (
                estudio.paciente_id == user.paciente.id
                and estudio.estado == estudio.Estado.ENTREGADO
                and informe.estado == informe.EstadoInforme.VALIDADO
                and informe.es_vigente
            )
        except Exception:
            return False
    if user.is_superuser or rol == 'admin':
        return True
    if rol == 'medico':
        try:
            return medico_puede_acceder_paciente(user.medico, estudio.paciente)
        except Exception:
            return False
    return False


def usuario_puede_validar_informe(user) -> bool:
    """C6.4.1: validación final solo admin/superuser."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or str(getattr(user, 'rol', '') or '').lower() == 'admin'
