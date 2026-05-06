"""
Señales Django para la app usuarios.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def crear_user_profile(sender, instance, created, **kwargs):
    """
    Señal que crea automáticamente un UserProfile cuando se crea un nuevo User.
    
    Args:
        sender: La clase del modelo (User)
        instance: La instancia del User que se acaba de crear/guardar
        created: Boolean que indica si la instancia fue creada (True) o solo actualizada (False)
        **kwargs: Argumentos adicionales
    """
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
            logger.info(f'Nuevo usuario creado: ID {instance.id} - Rol: {instance.rol}')
        except Exception as e:
            logger.error(f'Error creando perfil para usuario ID {instance.id}: {str(e)}', exc_info=True)




