from django.contrib import admin
from .models import Sector, Cama, Internacion


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(Cama)
class CamaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'sector', 'estado', 'aislada']
    list_filter = ['sector', 'estado', 'aislada']
    search_fields = ['nombre', 'sector__nombre']


@admin.register(Internacion)
class InternacionAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'cama', 'medico', 'fecha_ingreso', 'fecha_alta', 'activo']
    list_filter = ['activo', 'cama__sector', 'fecha_ingreso']
    search_fields = ['paciente__nombre', 'paciente__apellido', 'diagnostico_ingreso']
    readonly_fields = ['fecha_ingreso']
