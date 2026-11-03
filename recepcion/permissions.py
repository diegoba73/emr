from rest_framework import permissions

from api.permissions import emr_staff_or_admin_global, get_normalized_role
from usuarios.roles import ROLES_SECRETARIA_EMR

# Acciones que el médico puede hacer sobre sus pacientes en espera (TV + push).
_ACCIONES_MEDICO_COLA = frozenset(
    {
        'list',
        'retrieve',
        'tablero',
        'llamar',
        'en_atencion',
        'atendido',
        'atendido_por_turno',
        'no_asistio',
    }
)

_ACCIONES_LABORATORIO_COLA = frozenset(
    {
        'list',
        'retrieve',
        'tablero',
        'llamar',
        'en_atencion',
        'atendido',
        'no_asistio',
        'mover_puesto',
    }
)


def puede_operar_recepcion(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_superuser', False) or emr_staff_or_admin_global(user):
        return True
    role = get_normalized_role(user)
    return role in ('admin', 'enfermeria') or role in ROLES_SECRETARIA_EMR


def es_medico_recepcion(user) -> bool:
    return bool(user and user.is_authenticated and get_normalized_role(user) == 'medico')


def es_laboratorio_recepcion(user) -> bool:
    """Usuario laboratorio (cola L / extracciones)."""
    if not user or not user.is_authenticated:
        return False
    role = get_normalized_role(user)
    return role in ('laboratorio', 'secretaria_lab', 'bioquimico')


def es_solo_laboratorio(user) -> bool:
    """Lab sin permisos de secretaría EMR (opera solo EXTRACCION)."""
    if puede_operar_recepcion(user) or getattr(user, 'is_superuser', False):
        return False
    return es_laboratorio_recepcion(user)


def medico_perfil(user):
    from archivos_medicos.access import get_medico_perfil

    return get_medico_perfil(user)


def medico_ids_para_cola(user) -> list[int]:
    """
    IDs de Medico visibles para el usuario en recepción.

    Incluye el perfil vinculado al user y homónimos huérfanos (mismo apellido
    + primer nombre, sin user), frecuentes por duplicados de agenda/import.
    """
    m = medico_perfil(user)
    if not m:
        return []
    ids = {m.id}
    from medicos.models import Medico

    ap = (m.apellido or '').strip()
    primer = ((m.nombre or '').strip().split() or [''])[0]
    if ap:
        q = Medico.objects.filter(apellido__iexact=ap)
        if primer:
            q = q.filter(nombre__istartswith=primer)
        ids.update(q.values_list('id', flat=True))
    return list(ids)


def medico_puede_ver_llegada(user, llegada) -> bool:
    """El médico solo opera llegadas cuyo turno es el suyo (o homónimo)."""
    ids = medico_ids_para_cola(user)
    if not ids:
        return False
    return bool(
        llegada.turno_id
        and getattr(llegada, 'turno', None)
        and llegada.turno.medico_id in ids
    )


def es_llegada_extraccion(llegada) -> bool:
    return getattr(llegada, 'tipo_actividad', None) == 'EXTRACCION'


def llegada_en_cola_medica(llegada) -> bool:
    """
    Tras check-in administrativo (EN_ESPERA / llamado médico / en atención).
    Un LLAMADO de recepción (zona RECEPCION) sigue siendo de secretaría.
    """
    from .models import LlegadaRecepcion

    if es_llegada_extraccion(llegada):
        return False
    if not llegada.turno_id or not getattr(llegada, 'turno', None):
        return False
    if not llegada.turno.medico_id:
        return False
    if llegada.estado_flujo in (
        LlegadaRecepcion.EstadoFlujo.EN_ESPERA,
        LlegadaRecepcion.EstadoFlujo.EN_ATENCION,
    ):
        return True
    if (
        llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.LLAMADO
        and (llegada.zona_llamado or '') == 'MEDICO'
    ):
        return True
    return False


def puede_llamar_o_atender(user, llegada) -> bool:
    """
    Quién puede llamar/atender:
    - EXTRACCION: laboratorio (o admin/superuser); no secretaría.
    - Cola médica: solo el médico del turno (o admin).
    - Resto en recepción: secretaría.
    """
    if getattr(user, 'is_superuser', False) or emr_staff_or_admin_global(user):
        return True

    if es_llegada_extraccion(llegada):
        return es_laboratorio_recepcion(user)

    if llegada_en_cola_medica(llegada):
        if es_medico_recepcion(user):
            return medico_puede_ver_llegada(user, llegada)
        return False

    # Cola recepción (T/S/E/P anunciados): secretaría / enfermería.
    if puede_operar_recepcion(user):
        return True
    return False


def puede_derivar_a_medico(user, llegada) -> bool:
    """Check-in administrativo hacia cola del médico: secretaría, no L."""
    if es_llegada_extraccion(llegada):
        return False
    if getattr(user, 'is_superuser', False) or emr_staff_or_admin_global(user):
        return True
    return puede_operar_recepcion(user)


def puede_configurar_recepcion(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_superuser', False) or emr_staff_or_admin_global(user):
        return True
    return get_normalized_role(user) in ('admin',)


class RecepcionOperacionPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if puede_operar_recepcion(request.user):
            return True
        if es_medico_recepcion(request.user):
            action = getattr(view, 'action', None)
            return action in _ACCIONES_MEDICO_COLA
        if es_laboratorio_recepcion(request.user):
            action = getattr(view, 'action', None)
            return action in _ACCIONES_LABORATORIO_COLA
        return False

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, 'is_superuser', False) or emr_staff_or_admin_global(
            request.user
        ):
            return True
        if es_solo_laboratorio(request.user):
            return es_llegada_extraccion(obj)
        if puede_operar_recepcion(request.user):
            # Secretaría no opera objetos L (salvo lectura vía list filtrado).
            action = getattr(view, 'action', None)
            if es_llegada_extraccion(obj) and action not in (
                'retrieve',
                'list',
                None,
            ):
                if action in ('llamar', 'en_atencion', 'atendido', 'no_asistio', 'derivar_espera'):
                    return False
            return True
        if es_medico_recepcion(request.user):
            return medico_puede_ver_llegada(request.user, obj)
        return False


class RecepcionConfigPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return puede_operar_recepcion(request.user) or es_laboratorio_recepcion(
                request.user
            )
        return puede_configurar_recepcion(request.user)
