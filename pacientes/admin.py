from django.contrib import admin

from .models import Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    """Admin de ``Paciente`` alineado con el modelo: los datos personales
    viven en la propia ficha y se exponen como campos editables. La relación
    con ``User`` queda como vínculo opcional, no como fuente de verdad.

    La eliminación física está deshabilitada (identidad clínica longitudinal).
    La baja lógica / soft-delete se resolverá en una fase posterior.
    """

    list_display = ("dni", "apellido", "nombre", "fecha_registro")
    list_filter = ("fecha_registro", "sexo")
    search_fields = ("dni", "apellido", "nombre")
    readonly_fields = (
        "fecha_registro",
        "ultima_actualizacion",
        "creado_por",
        "modificado_por",
    )

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
                "fields": (
                    "fecha_registro",
                    "ultima_actualizacion",
                    "creado_por",
                    "modificado_por",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
