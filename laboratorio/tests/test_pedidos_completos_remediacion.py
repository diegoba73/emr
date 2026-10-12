"""Remediación LIMS: pedido atómico, anti-dup material+fecha, permisos, idempotencia."""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import PanelExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_microbiologia import (
    EstudioMicrobiologia,
    TipoCultivoMicrobiologia,
    TipoMuestraMicrobiologia,
)
from pacientes.models import Paciente

User = get_user_model()


class TestPedidosCompletosRemediacion(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_pc_{suf}", password="x", rol="laboratorio", is_staff=True
        )
        self.medico = User.objects.create_user(
            username=f"med_pc_{suf}", password="x", rol="medico"
        )
        self.pac = Paciente.objects.create(
            dni=f"8{suf[:7]}", nombre="Pedro", apellido="Completo"
        )
        self.tm_suero, _ = TipoMuestra.objects.get_or_create(
            codigo="SUERO", defaults={"nombre": "Suero", "activo": True}
        )
        self.tm_orina, _ = TipoMuestra.objects.get_or_create(
            codigo="ORINA", defaults={"nombre": "Orina", "activo": True}
        )
        self.glu = TipoExamen.objects.create(
            codigo=f"G{suf}",
            nombre="Glu PC",
            tipo_muestra_requerida=self.tm_suero,
            tipo_resultado="NUMERICO",
            activo=True,
        )
        self.crea = TipoExamen.objects.create(
            codigo=f"C{suf}",
            nombre="Crea PC",
            tipo_muestra_requerida=self.tm_suero,
            tipo_resultado="NUMERICO",
            activo=True,
        )
        self.orina_ex = TipoExamen.objects.create(
            codigo=f"O{suf}",
            nombre="Orina PC",
            tipo_muestra_requerida=self.tm_orina,
            tipo_resultado="TEXTO",
            activo=True,
        )
        self.panel_mixto = PanelExamen.objects.create(
            codigo=f"PM{suf}", nombre="Panel mixto PC", activo=True
        )
        self.panel_mixto.tipos_examen.add(self.glu, self.orina_ex)
        self.hoy = timezone.localdate()
        self.manana = self.hoy + timedelta(days=1)
        self.cultivo, _ = TipoCultivoMicrobiologia.objects.get_or_create(
            codigo="HEMOCULTIVO",
            defaults={"nombre": "Hemocultivo", "activo": True},
        )
        self.muestra_micro, _ = TipoMuestraMicrobiologia.objects.get_or_create(
            codigo="SANGRE",
            defaults={"nombre": "Sangre", "activo": True},
        )

    def test_medico_create_granular_403(self):
        self.client.force_authenticate(self.medico)
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.pk,
                "material_pedido": "SANGRE",
                "examenes_ids": [self.glu.pk],
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_medico_pedido_completo_atomico(self):
        self.client.force_authenticate(self.medico)
        r = self.client.post(
            "/api/lab/pedidos-completos/",
            {
                "paciente_id": self.pac.pk,
                "fecha_programada_toma": self.hoy.isoformat(),
                "solicitudes_lab": [
                    {
                        "material_pedido": "SANGRE",
                        "examenes_ids": [self.glu.pk],
                        "paneles_ids": [],
                    },
                    {
                        "material_pedido": "ORINA",
                        "examenes_ids": [self.orina_ex.pk],
                        "paneles_ids": [],
                    },
                ],
                "estudios_micro": [
                    {
                        "material_pedido": "SANGRE",
                        "tipo_cultivo_id": self.cultivo.pk,
                        "tipo_muestra_micro_id": self.muestra_micro.pk,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(len(r.data["solicitudes_ids"]), 2)
        self.assertEqual(len(r.data["estudios_micro_ids"]), 1)
        sols = list(SolicitudExamen.objects.filter(paciente=self.pac).order_by("id"))
        self.assertEqual({s.material_pedido for s in sols}, {"SANGRE", "ORINA"})
        self.assertEqual(EstudioMicrobiologia.objects.filter(paciente=self.pac).count(), 1)

    def test_panel_mixto_repartido_sin_expansion_total(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/pedidos-completos/",
            {
                "paciente_id": self.pac.pk,
                "fecha_programada_toma": self.hoy.isoformat(),
                "solicitudes_lab": [
                    {
                        "material_pedido": "SANGRE",
                        "examenes_ids": [],
                        "paneles_ids": [self.panel_mixto.pk],
                    },
                    {
                        "material_pedido": "ORINA",
                        "examenes_ids": [],
                        "paneles_ids": [self.panel_mixto.pk],
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        sol_s = SolicitudExamen.objects.get(pk=r.data["solicitudes_ids"][0])
        sol_o = SolicitudExamen.objects.get(pk=r.data["solicitudes_ids"][1])
        if sol_s.material_pedido != "SANGRE":
            sol_s, sol_o = sol_o, sol_s
        tipos_s = set(sol_s.resultados.values_list("tipo_examen_id", flat=True))
        tipos_o = set(sol_o.resultados.values_list("tipo_examen_id", flat=True))
        self.assertEqual(tipos_s, {self.glu.pk})
        self.assertEqual(tipos_o, {self.orina_ex.pk})
        self.assertTrue(sol_s.paneles.filter(pk=self.panel_mixto.pk).exists())
        self.assertTrue(sol_o.paneles.filter(pk=self.panel_mixto.pk).exists())

    def test_anti_dup_sangre_hoy_bloquea_segunda(self):
        self.client.force_authenticate(self.lab)
        r1 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.pk,
                "material_pedido": "SANGRE",
                "examenes_ids": [self.glu.pk],
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)
        r2 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.pk,
                "material_pedido": "SANGRE",
                "examenes_ids": [self.crea.pk],
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        # Mañana OK
        r3 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.pk,
                "material_pedido": "SANGRE",
                "examenes_ids": [self.crea.pk],
                "fecha_programada_toma": self.manana.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED, r3.data)
        # Orina hoy OK
        r4 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.pk,
                "material_pedido": "ORINA",
                "examenes_ids": [self.orina_ex.pk],
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r4.status_code, status.HTTP_201_CREATED, r4.data)

    def test_idempotencia_misma_clave_mismo_payload(self):
        self.client.force_authenticate(self.medico)
        body = {
            "paciente_id": self.pac.pk,
            "fecha_programada_toma": self.hoy.isoformat(),
            "solicitudes_lab": [
                {
                    "material_pedido": "SANGRE",
                    "examenes_ids": [self.glu.pk],
                    "paneles_ids": [],
                }
            ],
        }
        key = f"idem-{uuid.uuid4().hex}"
        r1 = self.client.post(
            "/api/lab/pedidos-completos/",
            body,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)
        ids1 = r1.data["solicitudes_ids"]
        r2 = self.client.post(
            "/api/lab/pedidos-completos/",
            body,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, r2.data)
        self.assertEqual(r2.data["solicitudes_ids"], ids1)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 1)

    def test_idempotencia_misma_clave_otro_payload_409(self):
        self.client.force_authenticate(self.medico)
        key = f"idem-{uuid.uuid4().hex}"
        body1 = {
            "paciente_id": self.pac.pk,
            "fecha_programada_toma": self.hoy.isoformat(),
            "solicitudes_lab": [
                {
                    "material_pedido": "SANGRE",
                    "examenes_ids": [self.glu.pk],
                    "paneles_ids": [],
                }
            ],
        }
        body2 = {
            "paciente_id": self.pac.pk,
            "fecha_programada_toma": self.hoy.isoformat(),
            "solicitudes_lab": [
                {
                    "material_pedido": "ORINA",
                    "examenes_ids": [self.orina_ex.pk],
                    "paneles_ids": [],
                }
            ],
        }
        r1 = self.client.post(
            "/api/lab/pedidos-completos/",
            body1,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)
        r2 = self.client.post(
            "/api/lab/pedidos-completos/",
            body2,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r2.status_code, status.HTTP_409_CONFLICT)

    def test_clearance_orina_incluye_creatininemia(self):
        """PAN_CLEAR en orden ORINA trae CREATI (suero) para calcular e informar."""
        from io import StringIO

        from django.core.management import call_command

        call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
        panel = PanelExamen.objects.get(codigo="PAN_CLEAR")
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/pedidos-completos/",
            {
                "paciente_id": self.pac.pk,
                "fecha_programada_toma": self.hoy.isoformat(),
                "solicitudes_lab": [
                    {
                        "material_pedido": "ORINA",
                        "examenes_ids": [],
                        "paneles_ids": [panel.pk],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        sol = SolicitudExamen.objects.get(pk=r.data["solicitudes_ids"][0])
        self.assertEqual(sol.material_pedido, "ORINA")
        codigos = set(
            sol.resultados.values_list("tipo_examen__codigo", flat=True)
        )
        self.assertTrue(
            {"CREATI", "CREA_U", "DIUR", "CLEAR_CREA"} <= codigos,
            codigos,
        )

    def test_clinica_y_micro_mismo_material_coexisten(self):
        self.client.force_authenticate(self.medico)
        r = self.client.post(
            "/api/lab/pedidos-completos/",
            {
                "paciente_id": self.pac.pk,
                "fecha_programada_toma": self.hoy.isoformat(),
                "solicitudes_lab": [
                    {
                        "material_pedido": "SANGRE",
                        "examenes_ids": [self.glu.pk],
                        "paneles_ids": [],
                    }
                ],
                "estudios_micro": [
                    {
                        "material_pedido": "SANGRE",
                        "tipo_cultivo_id": self.cultivo.pk,
                        "tipo_muestra_micro_id": self.muestra_micro.pk,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(len(r.data["solicitudes_ids"]), 1)
        self.assertEqual(len(r.data["estudios_micro_ids"]), 1)
