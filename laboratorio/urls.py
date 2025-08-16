# Ejemplo: laboratorio/urls.py
from django.urls import path
from . import views # Asumiendo que views.py está en la misma app

urlpatterns = [
    # ... otras URLs de tu app ...
    path('autocomplete/consultas-filtradas/', 
         views.ConsultaPorPacienteAutocompleteView.as_view(), 
         name='autocomplete_consultas_filtradas'),
]