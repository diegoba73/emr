from django.contrib import admin
from django import forms
from .models import (
    Turno,
    Recurso,
    Atencion,
    ConsultaAmbulatoria,
    RegistroProcedimiento,
    RegistroQuirurgico,
)

class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = '__all__'
        widgets = {
            'fecha_hora_inicio': forms.SplitDateTimeWidget(
                date_attrs={'type': 'date'},
                time_attrs={'type': 'time'}
            ),
            'fecha_hora_fin': forms.SplitDateTimeWidget(
                date_attrs={'type': 'date'},
                time_attrs={'type': 'time'}
            ),
        }


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    form = TurnoForm
    list_display = (
        'id',
        'recurso',
        'paciente',
        'medico',
        'fecha_hora_inicio',
        'fecha_hora_fin',
        'estado',
    )
    list_filter = (
        'estado',
        'medico',
        'recurso__tipo_recurso',
        'recurso__ubicacion',
    )
    search_fields = (
        'paciente__nombre',
        'paciente__apellido',
        'medico__nombre',
        'medico__apellido',
        'motivo_reserva',
        'recurso__nombre',
    )
    date_hierarchy = 'fecha_hora_inicio'
    autocomplete_fields = ('paciente', 'medico', 'recurso')


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'tipo_recurso', 'activo')
    list_filter = ('ubicacion', 'tipo_recurso', 'activo')
    search_fields = ('nombre',)


@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'paciente',
        'medico_principal',
        'tipo_atencion',
        'estado_clinico',
        'fecha_admision',
        'fecha_cierre',
    )
    list_filter = ('estado_clinico', 'tipo_atencion', 'fecha_admision', 'fecha_cierre')
    search_fields = (
        'paciente__nombre',
        'paciente__apellido',
        'medico_principal__nombre',
        'medico_principal__apellido',
    )
    autocomplete_fields = ('paciente', 'medico_principal', 'turno')


@admin.register(ConsultaAmbulatoria)
class ConsultaAmbulatoriaAdmin(admin.ModelAdmin):
    list_display = ('atencion',)
    search_fields = (
        'atencion__paciente__nombre',
        'atencion__paciente__apellido',
        'atencion__medico_principal__nombre',
        'atencion__medico_principal__apellido',
    )
    autocomplete_fields = ('atencion',)


@admin.register(RegistroProcedimiento)
class RegistroProcedimientoAdmin(admin.ModelAdmin):
    list_display = ('atencion', 'descripcion_procedimiento')
    search_fields = (
        'atencion__paciente__nombre',
        'atencion__paciente__apellido',
        'descripcion_procedimiento',
    )
    autocomplete_fields = ('atencion',)


@admin.register(RegistroQuirurgico)
class RegistroQuirurgicoAdmin(admin.ModelAdmin):
    list_display = ('atencion', 'anestesista', 'recuento_instrumental_ok')
    list_filter = ('recuento_instrumental_ok',)
    search_fields = (
        'atencion__paciente__nombre',
        'atencion__paciente__apellido',
        'anestesista__nombre',
        'anestesista__apellido',
    )
    autocomplete_fields = ('atencion', 'anestesista')