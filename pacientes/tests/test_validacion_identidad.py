"""Tests unitarios de validacion_identidad (sin DB)."""
from pacientes.validacion_identidad import dni_dudoso, nombre_o_apellido_valido


def test_nombre_punto_invalido():
    assert not nombre_o_apellido_valido(".")
    assert not nombre_o_apellido_valido("...")
    assert not nombre_o_apellido_valido("---")
    assert not nombre_o_apellido_valido("A")


def test_nombre_real_valido():
    assert nombre_o_apellido_valido("Juan")
    assert nombre_o_apellido_valido("  maría  ")
    assert nombre_o_apellido_valido("Ñoño")


def test_dni_placeholders():
    assert dni_dudoso("11111")
    assert dni_dudoso("12345")
    assert dni_dudoso("00000000")
    assert dni_dudoso("999999")


def test_dni_real_ok():
    assert not dni_dudoso("30111222")
    assert not dni_dudoso("12.345.678")
    assert not dni_dudoso("AB123456")
