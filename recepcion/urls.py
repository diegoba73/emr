from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'puestos', views.PuestoRecepcionViewSet, basename='recepcion-puestos')
router.register(r'reglas', views.ReglaRuteoRecepcionViewSet, basename='recepcion-reglas')
router.register(r'llegadas', views.LlegadaRecepcionViewSet, basename='recepcion-llegadas')

urlpatterns = [
    path('pantalla-llamados/', views.pantalla_llamados, name='recepcion-pantalla'),
    path('kiosco-checkin/', views.kiosco_checkin, name='recepcion-kiosco'),
    path('kiosco-config/', views.kiosco_config, name='recepcion-kiosco-config'),
    path('kiosco-qr.png', views.kiosco_qr_png, name='recepcion-kiosco-qr'),
    path('espera/<str:token>/', views.espera_paciente, name='recepcion-espera'),
    path('espera/<str:token>/ya-voy/', views.espera_ya_voy, name='recepcion-espera-ya-voy'),
    path('resolver-puesto/', views.resolver_puesto_preview, name='recepcion-resolver'),
    path('cobertura-hoy/', views.cobertura_hoy, name='recepcion-cobertura-hoy'),
    path('', include(router.urls)),
]
