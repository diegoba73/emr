from django.contrib import admin
from .models import Medico, Especialidad, DisponibilidadMedico, ExcepcionMedico

@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre', 'descripcion')
    ordering = ('nombre',)


class DisponibilidadMedicoInline(admin.TabularInline):
    model = DisponibilidadMedico
    extra = 1
    fields = ('dia_semana', 'hora_inicio', 'hora_fin', 'duracion_slot_min', 'activo')
    ordering = ('dia_semana', 'hora_inicio')


class ExcepcionMedicoInline(admin.TabularInline):
    model = ExcepcionMedico
    extra = 0
    fields = ('fecha', 'tipo', 'hora_inicio', 'hora_fin', 'motivo')
    ordering = ('-fecha',)


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ['matricula', 'apellido', 'especialidad']
    list_filter = ('especialidad', 'fecha_registro')
    search_fields = (
        'nombre',
        'apellido',
        'matricula',
        'especialidad__nombre',
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
    )
    readonly_fields = ('fecha_registro', 'ultima_actualizacion')
    inlines = [DisponibilidadMedicoInline, ExcepcionMedicoInline]
    
    fieldsets = (
        ('Usuario del Sistema', {
            'fields': ('user',)
        }),
        ('Información Profesional', {
            'fields': ('nombre', 'apellido', 'matricula', 'especialidad')
        }),
        ('Información Adicional', {
            'fields': ('areas_interes_ia',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'ultima_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def display_nombre(self, obj):
        return obj.nombre_completo
    display_nombre.short_description = 'Nombre'


@admin.register(DisponibilidadMedico)
class DisponibilidadMedicoAdmin(admin.ModelAdmin):
    list_display = ('medico', 'dia_semana', 'hora_inicio', 'hora_fin', 'duracion_slot_min', 'activo')
    list_filter = ('medico', 'dia_semana', 'activo')
    ordering = ('medico', 'dia_semana', 'hora_inicio')


@admin.register(ExcepcionMedico)
class ExcepcionMedicoAdmin(admin.ModelAdmin):
    list_display = ('medico', 'fecha', 'tipo', 'hora_inicio', 'hora_fin')
    list_filter = ('medico', 'tipo', 'fecha')
    ordering = ('-fecha',)