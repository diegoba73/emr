from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponseForbidden
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.utils.decorators import method_decorator
import os
import logging

from .models import ArchivoMedico
from .serializers import ArchivoMedicoSerializer, ArchivoMedicoListSerializer

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Autenticación de sesión sin exigir CSRF para APIs (solo desarrollo)."""
    def enforce_csrf(self, request):  # type: ignore[override]
        return  # No-op: desactiva verificación CSRF para SessionAuthentication


class ArchivoMedicoViewSet(viewsets.ModelViewSet):
    queryset = ArchivoMedico.objects.select_related('paciente', 'consulta', 'subido_por').all()
    serializer_class = ArchivoMedicoSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptSessionAuthentication, TokenAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['paciente', 'tipo_archivo', 'es_urgente', 'fecha_estudio']
    search_fields = ['titulo', 'descripcion', 'paciente__nombre', 'paciente__apellido']
    ordering_fields = ['fecha_subida', 'fecha_estudio', 'titulo']
    ordering = ['-fecha_subida']

    def get_queryset(self):
        """Filtra por rol del usuario sin relaciones inexistentes.

        - Admin/Staff: ven todo
        - Médicos/Secretarias: ven todo (hasta implementar reglas específicas)
        - Pacientes: solo sus propios archivos
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_superuser or user.is_staff:
            return queryset

        # No existe relación Paciente.medico en el modelo actual; evitar filtros inválidos
        if hasattr(user, 'medico') or any(getattr(user, attr, None) for attr in ['secretaria']):
            return queryset

        if hasattr(user, 'paciente'):
            return queryset.filter(paciente=user.paciente)

        return queryset.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return ArchivoMedicoListSerializer
        return ArchivoMedicoSerializer

    def perform_create(self, serializer):
        """Asigna el usuario que sube el archivo. Permiso: autenticado."""
        serializer.save(subido_por=self.request.user)
        logger.info(f"Archivo subido por {self.request.user.username}")

    def _tiene_permiso_lectura(self, user, archivo):
        """Verificar si el usuario tiene permiso para ver/descargar el archivo"""
        if user.is_superuser or user.is_staff:
            return True
            
        # Si es médico, puede ver archivos de sus pacientes
        if hasattr(user, 'medico') and archivo.paciente.medico == user.medico:
            return True
            
        # Si es paciente, solo puede ver sus propios archivos
        if hasattr(user, 'paciente') and archivo.paciente == user.paciente:
            return True
            
        return False

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        archivo = self.get_object()
        
        # Verificar permisos de descarga
        if not self._tiene_permiso_lectura(request.user, archivo):
            return Response(
                {'error': 'No tiene permiso para descargar este archivo'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if not os.path.exists(archivo.archivo.path):
            logger.error(f"Archivo no encontrado en la ruta: {archivo.archivo.path}")
            return Response(
                {'error': 'Archivo no encontrado en el servidor'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        try:
            response = FileResponse(open(archivo.archivo.path, 'rb'), as_attachment=True)
            # Configurar encabezados de seguridad
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(archivo.archivo.path)}"'
            response['X-Content-Type-Options'] = 'nosniff'
            return response
        except Exception as e:
            logger.error(f"Error al descargar archivo: {str(e)}")
            return Response(
                {'error': 'Error al procesar la descarga'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def tipos_disponibles(self, request):
        """Devuelve tipos de archivo disponibles (requiere autenticación)."""
        tipos = [{'value': choice[0], 'label': choice[1]} for choice in ArchivoMedico.TIPO_CHOICES]
        return Response(tipos)

    @action(detail=False, methods=['get'])
    def por_paciente(self, request):
        """Lista archivos por paciente (query param: paciente_id)."""
        paciente_id = request.query_params.get('paciente_id')
        if not paciente_id:
            return Response({'error': 'paciente_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        archivos = self.get_queryset().filter(paciente_id=paciente_id)
        serializer = ArchivoMedicoListSerializer(archivos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_consulta(self, request):
        """Lista archivos por consulta (query param: consulta_id)."""
        consulta_id = request.query_params.get('consulta_id')
        if not consulta_id:
            return Response({'error': 'consulta_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        archivos = self.get_queryset().filter(consulta_id=consulta_id)
        serializer = ArchivoMedicoListSerializer(archivos, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Elimina el archivo respetando permisos y borrando el fichero físico."""
        archivo = self.get_object()

        # Permisos: superuser/staff o permiso de app o dueño paciente que lo subió
        has_model_perm = request.user.has_perm('archivos_medicos.delete_archivomedico')
        is_admin = request.user.is_superuser or request.user.is_staff
        is_owner_patient = hasattr(request.user, 'paciente') and (
            archivo.paciente_id == getattr(request.user.paciente, 'id', None) and archivo.subido_por_id == request.user.id
        )

        if not (is_admin or has_model_perm or is_owner_patient):
            logger.warning(f"Eliminación no autorizada por {request.user.username}")
            return Response({'error': 'No tiene permisos para eliminar este archivo'}, status=status.HTTP_403_FORBIDDEN)

        # Eliminar archivo físico si existe
        try:
            if archivo.archivo and archivo.archivo.path and os.path.exists(archivo.archivo.path):
                os.remove(archivo.archivo.path)
        except Exception as file_err:
            logger.warning(f"No se pudo eliminar el archivo físico: {file_err}")

        archivo.delete()
        logger.info(f"Archivo {archivo.id} eliminado por {request.user.username}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """Actualiza un archivo con reglas de permiso similares a eliminar."""
        archivo = self.get_object()

        has_model_perm = request.user.has_perm('archivos_medicos.change_archivomedico')
        is_admin = request.user.is_superuser or request.user.is_staff
        is_owner_uploader = archivo.subido_por_id == request.user.id
        is_owner_patient = hasattr(request.user, 'paciente') and (archivo.paciente_id == getattr(request.user.paciente, 'id', None))

        if not (is_admin or has_model_perm or is_owner_uploader or is_owner_patient):
            return Response({'error': 'No tiene permisos para editar este archivo'}, status=status.HTTP_403_FORBIDDEN)

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """PATCH con las mismas reglas que update."""
        archivo = self.get_object()

        has_model_perm = request.user.has_perm('archivos_medicos.change_archivomedico')
        is_admin = request.user.is_superuser or request.user.is_staff
        is_owner_uploader = archivo.subido_por_id == request.user.id
        is_owner_patient = hasattr(request.user, 'paciente') and (archivo.paciente_id == getattr(request.user.paciente, 'id', None))

        if not (is_admin or has_model_perm or is_owner_uploader or is_owner_patient):
            return Response({'error': 'No tiene permisos para editar este archivo'}, status=status.HTTP_403_FORBIDDEN)

        return super().partial_update(request, *args, **kwargs)

@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request):
    """Endpoint para obtener el token CSRF"""
    return Response({'detail': 'CSRF cookie set'})
