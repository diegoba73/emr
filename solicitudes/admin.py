from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Solicitud

@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'paciente', 
        'tipo_solicitud', 
        'estado', 
        'prioridad', 
        'medico_solicitante',
        'fecha_solicitud', 
        'dias_pendiente_display',
        'lims_status'
    ]
    
    list_filter = [
        'estado',
        'tipo_solicitud',
        'prioridad',
        'sincronizado_lims',
        'fecha_solicitud',
        'medico_solicitante',
    ]
    
    search_fields = [
        'paciente__nombre',
        'paciente__apellido',
        'paciente__dni',
        'medico_solicitante__nombre',
        'medico_solicitante__apellido',
        'descripcion',
        'observaciones',
        'lims_id',
    ]
    
    readonly_fields = [
        'fecha_creacion',
        'fecha_modificacion',
        'ultima_sincronizacion',
        'dias_pendiente_display',
        'esta_vencida_display',
        'medicos_asignados_display',
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'paciente', 
                'medico_solicitante', 
                'medicos_asignados',
                'tipo_solicitud',
                'descripcion',
                'observaciones'
            )
        }),
        ('Estado y Prioridad', {
            'fields': (
                'estado',
                'prioridad',
                'fecha_limite',
                'fecha_completada'
            )
        }),
        ('Integración LIMS', {
            'fields': (
                'lims_id',
                'sincronizado_lims',
                'ultima_sincronizacion',
            ),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': (
                'creado_por',
                'modificado_por',
                'fecha_creacion',
                'fecha_modificacion',
            ),
            'classes': ('collapse',)
        }),
        ('Información Adicional', {
            'fields': (
                'dias_pendiente_display',
                'esta_vencida_display',
                'medicos_asignados_display',
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'marcar_como_completadas',
        'marcar_como_canceladas',
        'marcar_como_en_proceso',
        'reabrir_solicitudes',
    ]
    
    def dias_pendiente_display(self, obj):
        """Muestra los días pendiente con formato"""
        dias = obj.dias_pendiente
        if dias == 0:
            return "Hoy"
        elif dias == 1:
            return "1 día"
        else:
            return f"{dias} días"
    dias_pendiente_display.short_description = "Días Pendiente"
    
    def esta_vencida_display(self, obj):
        """Muestra si está vencida con formato"""
        if obj.esta_vencida:
            return format_html('<span style="color: red;">VENCIDA</span>')
        return format_html('<span style="color: green;">En tiempo</span>')
    esta_vencida_display.short_description = "Estado de Vencimiento"
    
    def medicos_asignados_display(self, obj):
        """Muestra los médicos asignados"""
        return obj.get_medicos_asignados_display()
    medicos_asignados_display.short_description = "Médicos Asignados"
    
    def lims_status(self, obj):
        """Muestra el estado de sincronización con LIMS"""
        if obj.sincronizado_lims:
            return format_html(
                '<span style="color: green;">✓ Sincronizado</span>'
            )
        elif obj.lims_id:
            return format_html(
                '<span style="color: orange;">⚠ Parcial</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ No sincronizado</span>'
            )
    lims_status.short_description = "Estado LIMS"
    
    def get_queryset(self, request):
        """Optimiza las consultas con select_related y prefetch_related"""
        return super().get_queryset(request).select_related(
            'paciente', 
            'medico_solicitante', 
            'creado_por', 
            'modificado_por'
        ).prefetch_related('medicos_asignados')
    
    def save_model(self, request, obj, form, change):
        """Guarda información de auditoría"""
        if not change:  # Es una nueva solicitud
            obj.creado_por = request.user
        obj.modificado_por = request.user
        super().save_model(request, obj, form, change)
    
    # Acciones personalizadas
    def marcar_como_completadas(self, request, queryset):
        """Marca las solicitudes seleccionadas como completadas"""
        updated = queryset.update(estado='COMPLETADA')
        self.message_user(
            request, 
            f'{updated} solicitud(es) marcada(s) como completada(s).'
        )
    marcar_como_completadas.short_description = "Marcar como completadas"
    
    def marcar_como_canceladas(self, request, queryset):
        """Marca las solicitudes seleccionadas como canceladas"""
        updated = queryset.update(estado='CANCELADA')
        self.message_user(
            request, 
            f'{updated} solicitud(es) marcada(s) como cancelada(s).'
        )
    marcar_como_canceladas.short_description = "Marcar como canceladas"
    
    def marcar_como_en_proceso(self, request, queryset):
        """Marca las solicitudes seleccionadas como en proceso"""
        updated = queryset.update(estado='EN_PROCESO')
        self.message_user(
            request, 
            f'{updated} solicitud(es) marcada(s) como en proceso.'
        )
    marcar_como_en_proceso.short_description = "Marcar como en proceso"
    
    def reabrir_solicitudes(self, request, queryset):
        """Reabre las solicitudes canceladas o completadas"""
        updated = 0
        for solicitud in queryset:
            if solicitud.estado in ['CANCELADA', 'COMPLETADA']:
                solicitud.reabrir()
                updated += 1
        
        self.message_user(
            request, 
            f'{updated} solicitud(es) reabierta(s).'
        )
    reabrir_solicitudes.short_description = "Reabrir solicitudes"
    
    class Media:
        css = {
            'all': ('admin/css/solicitudes.css',)
        }
        js = ('admin/js/solicitudes.js',)
