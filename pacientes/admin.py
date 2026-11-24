from django.contrib import admin

from .models import ObraSocial, Paciente, PacienteAfiliacion, ProblemaClinico


@admin.register(ObraSocial)
class ObraSocialAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')


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
    inlines = []

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
                "fields": ("obra_social", "numero_afiliado", "plan_obra_social"),
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


class PacienteAfiliacionInline(admin.TabularInline):
    model = PacienteAfiliacion
    extra = 0
    fields = ("obra_social", "numero_afiliado", "plan", "es_principal", "activo")


class ProblemaClinicoInline(admin.TabularInline):
    model = ProblemaClinico
    extra = 0
    fields = ("texto", "diagnostico_cie", "estado", "es_principal", "notas")
    readonly_fields = ()
    show_change_link = True


PacienteAdmin.inlines = [PacienteAfiliacionInline, ProblemaClinicoInline]


@admin.register(PacienteAfiliacion)
class PacienteAfiliacionAdmin(admin.ModelAdmin):
    list_display = ("paciente", "obra_social", "numero_afiliado", "plan", "es_principal", "activo")
    list_filter = ("es_principal", "activo", "obra_social")
    search_fields = (
        "obra_social__codigo",
        "obra_social__nombre",
        "numero_afiliado",
        "plan",
        "paciente__dni",
        "paciente__apellido",
    )
    raw_id_fields = ("obra_social",)


@admin.register(ProblemaClinico)
class ProblemaClinicoAdmin(admin.ModelAdmin):
    list_display = ("paciente", "texto", "estado", "es_principal", "actualizado_en")
    list_filter = ("estado", "es_principal")
    search_fields = ("texto", "paciente__dni", "paciente__apellido")
    raw_id_fields = ("paciente", "diagnostico_cie", "creado_por", "modificado_por")
