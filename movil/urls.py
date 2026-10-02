from django.urls import path
from .views import InstitucionMovil, LoginMovil, MiPerfil, LogoutMovil, PushMovil, TurnosMovil, MedicosMovil
from .views_informes import (
    InformesMovil,
    InformeMovilDetalle,
    InformeMovilPdf,
    InformeMovilValidar,
    InformeMovilInformarParcial,
)
from .views_lab import (
    CatalogoLabMovil,
    FavoritosLabMovil,
    OrdenesLabMovil,
    PacienteContextoLabMovil,
    PacientesLabMovil,
    RestriccionesEnsayosLabMovil,
)

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
    path('informes/', InformesMovil.as_view()),
    path('informes/<int:pk>/', InformeMovilDetalle.as_view()),
    path('informes/<int:pk>/pdf/', InformeMovilPdf.as_view()),
    path('informes/<int:pk>/validar/', InformeMovilValidar.as_view()),
    path('informes/<int:pk>/informar-parcial/', InformeMovilInformarParcial.as_view()),
    path('lab/pacientes/', PacientesLabMovil.as_view()),
    path('lab/pacientes/<int:pk>/contexto/', PacienteContextoLabMovil.as_view()),
    path('lab/pacientes/<int:pk>/restricciones-ensayos/', RestriccionesEnsayosLabMovil.as_view()),
    path('lab/catalogo/', CatalogoLabMovil.as_view()),
    path('lab/favoritos/', FavoritosLabMovil.as_view()),
    path('lab/ordenes/', OrdenesLabMovil.as_view()),
]
