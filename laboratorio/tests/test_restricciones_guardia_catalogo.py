"""Allowlist de catálogo clínico en pedidos GUARDIA."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import PanelExamen, TipoExamen, TipoMuestra
from laboratorio.restricciones_guardia_catalogo import (
    EXAMENES_GUARDIA_PERMITIDOS,
    PANELES_GUARDIA_PERMITIDOS,
    assert_examenes_permitidos_en_guardia,
    GuardiaCatalogoError,
)
from pacientes.models import Paciente

User = get_user_model()


class TestRestriccionesGuardiaCatalogo(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_g_{suf}", password="x", rol="laboratorio", is_staff=True
        )
        self.pac = Paciente.objects.create(
            dni=f"7{suf[:7]}", nombre="Ana", apellido="Guardia"
        )
        self.tm_suero, _ = TipoMuestra.objects.get_or_create(
            codigo="SUERO", defaults={"nombre": "Suero", "activo": True}
        )
        self.hoy = timezone.localdate()

        # Códigos canónicos del seed (nombres reales).
        self.glu, _ = TipoExamen.objects.get_or_create(
            codigo="GLU",
            defaults={
                "nombre": "Glucemia",
                "tipo_muestra_requerida": self.tm_suero,
                "tipo_resultado": "NUMERICO",
                "activo": True,
            },
        )
        self.crea, _ = TipoExamen.objects.get_or_create(
            codigo="CREATI",
            defaults={
                "nombre": "Creatininemia",
                "tipo_muestra_requerida": self.tm_suero,
                "tipo_resultado": "NUMERICO",
                "activo": True,
            },
        )
        self.urea, _ = TipoExamen.objects.get_or_create(
            codigo="UREA",
            defaults={
                "nombre": "Uremia",
                "tipo_muestra_requerida": self.tm_suero,
                "tipo_resultado": "NUMERICO",
                "activo": True,
            },
        )
        self.au, _ = TipoExamen.objects.get_or_create(
            codigo="AU",
            defaults={
                "nombre": "Uricemia",
                "tipo_muestra_requerida": self.tm_suero,
                "tipo_resultado": "NUMERICO",
                "activo": True,
            },
        )
        self.pan_hemo, _ = PanelExamen.objects.get_or_create(
            codigo="PAN_HEMO",
            defaults={"nombre": "Hemograma", "activo": True},
        )
        self.pan_lip, _ = PanelExamen.objects.get_or_create(
            codigo="PAN_LIP",
            defaults={"nombre": "Perfil lipídico", "activo": True},
        )

    def test_codigos_canonicos_en_allowlist(self):
        self.assertIn("GLU", EXAMENES_GUARDIA_PERMITIDOS)
        self.assertIn("CREATI", EXAMENES_GUARDIA_PERMITIDOS)
        self.assertIn("PAN_HEMO", PANELES_GUARDIA_PERMITIDOS)
        self.assertIn("PAN_IONO", PANELES_GUARDIA_PERMITIDOS)
        self.assertIn("PAN_HEP", PANELES_GUARDIA_PERMITIDOS)
        self.assertIn("PAN_EAB_ART", PANELES_GUARDIA_PERMITIDOS)
        self.assertIn("PAN_EAB_VEN", PANELES_GUARDIA_PERMITIDOS)
        self.assertIn("UREA", EXAMENES_GUARDIA_PERMITIDOS)
        # Uricemia (AU) sigue fuera del pedido de guardia.
        self.assertNotIn("AU", EXAMENES_GUARDIA_PERMITIDOS)

    def test_helper_acepta_urea_en_guardia(self):
        assert_examenes_permitidos_en_guardia(
            origen_solicitud="GUARDIA",
            examenes_ids=[self.urea.pk],
        )

    def test_helper_rechaza_uricemia_en_guardia(self):
        with self.assertRaises(GuardiaCatalogoError) as ctx:
            assert_examenes_permitidos_en_guardia(
                origen_solicitud="GUARDIA",
                examenes_ids=[self.au.pk],
            )
        self.assertIn("AU", str(ctx.exception))

    def test_helper_acepta_glucemia_y_creatininemia(self):
        assert_examenes_permitidos_en_guardia(
            origen_solicitud="GUARDIA",
            examenes_ids=[self.glu.pk, self.crea.pk],
            paneles_ids=[self.pan_hemo.pk],
        )

    def test_helper_no_op_fuera_de_guardia(self):
        assert_examenes_permitidos_en_guardia(
            origen_solicitud="AMBULATORIO_ICPL",
            examenes_ids=[self.urea.pk, self.au.pk],
            paneles_ids=[self.pan_lip.pk],
        )

    def test_api_create_guardia_rechaza_uricemia(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.pk,
                "origen_solicitud": "GUARDIA",
                "material_pedido": "SANGRE",
                "examenes_ids": [self.au.pk],
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)

    def test_api_create_guardia_acepta_glucemia(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.pk,
                "origen_solicitud": "GUARDIA",
                "material_pedido": "SANGRE",
                "examenes_ids": [self.glu.pk],
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

    def test_api_create_guardia_acepta_uremia(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.pk,
                "origen_solicitud": "GUARDIA",
                "material_pedido": "SANGRE",
                "examenes_ids": [self.urea.pk],
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

    def test_pedido_completo_guardia_rechaza_perfil_lipidico(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/pedidos-completos/",
            {
                "paciente_id": self.pac.pk,
                "origen_solicitud": "GUARDIA",
                "fecha_programada_toma": self.hoy.isoformat(),
                "solicitudes_lab": [
                    {
                        "material_pedido": "SANGRE",
                        "paneles_ids": [self.pan_lip.pk],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        detail = str(r.data.get("detail") or r.data)
        self.assertIn("guardia", detail.lower())
