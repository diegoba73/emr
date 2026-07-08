import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import Sector, Cama, Internacion
from .serializers import SectorSerializer, CamaSerializer, InternacionSerializer
from api.permissions import IsMedicoOrAdmin, IsMedicoOrEnfermeriaOrAdmin

logger = logging.getLogger(__name__)


class SectorViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar sectores (CRUD completo)"""
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    permission_classes = [IsAuthenticated, IsMedicoOrEnfermeriaOrAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre']
    ordering_fields = ['nombre']
    ordering = ['nombre']
    
    def perform_create(self, serializer):
        """Log de creación de sector"""
        sector = serializer.save()
        logger.info(
            f"Sector '{sector.nombre}' creado por usuario {self.request.user.username} "
            f"(Rol: {self.request.user.rol})"
        )
    
    def perform_destroy(self, instance):
        """Log de eliminación de sector"""
        nombre_sector = instance.nombre
        logger.info(
            f"Sector '{nombre_sector}' eliminado por usuario {self.request.user.username} "
            f"(Rol: {self.request.user.rol})"
        )
        instance.delete()


class CamaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar camas (CRUD completo)"""
    queryset = Cama.objects.select_related('sector').prefetch_related('internaciones').all()
    serializer_class = CamaSerializer
    permission_classes = [IsAuthenticated, IsMedicoOrEnfermeriaOrAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'sector__nombre']
    ordering_fields = ['nombre', 'sector__nombre']
    ordering = ['sector', 'nombre']
    
    def perform_create(self, serializer):
        """Log de creación de cama"""
        cama = serializer.save()
        logger.info(
            f"Cama '{cama.nombre}' creada por usuario {self.request.user.username} "
            f"(Rol: {self.request.user.rol})"
        )
    
    def perform_destroy(self, instance):
        """
        Validación de eliminación: No se puede eliminar una cama que no esté DISPONIBLE
        """
        if instance.estado != 'DISPONIBLE':
            logger.warning(
                f"Intento de eliminar cama '{instance.nombre}' con estado '{instance.estado}' "
                f"por usuario {self.request.user.username} (Rol: {self.request.user.rol})"
            )
            raise ValidationError({
                'estado': 'No se puede eliminar una cama activa/ocupada. '
                          'Debe estar en estado DISPONIBLE para poder eliminarla.'
            })
        
        # Verificar si tiene internaciones asociadas (aunque esté DISPONIBLE)
        if instance.internaciones.exists():
            logger.warning(
                f"Intento de eliminar cama '{instance.nombre}' con internaciones históricas "
                f"por usuario {self.request.user.username} (Rol: {self.request.user.rol})"
            )
            raise ValidationError({
                'internaciones': 'No se puede eliminar una cama que tiene internaciones asociadas. '
                                'Elimine primero las internaciones históricas.'
            })
        
        nombre_cama = instance.nombre
        logger.info(
            f"Cama '{nombre_cama}' eliminada por usuario {self.request.user.username} "
            f"(Rol: {self.request.user.rol})"
        )
        instance.delete()
    
    def get_queryset(self):
        """Permitir filtrar por nombre de sector o ID"""
        queryset = super().get_queryset()
        sector_param = self.request.query_params.get('sector', None)
        if sector_param:
            # Intentar filtrar por nombre primero
            try:
                # Si es un número, buscar por ID
                sector_id = int(sector_param)
                queryset = queryset.filter(sector_id=sector_id)
            except ValueError:
                # Si no es un número, buscar por nombre
                queryset = queryset.filter(sector__nombre=sector_param)
        return queryset
    
    def perform_update(self, serializer):
        cama = serializer.save()
        logger.info(
            f"Cama '{cama.nombre}' actualizada por usuario {self.request.user.username} "
            f"(Rol: {self.request.user.rol})"
        )

    def update(self, request, *args, **kwargs):
        """Actualizar datos de la cama con restricciones según su estado."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if instance.estado == 'OCUPADA':
            campos_permitidos = {'nombre', 'aislada'}
            campos_solicitados = set(request.data.keys())
            campos_no_permitidos = campos_solicitados - campos_permitidos
            if campos_no_permitidos:
                return Response(
                    {
                        'error': (
                            'En una cama ocupada solo se puede editar el nombre y si es aislada. '
                            'Para cambiar sector o estado, gestioná la internación del paciente.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


class InternacionViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar internaciones"""
    queryset = Internacion.objects.select_related('paciente', 'cama', 'medico', 'cama__sector').filter(activo=True)
    serializer_class = InternacionSerializer
    permission_classes = [IsAuthenticated, IsMedicoOrEnfermeriaOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'cama__sector', 'medico', 'paciente']
    search_fields = ['paciente__nombre', 'paciente__apellido', 'diagnostico_ingreso']
    ordering_fields = ['fecha_ingreso', 'fecha_alta']
    ordering = ['-fecha_ingreso']
    
    def get_queryset(self):
        """Filtrar por usuario según rol y por defecto solo activas"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Permitir ver todas las internaciones activas por defecto
        # El filtro por activo=True ya está en el queryset base
        
        if hasattr(user, 'rol') and user.rol:
            rol_upper = str(user.rol).strip().upper()
            if rol_upper == 'MEDICO':
                # Médicos pueden ver todas las internaciones activas para el panel
                queryset = queryset.filter(activo=True)
            elif rol_upper == 'ENFERMERIA':
                # Enfermería puede ver todas las internaciones activas
                queryset = queryset.filter(activo=True)
            elif rol_upper == 'ADMIN':
                # Admins ven todas las internaciones (activas e inactivas)
                queryset = Internacion.objects.select_related('paciente', 'cama', 'medico', 'cama__sector').all()
            else:
                # Otros roles no ven internaciones
                queryset = queryset.none()
        elif not user.is_superuser:
            # Si no tiene rol y no es superusuario, no ver nada
            queryset = queryset.none()
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Crear internación con logging de quién realizó el ingreso
        """
        internacion = serializer.save()
        paciente = internacion.paciente
        cama = internacion.cama
        
        logger.info(
            f"Paciente '{paciente.apellido}, {paciente.nombre}' (ID: {paciente.id}) ingresado a "
            f"cama '{cama.nombre}' (Sector: {cama.sector.nombre}) por usuario "
            f"{self.request.user.username} (Rol: {self.request.user.rol})"
        )
    
    def get_object(self):
        """
        Override para permitir actualizar internaciones incluso si no están en el queryset filtrado
        (pero solo si el usuario tiene permisos)
        """
        # Obtener el pk de la URL
        pk = self.kwargs.get('pk')
        user = self.request.user
        
        # Si es ADMIN, puede acceder a cualquier internación
        if hasattr(user, 'rol') and user.rol:
            rol_upper = str(user.rol).strip().upper()
            if rol_upper == 'ADMIN':
                try:
                    return Internacion.objects.get(pk=pk)
                except Internacion.DoesNotExist:
                    from rest_framework.exceptions import NotFound
                    raise NotFound('No Internacion matches the given query.')
        
        # Si es MEDICO o ENFERMERIA, puede acceder a todas las internaciones activas para ver/editar
        # (Esto permite que los médicos y enfermería gestionen internaciones desde el panel)
        if hasattr(user, 'rol') and user.rol:
            rol_upper = str(user.rol).strip().upper()
            if rol_upper in ['MEDICO', 'ENFERMERIA']:
                try:
                    internacion = Internacion.objects.get(pk=pk)
                    # Permitir acceso a internaciones activas
                    if internacion.activo:
                        return internacion
                    else:
                        from rest_framework.exceptions import PermissionDenied
                        raise PermissionDenied('No puede acceder a internaciones inactivas.')
                except Internacion.DoesNotExist:
                    from rest_framework.exceptions import NotFound
                    raise NotFound('No Internacion matches the given query.')
        
        # Intentar con el queryset filtrado por defecto
        try:
            return super().get_object()
        except Exception:
            from rest_framework.exceptions import NotFound
            raise NotFound('No Internacion matches the given query.')
    
    @action(detail=False, methods=['post'], url_path='ingresar')
    def ingresar(self, request):
        """
        Acción personalizada para ingresar un paciente.
        POST /api/internaciones/ingresar/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validar que la cama esté disponible
        cama_id = serializer.validated_data.get('cama').id
        cama = Cama.objects.get(id=cama_id)
        
        if cama.estado != 'DISPONIBLE':
            return Response(
                {'error': f'La cama {cama.nombre} no está disponible. Estado actual: {cama.estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear la internación (el save() del modelo actualizará el estado de la cama)
        internacion = serializer.save()
        
        return Response(
            InternacionSerializer(internacion).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='alta')
    def alta(self, request, pk=None):
        """
        Acción personalizada para dar de alta a un paciente.
        POST /api/internaciones/{id}/alta/
        """
        internacion = self.get_object()
        
        if not internacion.activo:
            return Response(
                {'error': 'Esta internación ya fue dada de alta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener fecha de alta del request o usar ahora
        from django.utils import timezone
        fecha_alta = request.data.get('fecha_alta')
        if not fecha_alta:
            fecha_alta = timezone.now()
        
        # Actualizar internación (el save() del modelo actualizará el estado de la cama)
        internacion.fecha_alta = fecha_alta
        internacion.save()
        
        serializer = self.get_serializer(internacion)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='mover-cama')
    def mover_cama(self, request, pk=None):
        """
        Acción personalizada para mover un paciente a otra cama.
        POST /api/internaciones/{id}/mover-cama/
        Body: {"cama_id": <id_cama_destino>}
        """
        internacion = self.get_object()
        
        if not internacion.activo:
            return Response(
                {'error': 'No se puede mover una internación inactiva'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cama_destino_id = request.data.get('cama_id')
        if not cama_destino_id:
            return Response(
                {'error': 'Debe proporcionar el ID de la cama destino'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cama_destino = Cama.objects.get(id=cama_destino_id)
        except Cama.DoesNotExist:
            return Response(
                {'error': 'La cama destino no existe'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Si la cama destino está ocupada, intercambiar pacientes
        if cama_destino.estado == 'OCUPADA':
            # Buscar la internación en la cama destino
            internacion_destino = Internacion.objects.filter(
                cama=cama_destino,
                activo=True
            ).first()
            
            if not internacion_destino:
                return Response(
                    {'error': 'La cama destino está marcada como ocupada pero no tiene internación activa'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Intercambiar camas
            cama_origen = internacion.cama
            
            # IMPORTANTE: Usar update para evitar que save() modifique estados incorrectamente
            # Primero actualizar las camas sin trigger de save()
            from django.db import transaction
            
            with transaction.atomic():
                # Actualizar internaciones directamente en la BD
                Internacion.objects.filter(pk=internacion.pk).update(cama=cama_destino)
                Internacion.objects.filter(pk=internacion_destino.pk).update(cama=cama_origen)
                
                # Actualizar estados de camas manualmente
                cama_origen.estado = 'OCUPADA'
                cama_origen.save()
                cama_destino.estado = 'OCUPADA'
                cama_destino.save()
                
                # Refrescar objetos desde la BD
                internacion.refresh_from_db()
                internacion_destino.refresh_from_db()
            
            serializer = self.get_serializer(internacion)
            serializer_destino = self.get_serializer(internacion_destino)
            
            return Response({
                'internacion_origen': serializer.data,
                'internacion_destino': serializer_destino.data,
                'mensaje': 'Pacientes intercambiados exitosamente'
            })
        
        # Si la cama destino está disponible, solo mover
        elif cama_destino.estado == 'DISPONIBLE':
            # Mover paciente a cama destino
            internacion.cama = cama_destino
            internacion.save()
            
            serializer = self.get_serializer(internacion)
            return Response({
                'internacion': serializer.data,
                'mensaje': 'Paciente movido exitosamente'
            })
        else:
            return Response(
                {'error': f'La cama destino no está disponible. Estado: {cama_destino.estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )
