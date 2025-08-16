from django.contrib import admin
from .models import Medico, Especialidad

@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre', 'descripcion')
    ordering = ('nombre',)

@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ('user', 'matricula', 'especialidad', 'get_nombre', 'get_apellido', 'get_email', 'fecha_registro')
    list_filter = ('especialidad', 'fecha_registro')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'matricula')
    readonly_fields = ('fecha_registro', 'ultima_actualizacion')
    
    fieldsets = (
        ('Usuario del Sistema', {
            'fields': ('user',)
        }),
        ('Información Profesional', {
            'fields': ('matricula', 'especialidad')
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
    
    def get_nombre(self, obj):
        return obj.nombre
    get_nombre.short_description = 'Nombre'
    
    def get_apellido(self, obj):
        return obj.apellido
    get_apellido.short_description = 'Apellido'
    
    def get_email(self, obj):
        return obj.email
    get_email.short_description = 'Email'