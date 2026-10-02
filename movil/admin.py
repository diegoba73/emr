from django.contrib import admin

from .models import FavoritoLabMedico, PaqueteLabContexto


@admin.register(PaqueteLabContexto)
class PaqueteLabContextoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'contexto', 'activo', 'orden')
    list_filter = ('contexto', 'activo')
    search_fields = ('codigo', 'nombre', 'descripcion')
    filter_horizontal = ('paneles', 'examenes')
    ordering = ('contexto', 'orden', 'nombre')


@admin.register(FavoritoLabMedico)
class FavoritoLabMedicoAdmin(admin.ModelAdmin):
    list_display = ('medico', 'panel', 'tipo_examen', 'orden')
    list_filter = ('medico',)
    search_fields = (
        'medico__apellido',
        'medico__nombre',
        'panel__codigo',
        'panel__nombre',
        'tipo_examen__codigo',
        'tipo_examen__nombre',
    )
    raw_id_fields = ('medico', 'panel', 'tipo_examen')
