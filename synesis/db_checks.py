"""Comprobaciones Django: una sola BD local en desarrollo."""
from django.conf import settings
from django.core.checks import Error, register

_FORBIDDEN_DB_USERS = frozenset({'synesis_user'})
_CANONICAL_LOCAL_DB = 'synesis_db'


@register()
def check_local_single_database(app_configs, **kwargs):
    """En DEBUG, bloquear credenciales/BD que impliquen otro Postgres local."""
    if not settings.DEBUG:
        return []

    db = settings.DATABASES.get('default', {})
    user = db.get('USER', '')
    name = db.get('NAME', '')
    engine = db.get('ENGINE', '')
    errors = []

    if 'postgresql' in engine and user in _FORBIDDEN_DB_USERS:
        errors.append(
            Error(
                f'DB_USER={user!r} está prohibido en desarrollo local. '
                'Usá el Postgres Docker emr_postgres con DB_USER=postgres. '
                'Ver docs/dev-start.md.',
                id='synesis.E001',
            )
        )

    if 'postgresql' in engine and name and name != _CANONICAL_LOCAL_DB:
        if not name.startswith('test_'):
            errors.append(
                Error(
                    f'DB_NAME={name!r} no es la BD única local ({_CANONICAL_LOCAL_DB}). '
                    'Mezclar bases es un riesgo de datos clínicos.',
                    id='synesis.E002',
                )
            )

    return errors
