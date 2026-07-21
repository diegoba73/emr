"""
Admin panel para la app laboratorio.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    TipoMuestra,
    TipoExamen,
    PanelExamen,
    SolicitudExamen,
    ResultadoExamen,
    AreaLaboratorio,
    SeccionLaboratorio,
    TipoContenedor,
    Muestra,
    EventoMuestra,
)


@admin.register(AreaLaboratorio)
class AreaLaboratorioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(SeccionLaboratorio)
class SeccionLaboratorioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "area", "activo")
    list_filter = ("area", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(TipoContenedor)
class TipoContenedorAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    search_fields = ("codigo", "nombre")


class EventoMuestraInline(admin.TabularInline):
    model = EventoMuestra
    extra = 0
    readonly_fields = ("accion", "estado_anterior", "estado_nuevo", "actor", "fecha", "metadata", "request_id")
    can_delete = False


@admin.register(Muestra)
class MuestraAdmin(admin.ModelAdmin):
    list_display = ("codigo_barra", "solicitud", "paciente", "estado", "tipo_muestra", "created_at")
    list_filter = ("estado",)
    search_fields = ("codigo_barra", "solicitud__numero")
    readonly_fields = ("codigo_barra", "created_at", "updated_at")
    inlines = [EventoMuestraInline]


@admin.register(TipoMuestra)
class TipoMuestraAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'color_tubo', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')
    ordering = ('nombre',)


@admin.register(TipoExamen)
class TipoExamenAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'abreviatura', 'tipo_muestra_requerida', 'tipo_contenedor', 'metodo', 'unidad_default', 'precio', 'activo')
    list_filter = ('activo', 'tipo_muestra_requerida', 'tipo_contenedor')
    search_fields = ('codigo', 'nombre', 'abreviatura')
    autocomplete_fields = ('tipo_muestra_requerida', 'tipo_contenedor')
    ordering = ('nombre',)


@admin.register(PanelExamen)
class PanelExamenAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'get_tipos_examen_count', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')
    filter_horizontal = ('tipos_examen',)
    ordering = ('nombre',)

    def get_tipos_examen_count(self, obj):
        """Muestra la cantidad de tipos de examen en el panel"""
        return obj.tipos_examen.count()
    get_tipos_examen_count.short_description = 'Cantidad de Exámenes'


@admin.register(SolicitudExamen)
class SolicitudExamenAdmin(admin.ModelAdmin):
    list_display = (
        'numero',
        'paciente',
        'medico_display',
        'origen_solicitud',
        'estado',
        'fecha_solicitud',
        'fecha_entrega_prometida',
    )
    list_filter = ('estado', 'origen_solicitud', 'fecha_solicitud')
    search_fields = (
        'numero',
        'paciente__nombre',
        'paciente__apellido',
        'paciente__dni',
        'medico_interno__nombre',
        'medico_interno__apellido',
        'medico_externo_nombre',
    )
    readonly_fields = ('numero', 'fecha_solicitud')
    filter_horizontal = ('tipos_examen', 'paneles')
    date_hierarchy = 'fecha_solicitud'

    fieldsets = (
        ('Información Básica', {
            'fields': (
                'numero',
                'paciente',
                'origen_solicitud',
                'estado',
            )
        }),
        ('Médico (Híbrido)', {
            'fields': (
                'medico_interno',
                'medico_externo_nombre',
            ),
            'description': 'Médico interno (del EMR) o externo (papel)'
        }),
        ('Exámenes Solicitados', {
            'fields': (
                'tipos_examen',
                'paneles',
            )
        }),
        ('Fechas', {
            'fields': (
                'fecha_solicitud',
                'fecha_entrega_prometida',
            )
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )

    def medico_display(self, obj):
        """
        Muestra claramente si es médico interno o externo.
        """
        if obj.medico_interno:
            return format_html(
                '<span style="color: green;">✓ Interno:</span> {}',
                obj.medico_interno.nombre_completo
            )
        elif obj.medico_externo_nombre:
            return format_html(
                '<span style="color: orange;">📄 Externo:</span> {}',
                obj.medico_externo_nombre
            )
        return format_html('<span style="color: red;">Sin médico</span>')
    medico_display.short_description = 'Médico'


@admin.register(ResultadoExamen)
class ResultadoExamenAdmin(admin.ModelAdmin):
    list_display = (
        'solicitud',
        'tipo_examen',
        'valor_obtenido',
        'es_patologico',
        'validado_por',
        'fecha_validacion',
    )
    list_filter = ('es_patologico', 'fecha_validacion', 'tipo_examen')
    search_fields = (
        'solicitud__numero',
        'solicitud__paciente__nombre',
        'solicitud__paciente__apellido',
        'tipo_examen__nombre',
        'valor_obtenido',
    )
    readonly_fields = ('fecha_validacion',)
    autocomplete_fields = ('solicitud', 'tipo_examen', 'validado_por')

    fieldsets = (
        ('Información Básica', {
            'fields': (
                'solicitud',
                'tipo_examen',
            )
        }),
        ('Resultado', {
            'fields': (
                'valor_obtenido',
                'es_patologico',
            )
        }),
        ('Validación', {
            'fields': (
                'validado_por',
                'fecha_validacion',
            )
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )



