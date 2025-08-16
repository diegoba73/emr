from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Secretaria

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil'
    fieldsets = (
        ('Información Personal', {
            'fields': ('fecha_nacimiento', 'genero', 'direccion', 'ciudad', 'codigo_postal')
        }),
        ('Información Médica', {
            'fields': ('grupo_sanguineo', 'alergias', 'medicamentos_actuales'),
            'classes': ('collapse',)
        }),
        ('Contacto de Emergencia', {
            'fields': ('contacto_emergencia_nombre', 'contacto_emergencia_telefono', 'contacto_emergencia_relacion'),
            'classes': ('collapse',)
        }),
    )

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'is_active', 'is_staff')
    list_filter = ('rol', 'is_active', 'is_staff', 'is_superuser', 'fecha_registro')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información del EMR', {
            'fields': ('rol', 'telefono', 'email_verificado', 'telefono_verificado')
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'ultima_actividad'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información del EMR', {
            'fields': ('rol', 'telefono')
        }),
    )
    
    inlines = [UserProfileInline]
    
    readonly_fields = ('fecha_registro', 'ultima_actividad')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'fecha_nacimiento', 'genero', 'ciudad', 'get_edad')
    list_filter = ('genero', 'grupo_sanguineo', 'fecha_creacion')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información Personal', {
            'fields': ('fecha_nacimiento', 'genero', 'direccion', 'ciudad', 'codigo_postal')
        }),
        ('Información Médica', {
            'fields': ('grupo_sanguineo', 'alergias', 'medicamentos_actuales')
        }),
        ('Contacto de Emergencia', {
            'fields': ('contacto_emergencia_nombre', 'contacto_emergencia_telefono', 'contacto_emergencia_relacion')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def get_edad(self, obj):
        return obj.get_edad()
    get_edad.short_description = 'Edad'

@admin.register(Secretaria)
class SecretariaAdmin(admin.ModelAdmin):
    list_display = ('user', 'legajo', 'sector', 'fecha_registro')
    list_filter = ('sector', 'fecha_registro')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'legajo')
    readonly_fields = ('fecha_registro', 'ultima_actualizacion')
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información Profesional', {
            'fields': ('legajo', 'sector')
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'ultima_actualizacion'),
            'classes': ('collapse',)
        }),
    )
