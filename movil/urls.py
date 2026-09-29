from django.urls import path
from .views import InstitucionMovil, LoginMovil, MiPerfil, LogoutMovil, PushMovil, TurnosMovil, MedicosMovil

urlpatterns = [
    path('institucion/', InstitucionMovil.as_view()),
    path('login/', LoginMovil.as_view()),
    path('me/', MiPerfil.as_view()),
    path('logout/', LogoutMovil.as_view()),
    path('push/', PushMovil.as_view()),
    path('medicos/', MedicosMovil.as_view({'get': 'list'})),
    path('medicos/<int:pk>/slots/', MedicosMovil.as_view({'get': 'slots'})),
    path('turnos/', TurnosMovil.as_view({'get': 'list'})),
    path('turnos/reservar-horario/', TurnosMovil.as_view({'post': 'reservar_horario'})),
    path('turnos/<int:pk>/', TurnosMovil.as_view({'get': 'retrieve'})),
    path('turnos/<int:pk>/asistencia/', TurnosMovil.as_view({'post': 'confirmar_asistencia'})),
    path('turnos/<int:pk>/confirmar/', TurnosMovil.as_view({'post': 'confirmar'})),
    path('turnos/<int:pk>/cancelar/', TurnosMovil.as_view({'post': 'cancelar'})),
    path('turnos/<int:pk>/reprogramar-horario/', TurnosMovil.as_view({'post': 'reprogramar_horario'})),
    path('turnos/<int:pk>/reprogramar/', TurnosMovil.as_view({'post': 'reprogramar'})),
]
