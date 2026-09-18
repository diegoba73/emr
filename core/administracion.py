"""Capacidad administrativa y retiro de configuración conservando relaciones."""
from django.db import transaction
from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot


def es_admin_sistema(user):
    return bool(user and user.is_authenticated and user.is_active and (
        user.is_superuser or str(getattr(user, 'rol', '')).lower() == 'admin'
    ))


@transaction.atomic
def cambiar_vigencia(instance, activo, actor):
    """Solo configuración con bandera de vigencia; nunca elimina objetos relacionados."""
    if not es_admin_sistema(actor):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('Solo el administrador puede retirar o recuperar registros.')
    field = 'activo' if hasattr(instance, 'activo') else 'activa'
    before = safe_model_snapshot(instance)
    setattr(instance, field, activo)
    instance.save(update_fields=[field])
    log_update(actor=actor, entity=instance, before=before, module='administracion',
               metadata={'accion': 'recuperar' if activo else 'retirar'})
    if instance._meta.label_lower == 'internacion.sector' and not activo:
        for cama in instance.camas.filter(activo=True):
            cambiar_vigencia(cama, False, actor)
