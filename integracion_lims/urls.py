from django.urls import path
from .views import recibir_resultados_lims, obtener_analisis_paciente

urlpatterns = [
    path('webhook/resultados/', recibir_resultados_lims, name='lims_webhook'),
    path('analisis/paciente/<int:paciente_id>/', obtener_analisis_paciente, name='analisis_paciente'),
]