from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pacientes', views.PacienteViewSet)
router.register(r'medicos', views.MedicoViewSet)
router.register(r'especialidades', views.EspecialidadViewSet)
router.register(r'tipos-examen', views.TipoExamenViewSet)
router.register(r'paneles-examen', views.PanelExamenViewSet)
router.register(r'solicitudes-examen', views.SolicitudExamenViewSet)
router.register(r'resultados-examen', views.ResultadoExamenViewSet)
router.register(r'consultas', views.ConsultaViewSet)
router.register(r'internaciones', views.InternacionViewSet)
router.register(r'diagnosticos', views.DiagnosticoViewSet)
router.register(r'prescripciones', views.PrescripcionViewSet)
router.register(r'medicamentos', views.MedicamentoViewSet)
router.register(r'turnos', views.TurnoViewSet)
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
    # URLs de autenticación
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/current-user/', views.current_user, name='current_user'),
    path('auth/users/', views.list_users, name='list_users'),
    path('auth/groups/', views.list_groups, name='list_groups'),
    
    # URLs de registro de usuarios
    path('auth/register/patient/', views.register_patient, name='register_patient'),
    path('auth/register/doctor/', views.register_doctor, name='register_doctor'),
    path('auth/register/secretary/', views.register_secretary, name='register_secretary'),
] 