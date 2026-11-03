from django.contrib import admin

from .models import CoberturaRecepcion, LlegadaRecepcion, PuestoRecepcion, ReglaRuteoRecepcion


@admin.register(PuestoRecepcion)
class PuestoRecepcionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'modo', 'activo', 'es_fallback', 'orden')
    list_filter = ('activo', 'modo', 'es_fallback')
    search_fields = ('codigo', 'nombre')


@admin.register(CoberturaRecepcion)
class CoberturaRecepcionAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha', 'puesto', 'tipos', 'sede')
    list_filter = ('fecha', 'sede', 'puesto')
    search_fields = ('usuario__username', 'usuario__email')
    raw_id_fields = ('usuario', 'puesto')


@admin.register(ReglaRuteoRecepcion)
class ReglaRuteoRecepcionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'puesto', 'tipo_actividad', 'tipo_recurso', 'prioridad', 'activo')
    list_filter = ('activo', 'tipo_actividad', 'puesto')
    search_fields = ('nombre',)


@admin.register(LlegadaRecepcion)
class LlegadaRecepcionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'fecha',
        'paciente',
        'puesto',
        'tipo_actividad',
        'estado_flujo',
        'numero_orden_dia',
        'checkin_en',
    )
    list_filter = ('fecha', 'puesto', 'estado_flujo', 'tipo_actividad')
    search_fields = ('paciente__apellido', 'paciente__dni', 'paciente__nombre')
    raw_id_fields = ('paciente', 'turno', 'puesto', 'destino_recurso')
