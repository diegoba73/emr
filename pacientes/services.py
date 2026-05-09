"""
Lógica de negocio para ficha de paciente y usuario.
"""
import logging
from typing import Optional

from django.db import transaction

from .models import Paciente

logger = logging.getLogger(__name__)


def ensure_paciente_linked_to_user(user) -> Optional[Paciente]:
    """
    Resuelve el registro Paciente asociado al User (rol paciente).
    Si no existe la relación OneToOne, intenta vincular un Paciente con user=NULL:
    - email igual al del usuario (iexact) y un solo candidato
    - o DNI igual al username (usuarios cuyo login es el DNI)
    """
    if (getattr(user, "rol", "") or "").lower() != "paciente":
        return None

    try:
        return user.paciente
    except Paciente.DoesNotExist:
        pass

    def link_paciente(p: Paciente) -> Optional[Paciente]:
        with transaction.atomic():
            locked = Paciente.objects.select_for_update().get(pk=p.pk)
            if locked.user_id is not None and locked.user_id != user.id:
                logger.warning(
                    "Paciente %s ya vinculado a otro usuario; no se reasigna",
                    locked.id,
                )
                return None
            if locked.user_id == user.id:
                return locked
            if locked.user_id is None:
                locked.user = user
                locked.save(update_fields=["user_id"])
        return Paciente.objects.get(user=user)

    email = (getattr(user, "email", None) or "").strip()
    if email:
        qs = Paciente.objects.filter(user__isnull=True, email__iexact=email)
        n = qs.count()
        if n == 1:
            p = qs.first()
            if p is None:
                return None
            logger.info("Vinculando Paciente %s a User %s por email", p.id, user.id)
            return link_paciente(p) or None
        if n > 1:
            logger.warning(
                "Varios pacientes con email %s sin usuario: no se auto-vincula", email
            )

    uname = (getattr(user, "username", None) or "").strip()
    if uname and uname.isdigit():
        p = (
            Paciente.objects.filter(dni=uname, user__isnull=True)
            .order_by("id")
            .first()
        )
        if p:
            logger.info("Vinculando Paciente %s a User %s por DNI=username", p.id, user.id)
            return link_paciente(p) or None

    return None
