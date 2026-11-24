"""Helpers de test para catálogo ObraSocial."""
from pacientes.obras_sociales import ensure_seed_obras_sociales, resolve_obra_social


def os_ref(codigo: str):
    ensure_seed_obras_sociales()
    obj = resolve_obra_social(codigo)
    assert obj is not None, f'Obra social no seed: {codigo}'
    return obj
