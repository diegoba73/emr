"""
ViewSets para la app catalogos.
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import (
    CentroFisico,
    TipoAtencion,
    Procedimiento,
    AreaInternacion,
    CamaInternacion,
)
from .serializers import (
    CentroFisicoSerializer,
    TipoAtencionSerializer,
    ProcedimientoSerializer,
    AreaInternacionSerializer,
    CamaInternacionSerializer,
)


class CentroFisicoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Centros Físicos.
    Expone la infraestructura estática para los "Selects" del frontend.
    """
    queryset = CentroFisico.objects.filter(activo=True)
    serializer_class = CentroFisicoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['codigo']


class TipoAtencionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Tipos de Atención.
    Expone la infraestructura estática para los "Selects" del frontend.
    """
    queryset = TipoAtencion.objects.filter(activo=True).select_related('centro_fisico')
    serializer_class = TipoAtencionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['centro_fisico', 'codigo']

    def get_queryset(self):
        queryset = super().get_queryset()
        centro_fisico = self.request.query_params.get('centro_fisico', None)
        if centro_fisico:
            queryset = queryset.filter(centro_fisico__codigo=centro_fisico)
        return queryset


class AreaInternacionViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de áreas de internación (solo lectura)."""

    queryset = AreaInternacion.objects.filter(activo=True).select_related('centro_fisico')
    serializer_class = AreaInternacionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['centro_fisico', 'codigo']

    def get_queryset(self):
        queryset = super().get_queryset()
        centro_fisico = self.request.query_params.get('centro_fisico', None)
        if centro_fisico:
            queryset = queryset.filter(centro_fisico__codigo=centro_fisico)
        return queryset


class CamaInternacionViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de camas de internación (solo lectura)."""

    queryset = CamaInternacion.objects.filter(activa=True).select_related(
        'area', 'area__centro_fisico'
    )
    serializer_class = CamaInternacionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero', 'area__nombre', 'area__codigo']
    ordering = ['area', 'numero']

    def get_queryset(self):
        queryset = super().get_queryset()
        area = self.request.query_params.get('area', None)
        estado = self.request.query_params.get('estado', None)
        if area:
            queryset = queryset.filter(area__codigo=area)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset


class ProcedimientoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Procedimientos.
    Expone el catálogo de procedimientos médicos.
    """
    queryset = Procedimiento.objects.filter(activo=True).select_related('especialidad')
    serializer_class = ProcedimientoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering_fields = ['nombre', 'codigo', 'duracion_estimada']
    ordering = ['nombre']
