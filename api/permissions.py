from rest_framework import permissions

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
        
        # Verificar si el usuario tiene rol apropiado
        return request.user.rol in ['medico', 'secretaria', 'admin']

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
        if request.user.rol == 'medico' and hasattr(obj, 'medico'):
            return obj.medico.user == request.user
        
        return False
