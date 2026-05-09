from django.contrib import admin

from .models import Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    """Admin de ``Paciente`` alineado con el modelo: los datos personales
    viven en la propia ficha y se exponen como campos editables. La relación
    con ``User`` queda como vínculo opcional, no como fuente de verdad.
    """

    list_display = ("dni", "apellido", "nombre", "fecha_registro")
    list_filter = ("fecha_registro", "sexo")
    search_fields = ("dni", "apellido", "nombre")
    readonly_fields = ("fecha_registro", "ultima_actualizacion")

    fieldsets = (
        (
            "Vínculo con Usuario del Sistema",
            {"fields": ("user",)},
        ),
        (
            "Identificación",
            {"fields": ("dni", "apellido", "nombre", "fecha_nacimiento", "sexo")},
        ),
        (
            "Contacto",
            {"fields": ("telefono", "email", "direccion")},
        ),
        (
            "Obra Social",
            {
                "fields": ("obra_social", "numero_afiliado"),
                "classes": ("collapse",),
            },
        ),
        (
            "Información Médica",
            {
                "fields": (
                    "antecedentes_personales",
                    "antecedentes_familiares",
                    "observaciones",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("fecha_registro", "ultima_actualizacion"),
                "classes": ("collapse",),
            },
        ),
    )
