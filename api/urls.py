from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from pacientes.views import PacienteViewSet
from medicos.views import MedicoViewSet, EspecialidadViewSet
from catalogos.views import CentroFisicoViewSet, TipoAtencionViewSet
from turnos.views import TurnoViewSet, RecursoViewSet, AtencionViewSet, EvolucionInternacionViewSet
from historias_clinicas.views import HistoriaClinicaViewSet, ConsultaViewSet
from solicitudes.views import SolicitudViewSet
from laboratorio.views import (
    SolicitudExamenViewSet,
    TipoExamenViewSet,
    TipoMuestraViewSet,
    PanelExamenViewSet,
)
from laboratorio.views_muestras import (
    AreaLaboratorioViewSet,
    MuestraTransaccionalViewSet,
    SeccionLaboratorioViewSet,
    TipoContenedorViewSet,
)
from laboratorio.views_microbiologia import (
    AisladoMicrobiologicoViewSet,
    AntibiogramaViewSet,
    AntibioticoViewSet,
    EstudioMicrobiologiaViewSet,
    IdentificacionMicroorganismoViewSet,
    InformeMicrobiologiaViewSet,
    LecturaCultivoViewSet,
    MedioCultivoViewSet,
    MicroorganismoViewSet,
    ResultadoAntibioticoViewSet,
    SiembraMicrobiologiaViewSet,
)
from usuarios.views import PacienteRegisterView
from core.views import HealthCheckView

router = DefaultRouter()
router.register(r'pacientes', PacienteViewSet, basename='pacientes')
router.register(r'medicos', MedicoViewSet, basename='medicos')
router.register(r'especialidades', EspecialidadViewSet, basename='especialidades')
router.register(r'centros-fisicos', CentroFisicoViewSet, basename='centros-fisicos')
router.register(r'tipos-atencion', TipoAtencionViewSet, basename='tipos-atencion')

# Router adicional para rutas con prefijo 'catalogos/' (compatibilidad con frontend)
catalogos_router = DefaultRouter()
catalogos_router.register(r'tipos-atencion', TipoAtencionViewSet, basename='catalogos-tipos-atencion')
catalogos_router.register(r'centros-fisicos', CentroFisicoViewSet, basename='catalogos-centros-fisicos')
router.register(r'recursos', RecursoViewSet, basename='recursos')
router.register(r'turnos', TurnoViewSet, basename='turnos')
router.register(r'atenciones', AtencionViewSet, basename='atenciones')
router.register(r'historias-clinicas', HistoriaClinicaViewSet, basename='historias-clinicas')
router.register(r'consultas', ConsultaViewSet, basename='consultas')
router.register(r'solicitudes', SolicitudViewSet, basename='solicitudes')
router.register(r'lab/solicitudes', SolicitudExamenViewSet, basename='lab-solicitudes')
router.register(r'lab/examenes', TipoExamenViewSet, basename='lab-examenes')
router.register(r'lab/muestras', TipoMuestraViewSet, basename='lab-muestras')
router.register(r'lab/paneles', PanelExamenViewSet, basename='lab-paneles')
router.register(r'lab/areas', AreaLaboratorioViewSet, basename='lab-areas')
router.register(r'lab/secciones', SeccionLaboratorioViewSet, basename='lab-secciones')
router.register(r'lab/contenedores', TipoContenedorViewSet, basename='lab-contenedores')
router.register(
    r'lab/muestras-transaccionales',
    MuestraTransaccionalViewSet,
    basename='lab-muestras-transaccionales',
)
# Rutas adicionales según requisitos del usuario
router.register(r'laboratorio/tipos-examen', TipoExamenViewSet, basename='laboratorio-tipos-examen')
router.register(r'laboratorio/solicitudes', SolicitudExamenViewSet, basename='laboratorio-solicitudes')
router.register(r'laboratorio/areas', AreaLaboratorioViewSet, basename='laboratorio-areas')
router.register(r'laboratorio/secciones', SeccionLaboratorioViewSet, basename='laboratorio-secciones')
router.register(r'laboratorio/contenedores', TipoContenedorViewSet, basename='laboratorio-contenedores')
router.register(
    r'laboratorio/muestras-transaccionales',
    MuestraTransaccionalViewSet,
    basename='laboratorio-muestras-transaccionales',
)
# Microbiología base B3.1 — /api/lab/microbiologia/...
router.register(
    r'lab/microbiologia/medios',
    MedioCultivoViewSet,
    basename='lab-micro-medios',
)
router.register(
    r'lab/microbiologia/estudios',
    EstudioMicrobiologiaViewSet,
    basename='lab-micro-estudios',
)
router.register(
    r'lab/microbiologia/siembras',
    SiembraMicrobiologiaViewSet,
    basename='lab-micro-siembras',
)
router.register(
    r'lab/microbiologia/lecturas',
    LecturaCultivoViewSet,
    basename='lab-micro-lecturas',
)
# Alias /api/laboratorio/microbiologia/... (misma clase ViewSet).
router.register(
    r'laboratorio/microbiologia/medios',
    MedioCultivoViewSet,
    basename='laboratorio-micro-medios',
)
router.register(
    r'laboratorio/microbiologia/estudios',
    EstudioMicrobiologiaViewSet,
    basename='laboratorio-micro-estudios',
)
router.register(
    r'laboratorio/microbiologia/siembras',
    SiembraMicrobiologiaViewSet,
    basename='laboratorio-micro-siembras',
)
router.register(
    r'laboratorio/microbiologia/lecturas',
    LecturaCultivoViewSet,
    basename='laboratorio-micro-lecturas',
)
# B3.2 — Microorganismos, aislados, identificaciones (mismo patrón alias).
router.register(
    r'lab/microbiologia/microorganismos',
    MicroorganismoViewSet,
    basename='lab-micro-microorganismos',
)
router.register(
    r'lab/microbiologia/aislados',
    AisladoMicrobiologicoViewSet,
    basename='lab-micro-aislados',
)
router.register(
    r'lab/microbiologia/identificaciones',
    IdentificacionMicroorganismoViewSet,
    basename='lab-micro-identificaciones',
)
router.register(
    r'laboratorio/microbiologia/microorganismos',
    MicroorganismoViewSet,
    basename='laboratorio-micro-microorganismos',
)
router.register(
    r'laboratorio/microbiologia/aislados',
    AisladoMicrobiologicoViewSet,
    basename='laboratorio-micro-aislados',
)
router.register(
    r'laboratorio/microbiologia/identificaciones',
    IdentificacionMicroorganismoViewSet,
    basename='laboratorio-micro-identificaciones',
)
# B3.3 — Antibióticos / Antibiogramas / Resultados de antibiótico (con aliases).
router.register(
    r'lab/microbiologia/antibioticos',
    AntibioticoViewSet,
    basename='lab-micro-antibioticos',
)
router.register(
    r'lab/microbiologia/antibiogramas',
    AntibiogramaViewSet,
    basename='lab-micro-antibiogramas',
)
router.register(
    r'lab/microbiologia/resultados-antibiotico',
    ResultadoAntibioticoViewSet,
    basename='lab-micro-resultados-antibiotico',
)
router.register(
    r'laboratorio/microbiologia/antibioticos',
    AntibioticoViewSet,
    basename='laboratorio-micro-antibioticos',
)
router.register(
    r'laboratorio/microbiologia/antibiogramas',
    AntibiogramaViewSet,
    basename='laboratorio-micro-antibiogramas',
)
router.register(
    r'laboratorio/microbiologia/resultados-antibiotico',
    ResultadoAntibioticoViewSet,
    basename='laboratorio-micro-resultados-antibiotico',
)
# B3.4 — Informes microbiológicos (con aliases).
router.register(
    r'lab/microbiologia/informes',
    InformeMicrobiologiaViewSet,
    basename='lab-micro-informes',
)
router.register(
    r'laboratorio/microbiologia/informes',
    InformeMicrobiologiaViewSet,
    basename='laboratorio-micro-informes',
)
router.register(r'disponibilidades', views.DisponibilidadMedicoViewSet, basename='disponibilidades')
router.register(r'excepciones', views.ExcepcionMedicoViewSet, basename='excepciones')
# router.register(r'tipos-examen', views.TipoExamenViewSet)
# router.register(r'paneles-examen', views.PanelExamenViewSet)
# router.register(r'solicitudes-examen', views.SolicitudExamenViewSet)
# router.register(r'resultados-examen', views.ResultadoExamenViewSet)
# Consultas ahora se registra desde historias_clinicas.views (ver arriba)
router.register(r'diagnosticos', views.DiagnosticoViewSet)
router.register(r'diagnosticos-cie10', views.DiagnosticoCIE10ViewSet)
router.register(r'prescripciones', views.PrescripcionViewSet)
router.register(r'medicamentos', views.MedicamentoViewSet)
router.register(r'internaciones', views.InternacionViewSet)
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')
# Atenciones ahora se registra desde turnos.views (ver arriba)
router.register(r'consultas-ambulatorias', views.ConsultaAmbulatoriaViewSet)
router.register(r'evoluciones-internacion', EvolucionInternacionViewSet, basename='evoluciones-internacion')
router.register(r'registros-procedimientos', views.RegistroProcedimientoViewSet)
router.register(r'registros-quirurgicos', views.RegistroQuirurgicoViewSet)
router.register(r'estudios-diagnosticos', views.EstudioDiagnosticoViewSet)
router.register(r'procedimientos-catalogo', views.ProcedimientoCatalogoViewSet)
router.register(r'documentos', views.DocumentoViewSet)

urlpatterns = [
    # Health check endpoint (sin autenticación requerida)
    path('health/', HealthCheckView.as_view(), name='health_check'),
    
    # Endpoint público para obtener token CSRF
    path('auth/csrf-token/', views.csrf_token_view, name='csrf_token'),
    
    path('', include(router.urls)),
    
    # Rutas adicionales con prefijo 'catalogos/' para compatibilidad con frontend
    path('catalogos/', include(catalogos_router.urls)),
    
    # Ruta para archivos médicos (compatibilidad con frontend)
    path('archivos-medicos/', include('archivos_medicos.urls')),

    # Estudios complementarios EMR (C6.4.1 — sin LIMS/PACS)
    path('estudios-complementarios/', include('estudios.urls')),
    
    # Ruta para internación (sectores, camas, internaciones)
    path('internacion/', include('internacion.urls')),

    # Auditoría (solo lectura, admin)
    path('auditoria/', include('auditoria.urls')),
    
    # URLs de autenticación
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/current-user/', views.current_user, name='current_user'),
    path('auth/users/', views.list_users, name='list_users'),
    path('auth/groups/', views.list_groups, name='list_groups'),
    
    # URLs de registro de usuarios
    path('auth/register/', PacienteRegisterView.as_view(), name='auth_register'),
    path('auth/register/patient/', views.register_patient, name='register_patient'),
    path('auth/register/doctor/', views.register_doctor, name='register_doctor'),
    path('auth/register/secretary/', views.register_secretary, name='register_secretary'),
] 