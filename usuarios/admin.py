from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.forms.models import BaseInlineFormSet

from .models import User, UserProfile, Secretaria


class UserProfileInlineFormSet(BaseInlineFormSet):
    """
    La señal ``crear_user_profile`` ya crea el perfil al guardar el User.
    En el alta del admin el inline intenta INSERT otra vez → IntegrityError.
    Si el perfil ya existe, actualizamos en lugar de crear.
    """

    def save_new(self, form, commit=True):
        parent = self.instance
        if parent and parent.pk:
            existing = UserProfile.objects.filter(user_id=parent.pk).first()
            if existing is not None:
                for name, value in form.cleaned_data.items():
                    if name in ("DELETE", "user", "id"):
                        continue
                    if hasattr(existing, name):
                        setattr(existing, name, value)
                if commit:
                    existing.save()
                form.instance = existing
                return existing
        return super().save_new(form, commit=commit)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    formset = UserProfileInlineFormSet
    can_delete = False
    max_num = 1
    extra = 1
    verbose_name_plural = "Perfil"
    fieldsets = (
        (
            "Información Personal",
            {
                "fields": (
                    "fecha_nacimiento",
                    "genero",
                    "direccion",
                    "ciudad",
                    "codigo_postal",
                )
            },
        ),
        (
            "Información Médica",
            {
                "fields": ("grupo_sanguineo", "alergias", "medicamentos_actuales"),
                "classes": ("collapse",),
            },
        ),
        (
            "Contacto de Emergencia",
            {
                "fields": (
                    "contacto_emergencia_nombre",
                    "contacto_emergencia_telefono",
                    "contacto_emergencia_relacion",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "rol",
        "is_active",
        "is_staff",
    )
    list_filter = ("rol", "is_active", "is_staff", "is_superuser", "fecha_registro")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Información del EMR",
            {
                "fields": (
                    "rol",
                    "telefono",
                    "email_verificado",
                    "telefono_verificado",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("fecha_registro", "ultima_actividad"),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Información del EMR", {"fields": ("rol", "telefono")}),
    )

    inlines = [UserProfileInline]

    readonly_fields = ("fecha_registro", "ultima_actividad")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "fecha_nacimiento", "genero", "ciudad", "get_edad")
    list_filter = ("genero", "grupo_sanguineo", "fecha_creacion")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")

    fieldsets = (
        ("Usuario", {"fields": ("user",)}),
        (
            "Información Personal",
            {
                "fields": (
                    "fecha_nacimiento",
                    "genero",
                    "direccion",
                    "ciudad",
                    "codigo_postal",
                )
            },
        ),
        (
            "Información Médica",
            {
                "fields": (
                    "grupo_sanguineo",
                    "alergias",
                    "medicamentos_actuales",
                )
            },
        ),
        (
            "Contacto de Emergencia",
            {
                "fields": (
                    "contacto_emergencia_nombre",
                    "contacto_emergencia_telefono",
                    "contacto_emergencia_relacion",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("fecha_creacion", "fecha_actualizacion"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_edad(self, obj):
        return obj.get_edad()

    get_edad.short_description = "Edad"


@admin.register(Secretaria)
class SecretariaAdmin(admin.ModelAdmin):
    list_display = ("user", "legajo", "sector", "fecha_registro")
    list_filter = ("sector", "fecha_registro")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "legajo",
    )
    readonly_fields = ("fecha_registro", "ultima_actualizacion")

    fieldsets = (
        ("Usuario", {"fields": ("user",)}),
        ("Información Profesional", {"fields": ("legajo", "sector")}),
        (
            "Auditoría",
            {
                "fields": ("fecha_registro", "ultima_actualizacion"),
                "classes": ("collapse",),
            },
        ),
    )
