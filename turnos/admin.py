from django.contrib import admin
from django import forms
from .models import Turno

class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = '__all__'
        widgets = {
            'fecha_hora': forms.SplitDateTimeWidget(
                date_attrs={'type': 'date'},
                time_attrs={'type': 'time'}
            ),
            'fecha_hora_inicio': forms.SplitDateTimeWidget(
                date_attrs={'type': 'date'},
                time_attrs={'type': 'time'}
            ),
            'fecha_hora_fin': forms.SplitDateTimeWidget(
                date_attrs={'type': 'date'},
                time_attrs={'type': 'time'}
            ),
        }

class TurnoAdmin(admin.ModelAdmin):
    form = TurnoForm
    list_display = (
        'paciente', 'medico', 'especialidad',
        'fecha_hora', 'estado'
    )
    list_filter = ('estado', 'especialidad', 'medico')
    search_fields = (
        'paciente__nombre', 'paciente__apellido',
        'medico__nombre', 'medico__apellido',
        'motivo_consulta'
    )
    date_hierarchy = 'fecha_hora'
    autocomplete_fields = ('paciente', 'medico', 'especialidad')

admin.site.register(Turno, TurnoAdmin)