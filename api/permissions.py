from rest_framework import permissions

from usuarios.roles import (
    ROLES_INTERNACION,
    ROLES_INTERNACION_CLINICA,
    ROLES_LIMS_CATALOG_READ,
    ROLES_LIMS_OPERADOR,
    ROLES_LIMS_OPERATIVA_LIMITADA,
    ROLES_LIMS_VALIDAR,
    ROLES_LIMS_WRITE,
    ROLES_SIN_BYPASS_EMR_STAFF,
)


def get_normalized_role(user):
    """Normaliza `User.rol` a minúsculas; cadena vacía si no hay usuario autenticado."""
    if not user or not getattr(user, 'is_authenticated', False):
        return ''
    return str(getattr(user, 'rol', '') or '').lower()


class LimsCatalogReadPermission(permissions.BasePermission):
    """
    Lectura de catálogos LIMS (tipos de muestra, exámenes, paneles).
    Roles: admin, laboratorio, médico (+ superuser).
    Sin acceso: anónimo y paciente. Los ViewSets son ReadOnly; métodos no seguros se niegan.
    """
    _roles_read = ROLES_LIMS_CATALOG_READ

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role in self._roles_read
        return False


class LimsTipoMuestraCatalogPermission(permissions.BasePermission):
    """
    Catálogo de tipos de muestra LIMS (sangre, orina, etc.).
    Lectura: roles clínicos con acceso LIMS. Escritura: admin, laboratorio y bioquímico.
    """

    _roles_read = ROLES_LIMS_CATALOG_READ
    _roles_write = ROLES_LIMS_WRITE

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role in self._roles_read
        if request.method in ('POST', 'PUT', 'PATCH'):
            return role in self._roles_write
        return False


class LimsTipoExamenCatalogPermission(permissions.BasePermission):
    """
    Catálogo de tipos de examen LIMS.
    Lectura: roles clínicos con acceso LIMS. Escritura: admin, laboratorio y bioquímico.
    """

    _roles_read = ROLES_LIMS_CATALOG_READ
    _roles_write = ROLES_LIMS_WRITE

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role in self._roles_read
        if request.method in ('POST', 'PUT', 'PATCH'):
            return role in self._roles_write
        return False


def usuario_puede_ver_solicitud_lims(user, solicitud) -> bool:
    """True si el usuario puede leer la orden LIMS (list/retrieve).

    Médico: órdenes propias **o** de pacientes con vínculo clínico
    (turno / consulta HC / atención), **o** órdenes ya informadas
    (FINALIZADO / INFORMADO_PARCIAL) — historial en ficha sin exigir
    ``medico_interno`` (p. ej. LabWin).
    Secretaría/enfermería: pueden ver el encabezado de todas las órdenes;
    los resultados clínicos se filtran con ``usuario_puede_ver_resultados_lims``.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    role = get_normalized_role(user)
    if role in ROLES_LIMS_WRITE:
        return True

    if role in ROLES_LIMS_OPERATIVA_LIMITADA:
        return True

    if role == 'medico':
        from laboratorio.access import ESTADOS_LECTURA_HISTORIAL_MEDICO

        if getattr(solicitud, 'estado', None) in ESTADOS_LECTURA_HISTORIAL_MEDICO:
            return True
        medico = getattr(solicitud, 'medico_interno', None)
        if medico and getattr(medico, 'user_id', None) == user.id:
            return True
        try:
            from archivos_medicos.access import medico_puede_acceder_paciente
            from pacientes.models import Paciente

            profile = user.medico
            paciente = getattr(solicitud, 'paciente', None)
            if paciente is None and getattr(solicitud, 'paciente_id', None):
                paciente = Paciente.objects.get(pk=solicitud.paciente_id)
            return bool(paciente and medico_puede_acceder_paciente(profile, paciente))
        except Exception:
            return False

    if role == 'paciente':
        try:
            return solicitud.paciente_id == user.paciente.id
        except Exception:
            return False

    return False


def usuario_puede_ver_resultados_lims(user, solicitud) -> bool:
    """True si el usuario puede ver valores de resultados / análisis longitudinal.

    Operadores LIMS (admin, laboratorio, bioquímico): siempre.
    Resto de roles clínicos: solo cuando la orden está validada (FINALIZADO).
    """
    if not usuario_puede_ver_solicitud_lims(user, solicitud):
        return False
    if user.is_superuser:
        return True
    role = get_normalized_role(user)
    if role in ROLES_LIMS_WRITE:
        return True
    return getattr(solicitud, 'estado', None) == 'FINALIZADO'


def usuario_puede_descargar_informe_lims(user, solicitud) -> bool:
    """PDF LIMS: solo orden FINALIZADO (validada por bioquímico). Sin borradores ni parciales."""
    if not usuario_puede_ver_solicitud_lims(user, solicitud):
        return False
    if getattr(solicitud, 'estado', None) != 'FINALIZADO':
        return False
    if user.is_superuser:
        return True
    role = get_normalized_role(user)
    if role in ROLES_LIMS_WRITE:
        return True
    if role in (*ROLES_LIMS_OPERATIVA_LIMITADA, 'medico', 'paciente'):
        return True
    return False


def usuario_puede_enviar_informe_lims(user, solicitud) -> bool:
    """Enviar PDF al paciente/médico: operadores LIMS y secretaría, solo FINALIZADO."""
    if not usuario_puede_ver_solicitud_lims(user, solicitud):
        return False
    if getattr(solicitud, 'estado', None) != 'FINALIZADO':
        return False
    if user.is_superuser:
        return True
    role = get_normalized_role(user)
    if role in ROLES_LIMS_WRITE:
        return True
    return role == 'secretaria'


def usuario_puede_operar_informe_micro(user) -> bool:
    """Crear / editar / emitir / anular / validar informes de microbiología.

    Solo bioquímico y admin (misma regla que validar en Lab. Clínico).
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    return get_normalized_role(user) in ROLES_LIMS_VALIDAR


def _medico_puede_ver_estudio_micro(user, estudio) -> bool:
    """Médico solicitante o con vínculo a la solicitud LIMS asociada."""
    if estudio is None:
        return False
    medico_interno_id = getattr(estudio, 'medico_interno_id', None)
    if medico_interno_id:
        try:
            if (
                hasattr(user, 'medico')
                and user.medico
                and user.medico.pk == medico_interno_id
            ):
                return True
        except Exception:
            pass
    solicitud = getattr(estudio, 'solicitud', None)
    if solicitud is None:
        return False
    return usuario_puede_ver_solicitud_lims(user, solicitud)


def usuario_puede_ver_contenido_informe_micro(user, informe) -> bool:
    """Contenido del informe micro.

    Bioquímico/admin: siempre (borrador, emitido, validado).
    Técnico laboratorio / médico: solo cuando el informe está VALIDADO.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    role = get_normalized_role(user)
    if role in ROLES_LIMS_VALIDAR:
        return True

    if getattr(informe, 'estado', None) != 'VALIDADO':
        return False

    estudio = getattr(informe, 'estudio', None)
    if role == 'laboratorio' or role in ROLES_LIMS_OPERATIVA_LIMITADA:
        return True
    if role == 'medico':
        return _medico_puede_ver_estudio_micro(user, estudio)
    return False


def usuario_puede_descargar_informe_micro(user, estudio) -> bool:
    """PDF micro: bio/admin con FINAL EMITIDO o VALIDADO; resto solo VALIDADO."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    role = get_normalized_role(user)

    if role == 'medico':
        if not _medico_puede_ver_estudio_micro(user, estudio):
            return False
    elif role in ROLES_LIMS_OPERATIVA_LIMITADA:
        pass
    elif role not in ROLES_LIMS_WRITE:
        return False

    from laboratorio.models_microbiologia import InformeMicrobiologia

    estados = ('EMITIDO', 'VALIDADO') if role in ROLES_LIMS_VALIDAR else ('VALIDADO',)
    return InformeMicrobiologia.objects.filter(
        estudio_id=estudio.pk,
        tipo='FINAL',
        estado__in=estados,
    ).exists()


_LIMS_SOLICITUD_READ_ROLES = frozenset({
    'admin',
    *ROLES_LIMS_OPERADOR,
    'medico',
    'secretaria',
    'enfermeria',
    'paciente',
})


class LimsSolicitudExamenPermission(permissions.BasePermission):
    """
    Permisos para SolicitudExamenViewSet.
    Carga/toma: operadores LIMS. Validar/liberar: solo bioquímico y admin.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        role = get_normalized_role(request.user)
        action = getattr(view, 'action', None)

        if action == 'list':
            return role in _LIMS_SOLICITUD_READ_ROLES
        if action == 'create':
            return role in (*ROLES_LIMS_WRITE, 'medico')
        if action == 'agregar_examenes':
            return role in (*ROLES_LIMS_WRITE, 'medico')
        if action == 'orden_abierta':
            return role in (*ROLES_LIMS_WRITE, 'medico', 'secretaria', 'enfermeria')
        if action == 'marcar_derivacion':
            return role in ROLES_LIMS_WRITE
        if action in ('retrieve', 'update', 'partial_update', 'destroy'):
            if action == 'retrieve' and role in _LIMS_SOLICITUD_READ_ROLES:
                return True
            if action in ('update', 'partial_update') and role in ROLES_LIMS_WRITE:
                return True
            if action == 'destroy' and role == 'admin':
                return True
            return False
        if action == 'cargar_resultados':
            return role in ROLES_LIMS_WRITE
        if action == 'tomar_muestra':
            return role in ROLES_LIMS_WRITE
        if action == 'enviar_informe':
            return role in (*ROLES_LIMS_WRITE, 'secretaria')
        if action in ('finalizar', 'validar'):
            return role in ROLES_LIMS_VALIDAR
        if action == 'tubos_preview':
            return role in (*ROLES_LIMS_WRITE, 'medico')
        if action == 'etiqueta':
            return role in ROLES_LIMS_WRITE
        if action == 'etiquetas_muestras':
            return role in ROLES_LIMS_WRITE
        if action == 'informe_pdf':
            return role in _LIMS_SOLICITUD_READ_ROLES
        if action == 'analisis_longitudinal':
            return role in _LIMS_SOLICITUD_READ_ROLES
        if action == 'historial_analitos':
            return role in _LIMS_SOLICITUD_READ_ROLES
        if action == 'sugerir_conclusion_hemograma':
            return role in ROLES_LIMS_WRITE
        if action == 'orden_informe':
            return role in ROLES_LIMS_WRITE
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        role = get_normalized_role(request.user)
        action = getattr(view, 'action', None)

        if action == 'retrieve':
            return usuario_puede_ver_solicitud_lims(request.user, obj)

        if action in ('update', 'partial_update'):
            return role in ROLES_LIMS_WRITE

        if action == 'destroy':
            return role == 'admin'

        if action == 'cargar_resultados':
            return role in ROLES_LIMS_WRITE

        if action == 'tomar_muestra':
            return role in ROLES_LIMS_WRITE

        if action == 'enviar_informe':
            return usuario_puede_enviar_informe_lims(request.user, obj)

        if action == 'agregar_examenes':
            if role in ROLES_LIMS_WRITE:
                return True
            if role == 'medico':
                return usuario_puede_ver_solicitud_lims(request.user, obj)
            return False

        if action == 'marcar_derivacion':
            return role in ROLES_LIMS_WRITE

        if action in ('finalizar', 'validar'):
            return role in ROLES_LIMS_VALIDAR

        if action == 'tubos_preview':
            return usuario_puede_ver_solicitud_lims(request.user, obj)

        if action == 'etiqueta':
            return role in ROLES_LIMS_WRITE

        if action == 'etiquetas_muestras':
            return role in ROLES_LIMS_WRITE

        if action == 'informe_pdf':
            return usuario_puede_descargar_informe_lims(request.user, obj)

        if action == 'analisis_longitudinal':
            return usuario_puede_ver_resultados_lims(request.user, obj)

        if action == 'historial_analitos':
            # Pre-carga: basta con poder ver la orden (no exige FINALIZADO).
            return usuario_puede_ver_solicitud_lims(request.user, obj)

        if action == 'sugerir_conclusion_hemograma':
            return role in ROLES_LIMS_WRITE

        if action == 'orden_informe':
            return role in ROLES_LIMS_WRITE

        return False


class IsSecretariaOrAdmin(permissions.BasePermission):
    """
    Permiso para secretarias y administradores
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Los superusuarios siempre tienen acceso
        if request.user.is_superuser:
            return True
        
        # Verificar si el usuario está en el grupo Secretarias o es secretaria
        return (request.user.groups.filter(name='Secretarias').exists() or 
                request.user.rol == 'secretaria')

class IsMedicoOrAdmin(permissions.BasePermission):
    """
    Permiso para médicos y administradores
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Los superusuarios siempre tienen acceso
        if request.user.is_superuser:
            return True
        
        # Verificar si el usuario está en el grupo Médicos o es médico
        return (request.user.groups.filter(name='Médicos').exists() or 
                request.user.rol == 'medico')

class IsMedicoOrEnfermeriaOrAdmin(permissions.BasePermission):
    """
    Permiso para médicos, enfermería y administradores
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Los superusuarios siempre tienen acceso
        if request.user.is_superuser:
            return True
        
        # Verificar si el usuario tiene rol apropiado
        user_rol = getattr(request.user, 'rol', None)
        if not user_rol:
            return False
        
        # Normalizar a minúsculas para comparación
        user_rol = str(user_rol).lower()
        return user_rol in ['medico', 'enfermeria', 'admin']


class IsInternacionStaff(permissions.BasePermission):
    """Acceso operativo a internación: médico, enfermería, admin y secretaría."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return get_normalized_role(request.user) in ROLES_INTERNACION


class IsInternacionClinica(permissions.BasePermission):
    """Evoluciones clínicas e infraestructura de internación: sin secretaría."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return get_normalized_role(request.user) in ROLES_INTERNACION_CLINICA


class ConsultaPermission(permissions.BasePermission):
    """Lectura de consultas: cualquier usuario autenticado (filtrado en queryset).
    Escritura: médico, enfermería o admin.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        checker = IsMedicoOrEnfermeriaOrAdmin()
        return checker.has_permission(request, view)


_ROLES_SIN_ACCESO_EMR_STAFF = ROLES_SIN_BYPASS_EMR_STAFF


def emr_staff_or_admin_global(user) -> bool:
    """Bypass staff/superuser para operaciones EMR globales.

    Operadores LIMS suelen tener ``is_staff=True``; no deben leer PHI EMR general.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = get_normalized_role(user)
    if role in _ROLES_SIN_ACCESO_EMR_STAFF:
        return False
    return bool(user.is_staff or role == 'admin')


def _atencion_is_staff_or_admin(user) -> bool:
    return emr_staff_or_admin_global(user)


def _atencion_user_medico(user):
    from archivos_medicos.access import get_medico_perfil

    return get_medico_perfil(user)


def _atencion_user_paciente(user):
    try:
        return user.paciente
    except Exception:
        return None


def _atencion_for_permission_obj(obj):
    """Normaliza el objeto de permiso a ``Atencion`` (p. ej. evolución o consulta ambulatoria)."""
    from turnos.models import Atencion
    if isinstance(obj, Atencion):
        return obj
    atencion = getattr(obj, 'atencion', None)
    if atencion is not None:
        return atencion
    return obj


_ATENCION_READ_ACTIONS = frozenset({'list', 'retrieve'})
_ATENCION_WRITE_ACTIONS = frozenset({'create', 'update', 'partial_update'})
_ATENCION_CLINICAL_ACTIONS = frozenset({
    'cerrar',
    'registrar_consulta',
    'crear_registro_ambulatorio',
    'cerrar_atencion',
    'registrar',
    'iniciar_guardia',
    'ensure_consulta_hc',
})


def filter_atencion_queryset_for_user(user, queryset):
    """Filtra atenciones según rol (QA-ROLE-01). Usado por AtencionViewSet activo y legacy."""
    if _atencion_is_staff_or_admin(user):
        return queryset
    role = get_normalized_role(user)
    if role == 'enfermeria':
        return queryset
    medico = _atencion_user_medico(user)
    if medico is not None:
        return queryset.filter(medico_principal=medico)
    paciente = _atencion_user_paciente(user)
    if paciente is not None:
        return queryset.filter(paciente=paciente)
    return queryset.none()


class AtencionPermission(permissions.BasePermission):
    """
    Permisos para atenciones clínicas (QA-ROLE-01).

    - admin/staff/superuser: operación completa (destroy bloqueado en view).
    - médico: lectura/escritura solo en atenciones donde es médico principal.
    - enfermería: solo lectura global (coordinación asistencial; sin mutación clínica).
    - paciente: solo lectura de propias atenciones.
    - secretaría, laboratorio, sin rol, anónimo: denegado.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if _atencion_is_staff_or_admin(user):
            return True

        role = get_normalized_role(user)
        if not role or role in ('secretaria', *ROLES_LIMS_OPERADOR):
            return False

        action = getattr(view, 'action', None)
        if action == 'destroy':
            return False

        if role == 'enfermeria':
            return action in _ATENCION_READ_ACTIONS
        if role == 'paciente':
            return action in _ATENCION_READ_ACTIONS
        if role == 'medico':
            return action in (
                _ATENCION_READ_ACTIONS
                | _ATENCION_WRITE_ACTIONS
                | _ATENCION_CLINICAL_ACTIONS
            )
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if _atencion_is_staff_or_admin(user):
            return True

        atencion = _atencion_for_permission_obj(obj)
        role = get_normalized_role(user)
        action = getattr(view, 'action', None)
        if action == 'destroy':
            return False

        if role == 'enfermeria':
            return action in _ATENCION_READ_ACTIONS

        if role == 'paciente':
            if action not in _ATENCION_READ_ACTIONS:
                return False
            paciente = _atencion_user_paciente(user)
            return paciente is not None and atencion.paciente_id == paciente.id

        if role == 'medico':
            medico = _atencion_user_medico(user)
            if medico is None or atencion.medico_principal_id != medico.id:
                return False
            return action in (
                _ATENCION_READ_ACTIONS
                | _ATENCION_WRITE_ACTIONS
                | _ATENCION_CLINICAL_ACTIONS
            )

        return False

class IsPacienteOrStaff(permissions.BasePermission):
    """
    Permiso para pacientes (solo ven sus propios datos) y staff
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff operativo EMR (excluye operadores LIMS con is_staff=True)
        if emr_staff_or_admin_global(request.user):
            return True
        
        # Verificar si el usuario está en el grupo Pacientes o es paciente
        return (request.user.groups.filter(name='Pacientes').exists() or 
                request.user.rol == 'paciente')
    
    def has_object_permission(self, request, view, obj):
        if emr_staff_or_admin_global(request.user):
            return True
        
        # Los pacientes solo pueden ver sus propios datos
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'paciente'):
            return obj.paciente.user == request.user
        
        return False

class IsMedicoOrSecretariaOrAdmin(permissions.BasePermission):
    """
    Permiso para médicos, secretarias y administradores
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Los superusuarios siempre tienen acceso
        if request.user.is_superuser:
            return True
        
        # Verificar si el usuario tiene rol apropiado (normalizar para soportar may/min)
        user_rol = (request.user.rol or '').lower()
        return user_rol in ['medico', 'secretaria', 'admin']

class CanManageTurnos(permissions.BasePermission):
    """
    Permiso para gestionar turnos según el rol
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Los superusuarios siempre tienen acceso
        if request.user.is_superuser:
            return True
        
        # Verificar si el usuario puede gestionar turnos
        return request.user.puede_gestionar_turnos()
    
    def has_object_permission(self, request, view, obj):
        # Los superusuarios siempre tienen acceso
        if request.user.is_superuser:
            return True
        
        # Secretarias y admins pueden gestionar todos los turnos
        if request.user.rol in ['secretaria', 'admin']:
            return True
        
        # Médicos solo pueden gestionar sus propios turnos
        if request.user.rol == 'medico' and hasattr(obj, 'medico') and obj.medico:
            if obj.medico.user:
                return obj.medico.user == request.user
            return False
        
        return False


class IsEMRClinician(permissions.BasePermission):
    """
    Permite acceso de escritura a personal clínico EMR: médicos, secretaría y administración.
    No incluye el operador LIMS (rol `laboratorio`); ese acceso se define en permisos LIMS.
    """
    allowed_roles = {'medico', 'secretaria', 'admin'}

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return (request.user.rol or '').lower() in self.allowed_roles


class IsEMRClinicianOrReadOnly(permissions.BasePermission):
    """
    Permite lectura a cualquier usuario autenticado y escritura solo a personal clínico autorizado.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        clinician_permission = IsEMRClinician()
        return clinician_permission.has_permission(request, view)


class CanWriteSignosVitales(permissions.BasePermission):
    """Escritura de signos vitales: médico, enfermería y admin."""

    allowed_roles = frozenset({'medico', 'enfermeria', 'admin'})

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        return get_normalized_role(request.user) in self.allowed_roles


class CanWriteArchivoMedico(permissions.BasePermission):
    """
    Alta/actualización de ArchivoMedico: admin y médico (vínculo validado en view).
    Paciente, secretaría, enfermería y laboratorio: solo lectura/descarga (C6.2).
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        return role in {'admin', 'medico'}


class CanWriteDocumentoClinico(permissions.BasePermission):
    """
    Alta/actualización de Documento por atención: solo admin y médico (C6.2).
    No incluye secretaría aunque sea IsEMRClinician en otros módulos.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return get_normalized_role(request.user) in {'admin', 'medico'}


class LimsB0CatalogPermission(permissions.BasePermission):
    """
    Catálogos B0 (área, sección, tipo contenedor).
    Lectura: admin, laboratorio, médico (+ superuser).
    Escritura (POST/PATCH): solo admin/superuser (catálogos maestros).
    """

    _roles_read = ROLES_LIMS_CATALOG_READ

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role in self._roles_read
        return role == "admin"


class LimsCodigoPermission(permissions.BasePermission):
    """
    Resolución / recepción unificada por código (tubo o micro).
    Lectura (por_codigo): operadores LIMS + médico.
    Escritura (recibir_por_codigo): solo operadores LIMS.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        action = getattr(view, "action", None)
        if action == "por_codigo":
            return role in (*ROLES_LIMS_WRITE, "medico")
        if action == "recibir_por_codigo":
            return role in ROLES_LIMS_WRITE
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if role in ROLES_LIMS_OPERADOR or role == "admin":
            return True
        if role == "medico":
            action = getattr(view, "action", None)
            if action != "por_codigo":
                return False
            # Tubo: via solicitud; micro: via medico_interno / solicitud.
            solicitud = getattr(obj, "solicitud", None)
            if solicitud is not None:
                return usuario_puede_ver_solicitud_lims(request.user, solicitud)
            medico_interno_id = getattr(obj, "medico_interno_id", None)
            if medico_interno_id:
                try:
                    if (
                        hasattr(request.user, "medico")
                        and request.user.medico
                        and request.user.medico.pk == medico_interno_id
                    ):
                        return True
                except Exception:
                    pass
            return False
        return False


class LimsMuestraTransaccionalPermission(permissions.BasePermission):
    """
    Muestra transaccional (Fase B1).
    - admin/superuser: CRUD restringido (sin destroy en práctica), todas las acciones.
    - laboratorio: listar/ver, crear, PATCH administrativo, tomar/recibir/rechazar/conservar/descartar/cancelar.
    - médico: solo lectura de muestras de órdenes propias o de pacientes vinculados.
    Sin acceso: anónimo, paciente, secretaría (no lectura técnica de muestras en esta fase).
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        action = getattr(view, "action", None)
        if role not in (*ROLES_LIMS_WRITE, "medico"):
            return False
        if action in ("list", "retrieve"):
            return True
        if action == "create":
            return role in ROLES_LIMS_WRITE
        if action in ("update", "partial_update"):
            return role in ROLES_LIMS_WRITE
        if action == "destroy":
            return False
        if action in (
            "tomar",
            "recibir",
            "rechazar",
            "conservar",
            "descartar",
            "cancelar",
            "cambiar_ubicacion",
            "recibir_por_codigo",
            "tomar_por_codigo",
        ):
            return role in ROLES_LIMS_WRITE
        if action in ("etiqueta", "por_codigo"):
            return role in (*ROLES_LIMS_WRITE, "medico")
        if action == "eventos":
            return role in (*ROLES_LIMS_WRITE, "medico")
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        action = getattr(view, "action", None)
        solicitud = getattr(obj, "solicitud", None)
        if role == "medico":
            if action not in ("retrieve", "list", "eventos"):
                return False
            if solicitud is None:
                return False
            return usuario_puede_ver_solicitud_lims(request.user, solicitud)
        if role in ROLES_LIMS_OPERADOR:
            return True
        if role == "admin":
            return True
        return False


class LimsMicrobiologiaCatalogPermission(permissions.BasePermission):
    """
    Catálogo de microbiología (medios de cultivo) — LIMS Fase B3.1.
    Lectura: admin, laboratorio, bioquímico, médico (+ superuser).
    Escritura (POST/PATCH): solo admin/superuser. Sin destroy (se desactiva).
    """

    _roles_read = ROLES_LIMS_CATALOG_READ

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role in self._roles_read
        return role == "admin"


class LimsMicrobiologiaPermission(permissions.BasePermission):
    """
    Estudios microbiológicos, siembras y lecturas — LIMS Fase B3.1.

    - admin / superuser: acceso total a list/retrieve/create/update y acciones.
    - laboratorio / bioquímico: list/retrieve/create/update y acciones técnicas.
    - médico: list/retrieve; además puede **solicitar** estudios (create/batch)
      desde consulta/mostrador (pedido clínico). No opera el flujo técnico
      (iniciar, siembras, etiquetas, etc.).
    - secretaría / enfermería: lectura de pedidos (todos los estados) y
      envío/PDF solo con informe FINAL VALIDADO. Sin operación técnica.
    - paciente / anónimo: sin acceso.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if role not in (*ROLES_LIMS_WRITE, "medico", *ROLES_LIMS_OPERATIVA_LIMITADA):
            return False
        action = getattr(view, "action", None)
        if action in ("list", "retrieve", "por_codigo"):
            return True
        # Pedido clínico: médico solo puede crear estudios (no siembras/lecturas/etc.).
        if action in ("create", "batch"):
            if role in ROLES_LIMS_WRITE:
                return True
            if role == "medico":
                view_name = type(view).__name__
                return view_name == "EstudioMicrobiologiaViewSet"
            return False
        if action in ("update", "partial_update"):
            return role in ROLES_LIMS_WRITE
        if action in (
            "iniciar",
            "cancelar",
            "descartar",
            "completar",
            "marcar_informado",
            "imprimir_etiquetas",
            "imprimir_etiquetas_batch",
            "recibir_por_codigo",
        ):
            return role in ROLES_LIMS_WRITE
        if action == "enviar_informe":
            return role in (*ROLES_LIMS_WRITE, "secretaria")
        if action == "informe_pdf":
            # Operadores + médico + secretaría/enfermería; object permission exige VALIDADO.
            return role in (*ROLES_LIMS_WRITE, "medico", *ROLES_LIMS_OPERATIVA_LIMITADA)
        if action == "informe_entrega":
            # Público con token; el método no exige auth.
            return True
        if action == "destroy":
            return False
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        action = getattr(view, "action", None)

        if action == "informe_pdf":
            estudio = obj if hasattr(obj, "medico_interno_id") else getattr(obj, "estudio", None)
            if estudio is None:
                return False
            # Bio/admin: pueden intentar (la vista responde 400 si aún no hay FINAL emitido).
            if role in ROLES_LIMS_VALIDAR:
                return True
            return usuario_puede_descargar_informe_micro(request.user, estudio)

        if action == "enviar_informe":
            # Envío al paciente/médico: operadores LIMS y secretaría, solo FINAL VALIDADO.
            estudio = obj if hasattr(obj, "medico_interno_id") else getattr(obj, "estudio", None)
            if estudio is None or role not in (*ROLES_LIMS_WRITE, "secretaria"):
                return False
            from laboratorio.models_microbiologia import InformeMicrobiologia

            return InformeMicrobiologia.objects.filter(
                estudio_id=estudio.pk,
                tipo="FINAL",
                estado="VALIDADO",
            ).exists()

        if role == "admin":
            return True
        if role in ROLES_LIMS_OPERADOR:
            return True
        if role in ROLES_LIMS_OPERATIVA_LIMITADA:
            if action not in ("retrieve", "list", "por_codigo", "informe_pdf", "enviar_informe"):
                return False
            return True
        if role == "medico":
            if action not in ("retrieve", "list", "por_codigo", "informe_pdf"):
                return False

            # Pedido directo (sin solicitud LIMS): el médico solicitante puede verlo.
            estudio = obj if hasattr(obj, "medico_interno_id") else None
            if estudio is None:
                estudio = getattr(obj, "estudio", None)
                if estudio is None:
                    aislado = getattr(obj, "aislado", None)
                    if aislado is None:
                        antibiograma = getattr(obj, "antibiograma", None)
                        aislado = (
                            getattr(antibiograma, "aislado", None) if antibiograma else None
                        )
                    estudio = getattr(aislado, "estudio", None) if aislado else None
            if estudio is not None:
                medico_interno_id = getattr(estudio, "medico_interno_id", None)
                if medico_interno_id:
                    try:
                        if (
                            hasattr(request.user, "medico")
                            and request.user.medico
                            and request.user.medico.pk == medico_interno_id
                        ):
                            return True
                    except Exception:
                        pass

            # Resolver solicitud caminando: estudio → aislado → antibiograma → resultado.
            solicitud = getattr(obj, "solicitud", None)
            if solicitud is None:
                if estudio is None:
                    estudio = getattr(obj, "estudio", None)
                    if estudio is None:
                        aislado = getattr(obj, "aislado", None)
                        if aislado is None:
                            antibiograma = getattr(obj, "antibiograma", None)
                            aislado = (
                                getattr(antibiograma, "aislado", None)
                                if antibiograma
                                else None
                            )
                        estudio = getattr(aislado, "estudio", None) if aislado else None
                solicitud = getattr(estudio, "solicitud", None) if estudio else None
            if solicitud is None:
                return False
            return usuario_puede_ver_solicitud_lims(request.user, solicitud)
        return False


class LimsMicrobiologiaInformePermission(permissions.BasePermission):
    """
    Informes de microbiología (B3.4).

    - bioquímico / admin: crear, completar (emitir), anular y validar; ven todo.
    - laboratorio / médico / secretaría / enfermería: solo list/retrieve de
      informes **VALIDADO**; no ven borradores ni emitidos pendientes.
    - paciente / anónimo: sin acceso.
    """

    _read_roles = frozenset({*ROLES_LIMS_WRITE, "medico", *ROLES_LIMS_OPERATIVA_LIMITADA})

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        action = getattr(view, "action", None)
        if action in (
            "create",
            "partial_update",
            "update",
            "emitir",
            "anular",
            "validar",
        ):
            return role in ROLES_LIMS_VALIDAR
        if action in ("list", "retrieve"):
            return role in self._read_roles
        if action == "destroy":
            return False
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        action = getattr(view, "action", None)
        if action in (
            "partial_update",
            "update",
            "emitir",
            "anular",
            "validar",
        ):
            return role in ROLES_LIMS_VALIDAR
        if action in ("retrieve", "list"):
            return usuario_puede_ver_contenido_informe_micro(request.user, obj)
        return False


class LimsInventarioPermission(permissions.BasePermission):
    """
    Inventario de laboratorio — insumos, lotes y movimientos.
    Lectura/escritura: admin, laboratorio, bioquímico (+ superuser).
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        return role in ROLES_LIMS_WRITE


class LimsQcPermission(permissions.BasePermission):
    """
    Control de calidad Westgard.
    Lectura/escritura: admin, laboratorio, bioquímico (+ superuser).
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        return role in ROLES_LIMS_WRITE


class CanUpdatePacienteDemographics(permissions.BasePermission):
    """
    Permiso para actualizar datos demográficos de pacientes.
    - Admin/Secretaria: pueden actualizar cualquier paciente
    - Médicos: pueden actualizar datos demográficos de CUALQUIER paciente
    - Pacientes: solo lectura (no pueden modificar su ficha)
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        # Admin, secretaría o staff EMR autorizado
        if (
            emr_staff_or_admin_global(request.user)
            or request.user.rol in ['admin', 'secretaria']
        ):
            return True
        
        # Médicos pueden leer y actualizar datos demográficos de CUALQUIER paciente
        if request.user.rol == 'medico':
            if request.method in ('GET', 'PATCH', 'PUT', 'HEAD', 'OPTIONS'):
                return True
        
        # Pacientes: solo lectura de su ficha demográfica
        if request.user.rol == 'paciente':
            return False
        
        # Para otras operaciones, usar la lógica por defecto
        return False
