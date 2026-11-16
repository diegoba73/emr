from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EstudioComplementarioViewSet, TipoEstudioComplementarioViewSet
from .views_pedido import (
    MedicoTipoEstudioViewSet,
    PedidoEstudioPacienteViewSet,
    TipoEstudioSalaViewSet,
)

router = DefaultRouter()
router.register(r'tipos', TipoEstudioComplementarioViewSet, basename='tipo-estudio-complementario')
router.register(r'medico-tipos', MedicoTipoEstudioViewSet, basename='medico-tipo-estudio')
router.register(r'tipo-salas', TipoEstudioSalaViewSet, basename='tipo-estudio-sala')
router.register(r'pedidos', PedidoEstudioPacienteViewSet, basename='pedido-estudio-paciente')
router.register(r'', EstudioComplementarioViewSet, basename='estudio-complementario')

urlpatterns = [
    path('', include(router.urls)),
]
