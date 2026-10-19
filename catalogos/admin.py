from django.contrib import admin
from .models import (
    DiagnosticoCIE10,
    Medicamento,
    ProcedimientoCatalogo,
    CirugiaEspecialidad,
    CirugiaProcedimiento,
    CirugiaAbordaje,
    EstudioDiagnostico,
    CentroAtencion,
    CentroFisico,
    TipoAtencion,
)


@admin.register(DiagnosticoCIE10)
class DiagnosticoCIE10Admin(admin.ModelAdmin):
    list_display = ['codigo', 'descripcion', 'capitulo', 'enfermedad', 'categoria', 'activo']
    list_filter = ['capitulo', 'enfermedad', 'categoria', 'activo']
    search_fields = ['codigo', 'descripcion', 'enfermedad', 'capitulo']
    ordering = ['codigo']
    readonly_fields = ['codigo']  # El código no se debe editar manualmente


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'principio_activo', 'presentacion', 'concentracion', 'via_administracion', 'activo']
    list_filter = ['via_administracion', 'activo']
    search_fields = ['nombre', 'principio_activo', 'codigo_atc']
    ordering = ['nombre']


@admin.register(ProcedimientoCatalogo)
class ProcedimientoCatalogoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'clasificacion_quirurgica', 'activo']
    list_filter = ['clasificacion_quirurgica', 'activo']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']


@admin.register(CirugiaEspecialidad)
class CirugiaEspecialidadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'orden', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre']
    ordering = ['orden', 'nombre']


@admin.register(CirugiaProcedimiento)
class CirugiaProcedimientoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'especialidad', 'activo']
    list_filter = ['especialidad', 'activo']
    search_fields = ['nombre', 'especialidad__nombre']
    ordering = ['especialidad__nombre', 'nombre']


@admin.register(CirugiaAbordaje)
class CirugiaAbordajeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'procedimiento', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'procedimiento__nombre']
    ordering = ['procedimiento__nombre', 'nombre']


@admin.register(EstudioDiagnostico)
class EstudioDiagnosticoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']


@admin.register(CentroAtencion)
class CentroAtencionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'telefono', 'email', 'activo']
    list_filter = ['tipo', 'activo']
    search_fields = ['nombre', 'direccion']
    ordering = ['nombre']


@admin.register(CentroFisico)
class CentroFisicoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'telefono', 'activo']
    list_filter = ['codigo', 'activo']
    search_fields = ['codigo', 'nombre', 'direccion']
    ordering = ['codigo']


@admin.register(TipoAtencion)
class TipoAtencionAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'centro_fisico', 'requiere_internacion', 'es_urgencia', 'activo']
    list_filter = ['centro_fisico', 'requiere_internacion', 'es_urgencia', 'activo']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['centro_fisico', 'codigo']
