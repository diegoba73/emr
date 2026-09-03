from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_hc

router = DefaultRouter()
router.register(r'sectores', views.SectorViewSet, basename='sector')
router.register(r'camas', views.CamaViewSet, basename='cama')
router.register(r'tipos-dieta', views.TipoDietaViewSet, basename='tipo-dieta')
router.register(r'internaciones', views.InternacionViewSet, basename='internacion')
router.register(
    r'internaciones/(?P<internacion_pk>[^/.]+)/indicaciones-medicas',
    views_hc.IndicacionMedicaViewSet,
    basename='indicacion-medica',
)
router.register(
    r'internaciones/(?P<internacion_pk>[^/.]+)/medicaciones',
    views_hc.MedicacionInternacionViewSet,
    basename='medicacion-internacion',
)
router.register(
    r'internaciones/(?P<internacion_pk>[^/.]+)/controles-enfermeria',
    views_hc.ControlEnfermeriaViewSet,
    basename='control-enfermeria',
)
router.register(
    r'internaciones/(?P<internacion_pk>[^/.]+)/balances-hidricos',
    views_hc.BalanceHidricoViewSet,
    basename='balance-hidrico',
)
router.register(
    r'internaciones/(?P<internacion_pk>[^/.]+)/notas-enfermeria',
    views_hc.NotaEnfermeriaHcViewSet,
    basename='nota-enfermeria-hc',
)
router.register(
    r'internaciones/(?P<internacion_pk>[^/.]+)/kinesiologia',
    views_hc.RegistroKinesiologiaViewSet,
    basename='registro-kinesiologia',
)
router.register(
    r'internaciones/(?P<internacion_pk>[^/.]+)/medicaciones-habituales',
    views_hc.MedicacionHabitualInternacionViewSet,
    basename='medicacion-habitual-internacion',
)

urlpatterns = [
    path('', include(router.urls)),
]
