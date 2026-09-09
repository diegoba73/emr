"""DELETE protegido → 409 con can_deactivate."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models_inventario import InsumoLab, LoteInsumo, MovimientoStock

User = get_user_model()


class TestDestroyProtectedInventario(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="inv_del",
            email="inv-del@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.insumo = InsumoLab.objects.create(
            codigo="R-DEL",
            nombre="Reactivo delete",
            tipo=InsumoLab.Tipo.REACTIVO,
            unidad="cartucho",
            stock_min=1,
            activo=True,
        )
        self.lote = LoteInsumo.objects.create(
            insumo=self.insumo,
            codigo_lote="L-DEL",
            cantidad=10,
            fecha_vencimiento=timezone.localdate() + timedelta(days=30),
            activo=True,
        )

    def test_lote_con_movimiento_devuelve_409(self):
        MovimientoStock.objects.create(
            tipo=MovimientoStock.Tipo.INGRESO,
            lote=self.lote,
            cantidad=10,
            motivo="alta",
            usuario=self.user,
        )
        r = self.client.delete(f"/api/lab/inventario/lotes/{self.lote.id}/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT, r.data)
        self.assertEqual(r.data.get("code"), "PROTECTED")
        self.assertTrue(r.data.get("can_deactivate"))
        self.assertTrue(LoteInsumo.objects.filter(pk=self.lote.id).exists())

    def test_lote_sin_movimiento_se_borra(self):
        r = self.client.delete(f"/api/lab/inventario/lotes/{self.lote.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT, r.data)
        self.assertFalse(LoteInsumo.objects.filter(pk=self.lote.id).exists())
