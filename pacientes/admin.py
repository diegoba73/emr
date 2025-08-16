from django.contrib import admin
from .models import Paciente

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'dni', 'get_nombre', 'get_apellido', 'get_email', 'fecha_registro')
    list_filter = ('fecha_registro', 'user__profile__genero')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'dni')
    readonly_fields = ('fecha_registro', 'ultima_actualizacion')
    
    fieldsets = (
        ('Usuario del Sistema', {
            'fields': ('user',)
        }),
        ('Información de Identificación', {
            'fields': ('dni',)
        }),
        ('Información Médica', {
            'fields': ('antecedentes_personales', 'antecedentes_familiares'),
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