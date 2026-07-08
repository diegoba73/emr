from django.contrib import admin
from .models import (
    DiagnosticoCIE10,
    Medicamento,
    ProcedimientoCatalogo,
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
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']


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
