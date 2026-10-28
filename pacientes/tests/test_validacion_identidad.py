"""Tests unitarios de validacion_identidad (sin DB)."""
from pacientes.validacion_identidad import dni_dudoso, nombre_o_apellido_valido


def test_nombre_simbolos_y_abreviaturas_invalidos():
    assert not nombre_o_apellido_valido(".")
    assert not nombre_o_apellido_valido("...")
    assert not nombre_o_apellido_valido("---")
    assert not nombre_o_apellido_valido("A")
    assert not nombre_o_apellido_valido("D")
    assert not nombre_o_apellido_valido("d.d.")
    assert not nombre_o_apellido_valido("D.D.")
    assert not nombre_o_apellido_valido("J.")
    assert not nombre_o_apellido_valido("Jose-Luis")
    assert not nombre_o_apellido_valido("O'Connor")
    assert not nombre_o_apellido_valido("Juan3")
    assert not nombre_o_apellido_valido("D ARMANDO")  # letra suelta


def test_nombre_real_valido():
    assert nombre_o_apellido_valido("Juan")
    assert nombre_o_apellido_valido("  maría  ")
    assert nombre_o_apellido_valido("Ñoño")
    assert nombre_o_apellido_valido("DIEGO")
    assert nombre_o_apellido_valido("DIEGO ARMANDO")
    assert nombre_o_apellido_valido("BAULDE")
    assert nombre_o_apellido_valido("DE LA CRUZ")


def test_dni_placeholders():
    assert dni_dudoso("11111")
    assert dni_dudoso("12345")
    assert dni_dudoso("00000000")
    assert dni_dudoso("999999")


def test_dni_real_ok():
    assert not dni_dudoso("30111222")
    assert not dni_dudoso("12.345.678")
    assert not dni_dudoso("AB123456")
