from rest_framework import permissions


def get_normalized_role(user):
    """Normaliza `User.rol` a minúsculas; cadena vacía si no hay usuario autenticado."""
    if not user or not getattr(user, 'is_authenticated', False):
        return ''
    return str(getattr(user, 'rol', '') or '').lower()


class LimsCatalogReadPermission(permissions.BasePermission):
    """
    Lectura de catálogos LIMS (tipos de muestra, exámenes, paneles).
    Roles: admin, laboratorio, médico, secretaría, enfermería (+ superuser).
    Sin acceso: anónimo y paciente. Los ViewSets son ReadOnly; métodos no seguros se niegan.
    """
    _roles_read = frozenset({'admin', 'laboratorio', 'medico', 'secretaria', 'enfermeria'})

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role in self._roles_read
        return False


class LimsSolicitudExamenPermission(permissions.BasePermission):
    """
    Permisos provisionales para SolicitudExamenViewSet y acciones custom LIMS.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        role = get_normalized_role(request.user)
        action = getattr(view, 'action', None)

        if action == 'list':
            return role in ('admin', 'laboratorio', 'medico')
        if action == 'create':
            return role in ('admin', 'laboratorio', 'medico')
        if action in ('retrieve', 'update', 'partial_update', 'destroy'):
            if action in ('retrieve',) and role in ('admin', 'laboratorio', 'medico'):
                return True
            if action in ('update', 'partial_update') and role in ('admin', 'laboratorio'):
                return True
            if action == 'destroy' and role == 'admin':
                return True
            return False
        if action == 'cargar_resultados':
            return role in ('admin', 'laboratorio')
        if action in ('tomar_muestra', 'cancelar', 'marcar_entregado'):
            return role in ('admin', 'laboratorio')
        if action == 'validar':
            return role == 'admin'
        if action == 'etiqueta':
            return role in ('admin', 'laboratorio')
        if action == 'informe_pdf':
            return role in ('admin', 'laboratorio', 'medico')
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        role = get_normalized_role(request.user)
        action = getattr(view, 'action', None)

        if action == 'retrieve':
            if role in ('admin', 'laboratorio'):
                return True
            if role == 'medico':
                mi = getattr(obj, 'medico_interno', None)
                return bool(mi and getattr(mi, 'user_id', None) == request.user.id)
            return False

        if action in ('update', 'partial_update'):
            return role in ('admin', 'laboratorio')

        if action == 'destroy':
            return role == 'admin'

        if action == 'cargar_resultados':
            return role in ('admin', 'laboratorio')

        if action in ('tomar_muestra', 'cancelar', 'marcar_entregado'):
            return role in ('admin', 'laboratorio')

        if action == 'validar':
            return role == 'admin'

        if action == 'etiqueta':
            return role in ('admin', 'laboratorio')

        if action == 'informe_pdf':
            if role in ('admin', 'laboratorio'):
                return True
            if role == 'medico':
                mi = getattr(obj, 'medico_interno', None)
                return bool(mi and getattr(mi, 'user_id', None) == request.user.id)
            return False

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


def _atencion_is_staff_or_admin(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.is_superuser
        or user.is_staff
        or get_normalized_role(user) == 'admin'
    )


def _atencion_user_medico(user):
    try:
        return user.medico
    except Exception:
        return None


def _atencion_user_paciente(user):
    try:
        return user.paciente
    except Exception:
        return None


_ATENCION_READ_ACTIONS = frozenset({'list', 'retrieve'})
_ATENCION_WRITE_ACTIONS = frozenset({'create', 'update', 'partial_update'})
_ATENCION_CLINICAL_ACTIONS = frozenset({
    'cerrar',
    'registrar_consulta',
    'crear_registro_ambulatorio',
    'cerrar_atencion',
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
        if not role or role in ('secretaria', 'laboratorio'):
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
            return paciente is not None and obj.paciente_id == paciente.id

        if role == 'medico':
            medico = _atencion_user_medico(user)
            if medico is None or obj.medico_principal_id != medico.id:
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
        
        # Los staff siempre tienen acceso
        if request.user.is_staff:
            return True
        
        # Verificar si el usuario está en el grupo Pacientes o es paciente
        return (request.user.groups.filter(name='Pacientes').exists() or 
                request.user.rol == 'paciente')
    
    def has_object_permission(self, request, view, obj):
        # Los staff pueden ver todos los objetos
        if request.user.is_staff:
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


class CanWriteArchivoMedico(permissions.BasePermission):
    """
    Alta/actualización de ArchivoMedico: admin, médico (vínculo validado en view) o paciente (propio).
    Secretaría, enfermería y laboratorio no pueden subir archivos clínicos (C6.2).
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        return role in {'admin', 'medico', 'paciente'}


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
    Lectura: admin, laboratorio, médico, secretaría, enfermería (+ superuser).
    Escritura (POST/PATCH): solo admin/superuser (catálogos maestros).
    """

    _roles_read = frozenset({"admin", "laboratorio", "medico", "secretaria", "enfermeria"})

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if request.method in permissions.SAFE_METHODS:
            return role in self._roles_read
        return role == "admin"


class LimsMuestraTransaccionalPermission(permissions.BasePermission):
    """
    Muestra transaccional (Fase B1).
    - admin/superuser: CRUD restringido (sin destroy en práctica), todas las acciones.
    - laboratorio: listar/ver, crear, PATCH administrativo, tomar/recibir/rechazar/conservar/descartar/cancelar.
    - médico: solo lectura de muestras vinculadas a solicitudes propias (medico_interno.user).
    Sin acceso: anónimo, paciente, secretaría (no lectura técnica de muestras en esta fase).
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        action = getattr(view, "action", None)
        if role not in ("admin", "laboratorio", "medico"):
            return False
        if action in ("list", "retrieve"):
            return True
        if action == "create":
            return role in ("admin", "laboratorio")
        if action in ("update", "partial_update"):
            return role in ("admin", "laboratorio")
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
        ):
            return role in ("admin", "laboratorio")
        if action == "eventos":
            return role in ("admin", "laboratorio", "medico")
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
            mi = getattr(solicitud, "medico_interno", None) if solicitud is not None else None
            return bool(mi and getattr(mi, "user_id", None) == request.user.id)
        if role == "laboratorio":
            return True
        if role == "admin":
            return True
        return False


class LimsMicrobiologiaCatalogPermission(permissions.BasePermission):
    """
    Catálogo de microbiología (medios de cultivo) — LIMS Fase B3.1.
    Lectura: admin, laboratorio, médico, secretaría, enfermería (+ superuser).
    Escritura (POST/PATCH): solo admin/superuser. Sin destroy (se desactiva).
    """

    _roles_read = frozenset({"admin", "laboratorio", "medico", "secretaria", "enfermeria"})

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
    - laboratorio: list/retrieve/create/update y acciones ``iniciar`` / ``cancelar``.
    - médico: list/retrieve sólo de estudios cuya solicitud tiene
      ``medico_interno.user`` = usuario actual (el queryset filtra; este permiso
      bloquea operaciones de escritura).
    - secretaría / enfermería / paciente / anónimo: sin acceso a operación
      técnica de microbiología en esta fase.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if role not in ("admin", "laboratorio", "medico"):
            return False
        action = getattr(view, "action", None)
        if action in ("list", "retrieve"):
            return True
        if action == "create":
            return role in ("admin", "laboratorio")
        if action in ("update", "partial_update"):
            return role in ("admin", "laboratorio")
        if action in ("iniciar", "cancelar", "descartar", "completar", "marcar_informado"):
            return role in ("admin", "laboratorio")
        if action == "destroy":
            return False
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        if role == "admin":
            return True
        if role == "laboratorio":
            return True
        if role == "medico":
            action = getattr(view, "action", None)
            if action not in ("retrieve", "list"):
                return False
            # Resolver solicitud caminando: estudio → aislado → antibiograma → resultado.
            solicitud = getattr(obj, "solicitud", None)
            if solicitud is None:
                estudio = getattr(obj, "estudio", None)
                if estudio is None:
                    aislado = getattr(obj, "aislado", None)
                    if aislado is None:
                        antibiograma = getattr(obj, "antibiograma", None)
                        aislado = getattr(antibiograma, "aislado", None) if antibiograma else None
                    estudio = getattr(aislado, "estudio", None) if aislado else None
                solicitud = getattr(estudio, "solicitud", None) if estudio else None
            mi = getattr(solicitud, "medico_interno", None) if solicitud is not None else None
            return bool(mi and getattr(mi, "user_id", None) == request.user.id)
        return False


class LimsMicrobiologiaInformePermission(permissions.BasePermission):
    """
    Informes de microbiología (B3.4).

    - admin / superuser: acceso total (incluye ``validar``).
    - laboratorio: crear/editar borradores, emitir, anular (no ``validar``).
    - médico: solo list/retrieve de informes de estudios de sus solicitudes.
    - secretaría / enfermería / paciente / anónimo: sin acceso.
    """

    _read_roles = frozenset({"admin", "laboratorio", "medico"})
    _write_roles = frozenset({"admin", "laboratorio"})

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = get_normalized_role(request.user)
        action = getattr(view, "action", None)
        if action == "validar":
            return role == "admin"
        if action in ("list", "retrieve"):
            return role in self._read_roles
        if action in ("create", "partial_update", "update", "emitir", "anular"):
            return role in self._write_roles
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
        if action == "validar":
            return role == "admin"
        if role in ("admin", "laboratorio"):
            return True
        if role == "medico":
            if action not in ("retrieve", "list"):
                return False
            estudio = getattr(obj, "estudio", None)
            solicitud = getattr(estudio, "solicitud", None) if estudio else None
            mi = getattr(solicitud, "medico_interno", None) if solicitud is not None else None
            return bool(mi and getattr(mi, "user_id", None) == request.user.id)
        return False


class CanUpdatePacienteDemographics(permissions.BasePermission):
    """
    Permiso para actualizar datos demográficos de pacientes.
    - Admin/Secretaria: pueden actualizar cualquier paciente
    - Médicos: pueden actualizar datos demográficos de CUALQUIER paciente
    - Pacientes: solo pueden actualizar su propio perfil
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        # Admin o Secretaria pueden editar siempre
        if request.user.is_staff or request.user.rol in ['admin', 'secretaria'] or request.user.is_superuser:
            return True
        
        # Médicos pueden leer y actualizar datos demográficos de CUALQUIER paciente
        if request.user.rol == 'medico':
            if request.method in ('GET', 'PATCH', 'PUT', 'HEAD', 'OPTIONS'):
                return True
        
        # Pacientes solo pueden actualizar su propio perfil
        if request.user.rol == 'paciente':
            if hasattr(obj, 'user'):
                return obj.user == request.user
        
        # Para otras operaciones, usar la lógica por defecto
        return False
