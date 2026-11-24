import pytest

from pacientes.obras_sociales import ensure_seed_obras_sociales


@pytest.fixture(autouse=True)
def _seed_obras_sociales(db):
    ensure_seed_obras_sociales()
