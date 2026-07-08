"""Acceso clínico a estudios complementarios (reutiliza vínculos de archivos_medicos)."""

from __future__ import annotations

from archivos_medicos.access import medico_puede_acceder_paciente
from usuarios.roles import ROLES_ESTUDIO_COMPLEMENTARIO, es_rol_estudio_complementario


def _rol(user) -> str:
    return str(getattr(user, 'rol', '') or '').lower()


def usuario_puede_escribir_estudio(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    rol = _rol(user)
    return rol in {'admin', 'medico', *ROLES_ESTUDIO_COMPLEMENTARIO}


def usuario_puede_asignar_turno_estudio(user) -> bool:
    """Agenda de estudios: secretaría y admin."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _rol(user) in {'admin', 'secretaria'}


def usuario_puede_ver_estudios_agenda(user) -> bool:
    """Listado para turnera / asignación de turnos."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    rol = _rol(user)
    return rol in {'admin', 'secretaria', 'medico', *ROLES_ESTUDIO_COMPLEMENTARIO}


def usuario_puede_ver_estudio(user, estudio) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    rol = _rol(user)
    if rol == 'admin':
        return True
    if es_rol_estudio_complementario(rol):
        return True
    if rol == 'secretaria':
        return True
    if rol in ('enfermeria', 'laboratorio'):
        return False
    if rol == 'medico':
        try:
            return medico_puede_acceder_paciente(user.medico, estudio.paciente)
        except Exception:
            return False

    return False


def usuario_puede_ver_estudio_clinico(user, estudio) -> bool:
    """Vista clínica: todos los estados del paciente vinculado o cola institucional."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    rol = _rol(user)
    if rol == 'admin':
        return True
    if es_rol_estudio_complementario(rol):
        return True
    if rol == 'secretaria':
        return True
    if rol in ('enfermeria', 'laboratorio'):
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
    rol = _rol(user)
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
    rol = _rol(user)
    if rol == 'admin':
        return True
    if es_rol_estudio_complementario(rol):
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
    rol = _rol(user)
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
    if es_rol_estudio_complementario(rol):
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
    return user.is_superuser or _rol(user) == 'admin'
