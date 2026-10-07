from django.contrib import admin

from .models import Profesional


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ['matricula', 'apellido', 'nombre', 'especialidad']
    list_filter = ('especialidad', 'fecha_registro')
    search_fields = (
        'nombre',
        'apellido',
        'matricula',
        'especialidad__nombre',
        'user__username',
        'user__email',
    )
    readonly_fields = ('fecha_registro', 'ultima_actualizacion')
