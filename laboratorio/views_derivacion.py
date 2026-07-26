"""ViewSet laboratorios de derivación externos."""
from rest_framework import filters, viewsets
from django_filters.rest_framework import DjangoFilterBackend

from api.permissions import LimsTipoExamenCatalogPermission
from laboratorio.models_derivacion import LaboratorioDerivacion
from laboratorio.serializers_derivacion import LaboratorioDerivacionSerializer


class LaboratorioDerivacionViewSet(viewsets.ModelViewSet):
    queryset = LaboratorioDerivacion.objects.all()
    serializer_class = LaboratorioDerivacionSerializer
    permission_classes = [LimsTipoExamenCatalogPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["activo", "codigo"]
    search_fields = ["codigo", "nombre", "ciudad"]
    ordering = ["codigo"]
    http_method_names = ["get", "post", "patch", "head", "options"]
