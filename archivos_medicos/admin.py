from django.contrib import admin
from .models import ArchivoMedico


@admin.register(ArchivoMedico)
class ArchivoMedicoAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 'paciente', 'tipo_archivo', 'fecha_subida', 'es_urgente'
    ]
    list_filter = [
        'tipo_archivo', 'es_urgente', 'fecha_estudio'
    ]
    search_fields = [
        'titulo', 'descripcion', 'paciente__nombre',
        'paciente__apellido'
    ]
    readonly_fields = ['fecha_subida', 'subido_por']
    autocomplete_fields = ['paciente', 'consulta']
    date_hierarchy = 'fecha_subida'

    fieldsets = (
        ('Información Básica', {
            'fields': ('titulo', 'descripcion', 'tipo_archivo', 'archivo')
        }),
        ('Relaciones', {
            'fields': ('paciente', 'consulta')
        }),
        ('Fechas', {
            'fields': ('fecha_estudio', 'fecha_subida')
        }),
        ('Metadatos', {
            'fields': ('subido_por', 'es_urgente')
        }),
    )

    def save_model(self, request, obj, form, change):
        """Asignar el usuario actual al archivo si no tiene uno"""
        if not obj.subido_por:
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)
