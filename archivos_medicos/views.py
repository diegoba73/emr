from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse
from django.utils import timezone
import os
import logging
from datetime import timedelta

from .models import ArchivoMedico
from .serializers import ArchivoMedicoSerializer, ArchivoMedicoListSerializer

logger = logging.getLogger(__name__)


class ArchivoMedicoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para archivos médicos con autenticación JWT y permisos basados en roles.

    Nota sobre destroy: el borrado por defecto elimina el registro en BD; los bytes en
    MEDIA pueden quedar huérfanos salvo política explícita de limpieza (no se borra
    disco aquí por decisión de trazabilidad/seguridad).
    """
    queryset = ArchivoMedico.objects.select_related('paciente', 'consulta', 'subido_por').all()
    serializer_class = ArchivoMedicoSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['paciente', 'tipo_archivo', 'es_urgente', 'fecha_estudio']
    search_fields = ['titulo', 'descripcion', 'paciente__nombre', 'paciente__apellido']
    ordering_fields = ['fecha_subida', 'fecha_estudio', 'titulo']
    ordering = ['-fecha_subida']
    
    def get_queryset(self):
        """
        Filtra archivos médicos basándose en el rol del usuario.
        Permite filtrar por paciente_id desde query params para vista de pacientes.
        """
        queryset = super().get_queryset()
        
        # Permitir filtrar por paciente_id desde query params (para compatibilidad con ?paciente_id=)
        paciente_id = self.request.query_params.get('paciente_id')
        if paciente_id:
            try:
                paciente_id = int(paciente_id)
                queryset = queryset.filter(paciente_id=paciente_id)
            except (ValueError, TypeError):
                pass  # Ignorar si no es un ID válido
        
        user = self.request.user
        
        # Admin ve todos los archivos
        if user.rol == 'admin' or user.is_superuser:
            return queryset

        # Secretaria no tiene acceso a archivos médicos
        if user.rol == 'secretaria':
            return queryset.none()

        # Médico ve archivos de pacientes que ha atendido
        if user.rol == 'medico':
            try:
                from medicos.models import Medico
                from historias_clinicas.models import Consulta
                medico = Medico.objects.get(user=user)
                # Obtener IDs de pacientes que han tenido consultas con este médico
                pacientes_con_consultas = Consulta.objects.filter(
                    medico=medico
                ).values_list('historia_clinica__paciente_id', flat=True).distinct()
                return queryset.filter(paciente_id__in=pacientes_con_consultas)
            except:
                # Si no existe el médico, no mostrar archivos
                return queryset.none()

        # Paciente ve solo sus propios archivos
        if user.rol == 'paciente':
            try:
                from pacientes.models import Paciente
                paciente = Paciente.objects.get(user=user)
                return queryset.filter(paciente=paciente)
            except:
                # Si no existe el paciente, no mostrar archivos
                return queryset.none()

        # Por defecto, no mostrar archivos
        return queryset.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return ArchivoMedicoListSerializer
        return ArchivoMedicoSerializer

    def perform_create(self, serializer):
        """Asigna el usuario que sube el archivo"""
        serializer.save(subido_por=self.request.user)
        logger.info(f"Archivo subido por {self.request.user.username}")

    def _tiene_permiso_lectura(self, user, archivo):
        """
        Verificar si el usuario tiene permiso para ver/descargar el archivo
        """
        # Admin tiene acceso total
        if user.rol == 'admin' or user.is_superuser:
            return True
        
        # Secretaria no tiene acceso a archivos médicos
        if user.rol == 'secretaria':
            return False
            
        # Médico puede ver archivos de pacientes que ha atendido
        if user.rol == 'medico':
            try:
                from medicos.models import Medico
                from historias_clinicas.models import Consulta
                medico = Medico.objects.get(user=user)
                # Verificar si el paciente ha tenido consultas con este médico
                tiene_consultas = Consulta.objects.filter(
                    medico=medico,
                    historia_clinica__paciente=archivo.paciente
                ).exists()
                return tiene_consultas
            except:
                return False
            
        # Paciente solo puede ver sus propios archivos
        if user.rol == 'paciente':
            try:
                from pacientes.models import Paciente
                paciente = Paciente.objects.get(user=user)
                return archivo.paciente == paciente
            except:
                return False
            
        return False

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Descargar archivo médico con verificación de permisos
        """
        archivo = self.get_object()
        
        # Verificar permisos de descarga
        if not self._tiene_permiso_lectura(request.user, archivo):
            return Response(
                {'error': 'No tiene permiso para descargar este archivo'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if not os.path.exists(archivo.archivo.path):
            logger.error("Archivo no encontrado en almacenamiento (id=%s)", archivo.id)
            return Response(
                {'error': 'Archivo no encontrado en el servidor'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            response = FileResponse(
                open(archivo.archivo.path, 'rb'),
                content_type='application/octet-stream'
            )
            # Nombre de descarga: preferir basename del fichero almacenado (incluye extensión); evitar título sin sanitizar
            nombre_descarga = os.path.basename(archivo.archivo.name) or 'archivo'
            nombre_descarga = nombre_descarga.replace('"', '_')
            response['Content-Disposition'] = f'attachment; filename="{nombre_descarga}"'
            return response
        except Exception as e:
            logger.error(f"Error al descargar archivo: {e}")
            return Response(
                {'error': 'Error al procesar el archivo'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def tipos_disponibles(self, request):
        """
        Obtener tipos de archivo disponibles
        """
        tipos = ArchivoMedico.TIPO_CHOICES
        return Response([{'value': choice[0], 'label': choice[1]} for choice in tipos])

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Estadísticas de archivos médicos (solo para admin/secretaria)
        """
        if request.user.rol not in ['admin', 'secretaria'] and not request.user.is_superuser:
            return Response(
                {'error': 'No tiene permisos para ver estadísticas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        stats = {
            'total_archivos': queryset.count(),
            'por_tipo': {},
            'urgentes': queryset.filter(es_urgente=True).count(),
            'recientes': queryset.filter(fecha_subida__gte=timezone.now() - timedelta(days=7)).count()
        }
        
        for choice in ArchivoMedico.TIPO_ARCHIVO_CHOICES:
            stats['por_tipo'][choice[0]] = queryset.filter(tipo_archivo=choice[0]).count()
        
        return Response(stats)


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def tipos_archivo_publicos(request):
    """
    Catálogo estático de tipos de archivo permitidos (value/label del modelo).

    AllowAny: no expone datos de pacientes ni rutas; solo metadatos de formulario.
    GET no modifica estado.
    """
    from .models import ArchivoMedico
    tipos = ArchivoMedico.TIPO_CHOICES
    return Response([{'value': choice[0], 'label': choice[1]} for choice in tipos])
