"""Consumo de reactivos al cargar resultados + recetas + alertas."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.inventario_service import alertas, egresar_por_resultado
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_inventario import (
    ConsumoInsumoExamen,
    InsumoLab,
    LoteInsumo,
    MovimientoStock,
)
from pacientes.models import Paciente

User = get_user_model()


class TestEgresoPorResultado(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="lab_inv", password="x", rol="laboratorio"
        )
        self.tm = TipoMuestra.objects.create(codigo="SANG_INV", nombre="Sangre INV")
        self.ex = TipoExamen.objects.create(
            codigo="GLU_INV",
            nombre="Glucosa INV",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
        )
        self.ex2 = TipoExamen.objects.create(
            codigo="UREA_INV",
            nombre="Urea INV",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
        )
        self.pac = Paciente.objects.create(
            nombre="Inv", apellido="Test", dni="99112233"
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.pac, estado="EN_PROCESO", origen_solicitud="GUARDIA"
        )
        self.sol.tipos_examen.add(self.ex, self.ex2)
        self.res = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.ex, valor_obtenido=""
        )
        self.res2 = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.ex2, valor_obtenido=""
        )

        self.cartucho = InsumoLab.objects.create(
            codigo="GLU-CART",
            nombre="GLU cartucho CM260",
            tipo=InsumoLab.Tipo.REACTIVO,
            unidad="cartucho",
            stock_min=5,
            composicion=InsumoLab.Composicion.A_B,
            canal_analizador=InsumoLab.CanalAnalizador.DEDICADO,
            activo=True,
        )
        self.lote = LoteInsumo.objects.create(
            insumo=self.cartucho,
            codigo_lote="L-CART-1",
            cantidad=10,
            activo=True,
        )
        ConsumoInsumoExamen.objects.create(
            tipo_examen=self.ex,
            insumo=self.cartucho,
            cantidad_por_determinacion=Decimal("1"),
            rol="CARTUCHO",
            activo=True,
        )

    def test_una_linea_descuenta_uno(self):
        self.res.valor_obtenido = "100"
        self.res.save()
        out = egresar_por_resultado(self.res, user=self.user)
        self.assertTrue(out["ok"])
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad, 9)
        self.assertEqual(
            MovimientoStock.objects.filter(
                resultado_id=self.res.id, tipo=MovimientoStock.Tipo.EGRESO
            ).count(),
            1,
        )

    def test_idempotente_segunda_llamada(self):
        self.res.valor_obtenido = "100"
        self.res.save()
        egresar_por_resultado(self.res, user=self.user)
        egresar_por_resultado(self.res, user=self.user)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad, 9)

    def test_sin_receta_no_descuenta(self):
        self.res2.valor_obtenido = "40"
        self.res2.save()
        out = egresar_por_resultado(self.res2, user=self.user)
        self.assertTrue(out.get("skipped"))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad, 10)

    def test_dos_skus_descuenta_ambos(self):
        dil = InsumoLab.objects.create(
            codigo="CELL-PACK",
            nombre="Cellpack",
            tipo=InsumoLab.Tipo.REACTIVO,
            unidad="test",
            stock_min=50,
            activo=True,
        )
        lote_dil = LoteInsumo.objects.create(
            insumo=dil, codigo_lote="CP-1", cantidad=100, activo=True
        )
        ConsumoInsumoExamen.objects.create(
            tipo_examen=self.ex,
            insumo=dil,
            cantidad_por_determinacion=Decimal("1"),
            rol="DILUYENTE",
            activo=True,
        )
        self.res.valor_obtenido = "12.3"
        self.res.save()
        egresar_por_resultado(self.res, user=self.user)
        self.lote.refresh_from_db()
        lote_dil.refresh_from_db()
        self.assertEqual(self.lote.cantidad, 9)
        self.assertEqual(lote_dil.cantidad, 99)

    @override_settings(LAB_INVENTARIO_STRICT=False)
    def test_sin_stock_soft_warning(self):
        self.lote.cantidad = 0
        self.lote.save(update_fields=["cantidad"])
        self.res.valor_obtenido = "1"
        self.res.save()
        out = egresar_por_resultado(self.res, user=self.user)
        self.assertFalse(out["ok"])
        self.assertTrue(out["warnings"])

    def test_alertas_bajo_minimo_tras_egreso(self):
        self.cartucho.stock_min = 10
        self.cartucho.save(update_fields=["stock_min"])
        self.res.valor_obtenido = "90"
        self.res.save()
        egresar_por_resultado(self.res, user=self.user)
        data = alertas()
        ids = {x["insumo_id"] for x in data["bajo_minimo"]}
        self.assertIn(self.cartucho.id, ids)
        ped = {x["insumo_id"] for x in data["pedidos"]}
        self.assertIn(self.cartucho.id, ped)


class TestCargaResultadosDescuentaInventario(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="lab_carga_inv", password="x", rol="laboratorio"
        )
        self.client.force_authenticate(user=self.user)
        self.tm = TipoMuestra.objects.create(codigo="SANG_CI", nombre="Sangre CI")
        self.ex = TipoExamen.objects.create(
            codigo="CREA_CI",
            nombre="Creatinina CI",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
            requiere_muestra=False,
        )
        self.pac = Paciente.objects.create(
            nombre="Carga", apellido="Inv", dni="88112233"
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.pac, estado="EN_PROCESO", origen_solicitud="GUARDIA"
        )
        self.sol.tipos_examen.add(self.ex)
        self.res = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.ex, valor_obtenido=""
        )
        self.insumo = InsumoLab.objects.create(
            codigo="CREA-CART",
            nombre="CREA abierto",
            tipo=InsumoLab.Tipo.REACTIVO,
            unidad="cartucho",
            canal_analizador=InsumoLab.CanalAnalizador.ABIERTO,
            composicion=InsumoLab.Composicion.SOLO_A,
            stock_min=2,
            activo=True,
        )
        self.lote = LoteInsumo.objects.create(
            insumo=self.insumo, codigo_lote="AB-1", cantidad=5, activo=True
        )
        ConsumoInsumoExamen.objects.create(
            tipo_examen=self.ex,
            insumo=self.insumo,
            cantidad_por_determinacion=1,
            rol="CARTUCHO",
            activo=True,
        )

    def test_cargar_primera_vez_descuenta(self):
        r = self.client.post(
            f"/api/lab/solicitudes/{self.sol.id}/cargar-resultados/",
            {"resultados": [{"id": self.res.id, "valor": "1.2"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad, 4)
        self.assertEqual(
            MovimientoStock.objects.filter(resultado_id=self.res.id).count(), 1
        )

    def test_segunda_carga_no_vuelve_a_descontar(self):
        self.client.post(
            f"/api/lab/solicitudes/{self.sol.id}/cargar-resultados/",
            {"resultados": [{"id": self.res.id, "valor": "1.2"}]},
            format="json",
        )
        self.client.post(
            f"/api/lab/solicitudes/{self.sol.id}/cargar-resultados/",
            {"resultados": [{"id": self.res.id, "valor": "1.4"}]},
            format="json",
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad, 4)


class TestConsumoInsumoApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="lab_receta", password="x", rol="laboratorio"
        )
        self.client.force_authenticate(user=self.user)
        self.tm = TipoMuestra.objects.create(codigo="SANG_RC", nombre="Sangre RC")
        self.ex = TipoExamen.objects.create(
            codigo="TSH_RC",
            nombre="TSH RC",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
        )
        self.insumo = InsumoLab.objects.create(
            codigo="TSH-CART",
            nombre="TSH Finecare",
            tipo=InsumoLab.Tipo.REACTIVO,
            unidad="cartucho",
            activo=True,
        )

    def test_crud_receta(self):
        r = self.client.post(
            "/api/lab/inventario/consumos-examen/",
            {
                "tipo_examen": self.ex.id,
                "insumo": self.insumo.id,
                "cantidad_por_determinacion": "1",
                "rol": "CARTUCHO",
                "activo": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        cid = r.data["id"]
        lst = self.client.get(
            "/api/lab/inventario/consumos-examen/",
            {"tipo_examen_id": self.ex.id},
        )
        self.assertEqual(lst.status_code, status.HTTP_200_OK)
        results = lst.data.get("results", lst.data)
        self.assertTrue(any(x["id"] == cid for x in results))
        d = self.client.delete(f"/api/lab/inventario/consumos-examen/{cid}/")
        self.assertEqual(d.status_code, status.HTTP_204_NO_CONTENT)

    def test_consumo_solo_reactivo_permitido(self):
        r = self.client.post(
            "/api/lab/inventario/consumos-examen/",
            {
                "tipo_examen": self.ex.id,
                "insumo": self.insumo.id,
                "cantidad_por_determinacion": "1",
                "activo": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

    def test_consumo_rechaza_insumo_no_reactivo(self):
        for tipo, codigo in (
            (InsumoLab.Tipo.TUBO, "TUBO-RC"),
            (InsumoLab.Tipo.MEDIO, "MEDIO-RC"),
            (InsumoLab.Tipo.OTRO, "OTRO-RC"),
        ):
            with self.subTest(tipo=tipo):
                otro = InsumoLab.objects.create(
                    codigo=codigo,
                    nombre=f"No reactivo {tipo}",
                    tipo=tipo,
                    unidad="u",
                    activo=True,
                )
                r = self.client.post(
                    "/api/lab/inventario/consumos-examen/",
                    {
                        "tipo_examen": self.ex.id,
                        "insumo": otro.id,
                        "cantidad_por_determinacion": "1",
                        "activo": True,
                    },
                    format="json",
                )
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
                self.assertIn("insumo", r.data)

    def test_consumo_cantidad_positiva_ok(self):
        r = self.client.post(
            "/api/lab/inventario/consumos-examen/",
            {
                "tipo_examen": self.ex.id,
                "insumo": self.insumo.id,
                "cantidad_por_determinacion": "0.5",
                "activo": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

    def test_consumo_rechaza_cantidad_cero(self):
        r = self.client.post(
            "/api/lab/inventario/consumos-examen/",
            {
                "tipo_examen": self.ex.id,
                "insumo": self.insumo.id,
                "cantidad_por_determinacion": "0",
                "activo": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertIn("cantidad_por_determinacion", r.data)

    def test_consumo_rechaza_cantidad_negativa(self):
        r = self.client.post(
            "/api/lab/inventario/consumos-examen/",
            {
                "tipo_examen": self.ex.id,
                "insumo": self.insumo.id,
                "cantidad_por_determinacion": "-1",
                "activo": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertIn("cantidad_por_determinacion", r.data)
