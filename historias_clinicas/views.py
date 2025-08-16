from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Consulta, Internacion
from .serializers import InternacionSerializer, InternacionCreateSerializer

# Create your views here.

class InternacionViewSet(viewsets.ModelViewSet):
    queryset = Internacion.objects.all()
    serializer_class = InternacionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return InternacionCreateSerializer
        return InternacionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrar por rol del usuario
        if hasattr(user, 'rol'):
            if user.rol.upper() == 'MEDICO':
                # Médicos ven sus propias internaciones
                try:
                    queryset = queryset.filter(medico_responsable=user.medico)
                except:
                    queryset = queryset.none()
            elif user.rol.upper() == 'ADMIN':
                # Admins ven todas
                pass
            else:
                # Otros roles no ven internaciones
                queryset = queryset.none()
        
        # Filtros adicionales
        estado = self.request.query_params.get('estado', None)
        centro_fisico = self.request.query_params.get('centro_fisico', None)
        area = self.request.query_params.get('area', None)
        
        if estado:
            queryset = queryset.filter(estado=estado)
        if centro_fisico:
            queryset = queryset.filter(cama__area__centro_fisico__codigo=centro_fisico)
        if area:
            queryset = queryset.filter(cama__area__codigo=area)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def dar_alta(self, request, pk=None):
        """Dar alta a una internación"""
        internacion = self.get_object()
        
        if internacion.estado != 'ACTIVA':
            return Response(
                {'error': 'Solo se puede dar alta a internaciones activas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar estado y fecha de alta
        internacion.estado = 'ALTA_MEDICA'
        internacion.fecha_alta = request.data.get('fecha_alta')
        internacion.observaciones = request.data.get('observaciones', '')
        internacion.save()
        
        # Liberar la cama
        cama = internacion.cama
        cama.estado = 'DISPONIBLE'
        cama.save()
        
        serializer = self.get_serializer(internacion)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtener estadísticas de internaciones"""
        queryset = self.get_queryset()
        
        # Estadísticas por estado
        activas = queryset.filter(estado='ACTIVA').count()
        altas_medicas = queryset.filter(estado='ALTA_MEDICA').count()
        altas_voluntarias = queryset.filter(estado='ALTA_VOLUNTARIA').count()
        
        # Estadísticas por centro
        cehta = queryset.filter(cama__area__centro_fisico__codigo='CEHTA').count()
        icpl = queryset.filter(cama__area__centro_fisico__codigo='ICPL').count()
        
        return Response({
            'por_estado': {
                'activas': activas,
                'altas_medicas': altas_medicas,
                'altas_voluntarias': altas_voluntarias
            },
            'por_centro': {
                'cehta': cehta,
                'icpl': icpl
            },
            'total': queryset.count()
        })
