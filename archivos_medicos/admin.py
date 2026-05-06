from django.contrib import admin
from .models import ArchivoMedico


@admin.register(ArchivoMedico)
class ArchivoMedicoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'paciente', 'tipo_archivo', 'fecha_subida')
    list_filter = ('tipo_archivo', 'es_urgente')
    search_fields = ('titulo', 'paciente__nombre', 'paciente__apellido', 'paciente__dni')
    readonly_fields = ('fecha_subida',)
    
    fieldsets = (
        ('Información del Archivo', {
            'fields': ('titulo', 'descripcion', 'tipo_archivo', 'archivo', 'es_urgente')
        }),
        ('Relaciones', {
            'fields': ('paciente', 'consulta', 'subido_por')
        }),
        ('Fechas', {
            'fields': ('fecha_estudio', 'fecha_subida')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Asignar el usuario actual al archivo si no tiene uno"""
        if not obj.subido_por:
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)
