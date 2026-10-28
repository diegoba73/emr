from decimal import Decimal

from django.test import SimpleTestCase

from laboratorio.valor_operador import numero_para_calculo, parse_valor_con_operador


class TestValorOperador(SimpleTestCase):
    def test_menor_que(self):
        p = parse_valor_con_operador("<0.1")
        self.assertEqual(p.operador, "<")
        self.assertEqual(p.numero, Decimal("0.1"))
        self.assertEqual(numero_para_calculo("< 0,1"), Decimal("0.1"))

    def test_mayor_igual(self):
        p = parse_valor_con_operador("≥20")
        self.assertEqual(p.operador, ">=")
        self.assertEqual(p.numero, Decimal("20"))

    def test_numero_puro(self):
        p = parse_valor_con_operador("12.5")
        self.assertIsNone(p.operador)
        self.assertEqual(p.numero, Decimal("12.5"))

    def test_texto_no_numerico(self):
        p = parse_valor_con_operador("Positivo")
        self.assertIsNone(p.operador)
        self.assertIsNone(p.numero)
        self.assertIsNone(numero_para_calculo("Positivo"))
