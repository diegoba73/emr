"""Gate de seed_data cuando DEBUG=False."""
from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_seed_data_bloqueado_sin_force_unsafe_si_debug_false():
    with pytest.raises(CommandError, match='DEBUG=False'):
        call_command('seed_data', stdout=StringIO())


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_seed_data_permite_force_unsafe_con_debug_false():
    # Smoke: no debe lanzar CommandError de gate (puede fallar luego por deps;
    # el gate se valida por ausencia de ese error al inicio).
    out = StringIO()
    try:
        call_command('seed_data', '--force-unsafe', stdout=out)
    except CommandError as exc:
        assert 'DEBUG=False' not in str(exc)
        raise
