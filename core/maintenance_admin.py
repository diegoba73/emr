"""Consola de mantenimiento por rol admin, independiente de las restricciones operativas."""
from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.db import models, transaction

from auditoria.audit_service import log_create, log_event, log_update
from auditoria.snapshot import safe_model_snapshot
from core.administracion import cambiar_vigencia, es_admin_sistema

BUSINESS_APPS = {
    'usuarios', 'pacientes', 'medicos', 'turnos', 'historias_clinicas',
    'laboratorio', 'catalogos', 'archivos_medicos', 'internacion',
    'solicitudes', 'estudios', 'emr', 'auditoria',
}


def es_configuracion(model):
    meta = model._meta
    return (meta.app_label == 'catalogos' or
            meta.label_lower in {'internacion.cama', 'internacion.sector', 'internacion.tipodieta',
                                 'medicos.medico', 'medicos.especialidad', 'turnos.recurso'} or
            (meta.app_label == 'laboratorio' and any(f.name == 'activo' for f in meta.fields)) or
            meta.model_name.startswith('tipo'))


def campo_vigencia(model):
    if not es_configuracion(model):
        return None
    return next((f.name for f in model._meta.fields
                 if f.name in ('activo', 'activa') and isinstance(f, models.BooleanField)), None)


def tiene_referencias(obj):
    # Incluye FK SET_NULL: borrar la configuración tampoco debe vaciar el historial.
    for relation in obj._meta.related_objects:
        if relation.related_model._meta.auto_created:
            continue
        if relation.related_model._default_manager.filter(**{relation.field.name: obj}).exists():
            return True
    return False


class MaintenanceLoginForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        if not es_admin_sistema(user):
            raise forms.ValidationError('Esta sección es exclusiva del administrador.', code='invalid_login')


class MaintenanceSite(admin.AdminSite):
    site_header = 'Administración avanzada del EMR'
    site_title = 'Administración avanzada'
    index_title = 'Configuración y registros del sistema'
    site_url = '/dashboard'
    login_form = MaintenanceLoginForm
    index_template = 'admin/maintenance_index.html'

    def has_permission(self, request):
        return es_admin_sistema(request.user)


class MaintenancePermissions:
    def has_module_permission(self, request):
        return es_admin_sistema(request.user)

    def has_view_permission(self, request, obj=None):
        return es_admin_sistema(request.user)

    def has_add_permission(self, request):
        return es_admin_sistema(request.user) and self.model._meta.app_label != 'auditoria'

    def has_change_permission(self, request, obj=None):
        return self.has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return (self.has_change_permission(request, obj) and es_configuracion(self.model)
                and (obj is None or not tiene_referencias(obj)))

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        if not campo_vigencia(self.model):
            actions.pop('retirar', None)
            actions.pop('recuperar', None)
        return actions

    def save_model(self, request, obj, form, change):
        form._maintenance_before = safe_model_snapshot(
            self.model._default_manager.get(pk=obj.pk)) if change else None
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        kw = dict(actor=request.user, entity=form.instance, module='administracion',
                  metadata={'origen': 'administracion_avanzada',
                            'campos_modificados': list(form.changed_data)})
        if change:
            log_update(before=form._maintenance_before, **kw)
        else:
            log_create(**kw)
        if form.instance._meta.label_lower == 'internacion.sector' and not form.instance.activo:
            for cama in form.instance.camas.filter(activo=True):
                cambiar_vigencia(cama, False, request.user)

    @transaction.atomic
    def delete_model(self, request, obj):
        # Serializar con nuevas referencias FK antes de decidir un borrado físico.
        obj = self.model._default_manager.select_for_update().get(pk=obj.pk)
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied('El registro tiene historial. Retírelo de uso para conservarlo.')
        before, pk, label = safe_model_snapshot(obj), obj.pk, obj._meta.label
        obj.delete()
        log_event(action='DELETE', actor=request.user, entity_type=label, entity_id=str(pk),
                  before=before, after=None, module='administracion',
                  metadata={'origen': 'administracion_avanzada', 'sin_referencias': True})


class MaintenanceModelAdmin(MaintenancePermissions, admin.ModelAdmin):
    list_per_page = 50
    actions = ['retirar', 'recuperar']

    def get_search_fields(self, request):
        return tuple(f.name for f in self.model._meta.fields if f.name in (
            'nombre', 'apellido', 'codigo', 'numero', 'dni', 'username', 'titulo'))

    def get_list_display(self, request):
        campo = campo_vigencia(self.model)
        return ('__str__', campo) if campo else ('__str__',)

    def get_list_filter(self, request):
        campo = campo_vigencia(self.model)
        return (campo,) if campo else ()

    def get_readonly_fields(self, request, obj=None):
        if self.model._meta.app_label == 'auditoria':
            return tuple(f.name for f in self.model._meta.fields)
        return tuple(f.name for f in self.model._meta.fields if not f.editable)

    @admin.action(description='Retirar de uso (conservar historial)')
    @transaction.atomic
    def retirar(self, request, queryset):
        for obj in queryset:
            cambiar_vigencia(obj, False, request.user)
        self.message_user(request, 'Registros retirados. Se conservó el historial.', messages.SUCCESS)

    @admin.action(description='Recuperar registros retirados')
    @transaction.atomic
    def recuperar(self, request, queryset):
        for obj in queryset:
            cambiar_vigencia(obj, True, request.user)
        self.message_user(request, 'Registros recuperados.', messages.SUCCESS)


class MaintenanceUserAdmin(MaintenancePermissions, UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('EMR', {'fields': ('rol', 'telefono')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('EMR', {'fields': ('rol',)}),)


maintenance_site = MaintenanceSite(name='maintenance')
for model in apps.get_models():
    if model._meta.app_label not in BUSINESS_APPS or model._meta.proxy:
        continue
    model_admin = MaintenanceUserAdmin if model._meta.label_lower == 'usuarios.user' else MaintenanceModelAdmin
    if model_admin is MaintenanceModelAdmin:
        model_admin = type(f'{model.__name__}MaintenanceAdmin', (model_admin,), {
            'raw_id_fields': tuple(f.name for f in (*model._meta.fields, *model._meta.many_to_many)
                                   if isinstance(f, (models.ForeignKey, models.ManyToManyField))),
        })
    maintenance_site.register(model, model_admin)
