from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import TipoExamen, PanelExamen, SolicitudExamen, ResultadoExamen


@admin.register(TipoExamen)
class TipoExamenAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'precio', 'activo']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['nombre']


@admin.register(PanelExamen)
class PanelExamenAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'precio', 'activo', 'mostrar_examenes']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    filter_horizontal = ['examenes']
    ordering = ['nombre']

    def mostrar_examenes(self, obj):
        examenes = obj.examenes.all()[:5]  # Mostrar solo los primeros 5
        nombres = [examen.nombre for examen in examenes]
        if obj.examenes.count() > 5:
            nombres.append(f"... y {obj.examenes.count() - 5} más")
        return ", ".join(nombres)
    mostrar_examenes.short_description = "Exámenes del Panel"


class ResultadoExamenInline(admin.TabularInline):
    model = ResultadoExamen
    extra = 0
    readonly_fields = ['fecha_resultado']
    fields = [
        'tipo_examen', 
        'valor_numerico', 
        'valor_texto', 
        'unidad',
        'valor_normal_min', 
        'valor_normal_max', 
        'valor_normal_texto',
        'es_normal', 
        'interpretacion_ia',
        'observaciones', 
        'tecnico',
        'validado_por'
    ]


@admin.register(SolicitudExamen)
class SolicitudExamenAdmin(admin.ModelAdmin):
    list_display = ['numero', 'paciente', 'medico', 'estado', 'fecha_solicitud', 'total', 'ver_resultados']
    list_filter = ['estado', 'fecha_solicitud']
    search_fields = ['numero', 'paciente__nombre', 'paciente__apellido', 'medico__nombre']
    readonly_fields = ['numero', 'fecha_solicitud', 'total']
    filter_horizontal = ['examenes_individuales', 'paneles']
    inlines = [ResultadoExamenInline]
    date_hierarchy = 'fecha_solicitud'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero', 'paciente', 'medico', 'consulta')
        }),
        ('Exámenes', {
            'fields': ('examenes_individuales', 'paneles')
        }),
        ('Estado y Fechas', {
            'fields': ('estado', 'fecha_solicitud', 'fecha_entrega')
        }),
        ('Información Adicional', {
            'fields': ('observaciones', 'total'),
            'classes': ('collapse',)
        }),
    )

    def ver_resultados(self, obj):
        if obj.resultadoexamen_set.exists():
            url = reverse('admin:laboratorio_resultadoexamen_changelist') + f'?solicitud__id__exact={obj.id}'
            return format_html('<a href="{}">Ver Resultados</a>', url)
        return "Sin resultados"
    ver_resultados.short_description = "Resultados"

    def save_model(self, request, obj, form, change):
        try:
            # Calcular total antes de guardar
            obj.total = obj.calcular_total()
            super().save_model(request, obj, form, change)
        except Exception as e:
            # Si hay error al calcular el total, guardar con total 0
            obj.total = 0
            super().save_model(request, obj, form, change)


@admin.register(ResultadoExamen)
class ResultadoExamenAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'tipo_examen', 'valor_numerico', 'valor_texto', 'es_normal', 'fecha_resultado', 'tecnico']
    list_filter = ['es_normal', 'fecha_resultado', 'tipo_examen']
    search_fields = ['solicitud__numero', 'tipo_examen__nombre', 'tecnico']
    readonly_fields = ['fecha_resultado']
    date_hierarchy = 'fecha_resultado'
    
    fieldsets = (
        ('Información de la Solicitud', {
            'fields': ('solicitud', 'tipo_examen')
        }),
        ('Resultado', {
            'fields': ('valor_numerico', 'valor_texto', 'unidad', 'valor_normal_min', 'valor_normal_max', 'valor_normal_texto', 'es_normal')
        }),
        ('Análisis', {
            'fields': ('interpretacion_ia', 'observaciones')
        }),
        ('Responsables', {
            'fields': ('tecnico', 'validado_por', 'fecha_resultado'),
            'classes': ('collapse',)
        }),
    )