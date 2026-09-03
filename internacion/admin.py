from django.contrib import admin
from .models import (
    BalanceHidrico,
    Cama,
    ControlEnfermeria,
    IndicacionMedica,
    Internacion,
    MedicacionHabitualInternacion,
    MedicacionInternacion,
    NotaEnfermeria,
    RegistroKinesiologia,
    Sector,
    TipoDieta,
)


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(Cama)
class CamaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'sector', 'estado', 'aislada']
    list_filter = ['sector', 'estado', 'aislada']
    search_fields = ['nombre', 'sector__nombre']


@admin.register(TipoDieta)
class TipoDietaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']


@admin.register(Internacion)
class InternacionAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'cama', 'medico', 'tipo_dieta', 'fecha_ingreso', 'fecha_alta', 'activo']
    list_filter = ['activo', 'cama__sector', 'tipo_dieta', 'fecha_ingreso']
    search_fields = ['paciente__nombre', 'paciente__apellido', 'diagnostico_ingreso']
    readonly_fields = ['fecha_ingreso']


@admin.register(IndicacionMedica)
class IndicacionMedicaAdmin(admin.ModelAdmin):
    list_display = ['internacion', 'fecha', 'vigente']


@admin.register(MedicacionHabitualInternacion)
class MedicacionHabitualInternacionAdmin(admin.ModelAdmin):
    list_display = ['internacion', 'medicamento', 'dosis_mg_dia']


@admin.register(MedicacionInternacion)
class MedicacionInternacionAdmin(admin.ModelAdmin):
    list_display = ['internacion', 'medicamento', 'activa', 'fecha']


@admin.register(ControlEnfermeria)
class ControlEnfermeriaAdmin(admin.ModelAdmin):
    list_display = ['internacion', 'turno', 'fecha']


@admin.register(BalanceHidrico)
class BalanceHidricoAdmin(admin.ModelAdmin):
    list_display = ['internacion', 'turno', 'fecha']


@admin.register(NotaEnfermeria)
class NotaEnfermeriaAdmin(admin.ModelAdmin):
    list_display = ['internacion', 'fecha']


@admin.register(RegistroKinesiologia)
class RegistroKinesiologiaAdmin(admin.ModelAdmin):
    list_display = ['internacion', 'fecha']
