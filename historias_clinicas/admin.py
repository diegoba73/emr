from django.contrib import admin
from django import forms
from .models import HistoriaClinica, Consulta, Sintoma, Diagnostico, Tratamiento, Prescripcion

# --- INLINE ADMINS (PARA ANIDAR EN CONSULTA) ---
class DiagnosticoInline(admin.TabularInline): # O admin.TabularInline para un formato de tabla
    model = Diagnostico
    extra = 0
    fields = ['diagnostico_cie', 'nombre_diagnostico', 'descripcion_diagnostico', 'sintomas_asociados']

class TratamientoInline(admin.TabularInline): # O admin.TabularInline para un formato de tabla
    model = Tratamiento
    extra = 0
    fields = ['tipo_tratamiento', 'descripcion_tratamiento', 'dosis_frecuencia', 'fecha_inicio', 'fecha_fin_estimada']

class PrescripcionInline(admin.TabularInline):
    model = Prescripcion
    extra = 0
    fields = ['medicamento', 'dosis', 'frecuencia', 'duracion', 'instrucciones', 'activa']

# --- Personalización de Widgets para el Formulario de Consulta ---
class ConsultaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = '__all__'
        widgets = {
            'fecha_hora_consulta': forms.SplitDateTimeWidget(
                date_attrs={'type': 'date'},
                time_attrs={'type': 'time'}
            ),
        }

# --- Clases de Administración ---
@admin.register(HistoriaClinica)
class HistoriaClinicaAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'fecha_creacion', 'ultima_actualizacion']
    search_fields = ['paciente__nombre', 'paciente__apellido', 'paciente__dni']
    readonly_fields = ['fecha_creacion', 'ultima_actualizacion']

@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    form = ConsultaForm
    list_display = ['historia_clinica', 'medico', 'fecha_hora_consulta', 'motivo_consulta_detalle']
    list_filter = ['fecha_hora_consulta', 'medico']
    search_fields = ['historia_clinica__paciente__nombre', 'historia_clinica__paciente__apellido', 'medico__nombre']
    readonly_fields = ['fecha_registro', 'ultima_actualizacion']
    inlines = [DiagnosticoInline, TratamientoInline, PrescripcionInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('historia_clinica', 'medico', 'turno', 'fecha_hora_consulta')
        }),
        ('Motivo de Consulta', {
            'fields': ('motivo_consulta_detalle',)
        }),
        ('Evaluación Clínica', {
            'fields': ('anamnesis', 'examen_fisico', 'diagnostico_presuntivo')
        }),
        ('Plan de Manejo', {
            'fields': ('plan_manejo', 'notas_medicas')
        }),
        ('Metadatos', {
            'fields': ('fecha_registro', 'ultima_actualizacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Sintoma)
class SintomaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre']
    ordering = ['nombre']


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ['consulta', 'diagnostico_cie', 'nombre_diagnostico', 'fecha_diagnostico']
    list_filter = ['fecha_diagnostico', 'diagnostico_cie__categoria']
    search_fields = ['nombre_diagnostico', 'diagnostico_cie__codigo', 'diagnostico_cie__descripcion']
    filter_horizontal = ['sintomas_asociados']


@admin.register(Tratamiento)
class TratamientoAdmin(admin.ModelAdmin):
    list_display = ['consulta', 'tipo_tratamiento', 'descripcion_tratamiento', 'fecha_registro']
    list_filter = ['tipo_tratamiento', 'fecha_registro']
    search_fields = ['descripcion_tratamiento', 'consulta__historia_clinica__paciente__nombre']


@admin.register(Prescripcion)
class PrescripcionAdmin(admin.ModelAdmin):
    list_display = ['consulta', 'medicamento', 'dosis', 'frecuencia', 'activa', 'fecha_prescripcion']
    list_filter = ['activa', 'fecha_prescripcion', 'medicamento__via_administracion']
    search_fields = ['medicamento__nombre', 'consulta__historia_clinica__paciente__nombre']
    readonly_fields = ['fecha_prescripcion']