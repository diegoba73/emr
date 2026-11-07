"""Historial de cultivo micro: mismo tipo_cultivo, cualquier microorganismo."""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.analisis_historial_microbiologia import (
    clasificar_desarrollo,
    historial_cultivo_estudio,
)
from laboratorio.models_microbiologia import (
    AisladoMicrobiologico,
    EstudioMicrobiologia,
    LecturaCultivo,
    Microorganismo,
    MedioCultivo,
    SiembraMicrobiologia,
    TipoCultivoMicrobiologia,
    TipoMuestraMicrobiologia,
)
from pacientes.models import Paciente

User = get_user_model()


class TestHistorialCultivoMicro(TestCase):
    def setUp(self):
        suf = uuid.uuid4().hex[:6]
        self.client = APIClient()
        self.lab = User.objects.create_user(
            username=f"lab_hm_{suf}", password="x", rol="laboratorio", is_staff=True
        )
        self.pac = Paciente.objects.create(
            dni=f"6{suf[:7]}", nombre="Luis", apellido="MicroHist"
        )
        self.cultivo, _ = TipoCultivoMicrobiologia.objects.get_or_create(
            codigo="UROCULTIVO",
            defaults={"nombre": "Urocultivo", "activo": True},
        )
        self.otro_cultivo, _ = TipoCultivoMicrobiologia.objects.get_or_create(
            codigo="HEMOCULTIVO",
            defaults={"nombre": "Hemocultivo", "activo": True},
        )
        self.muestra, _ = TipoMuestraMicrobiologia.objects.get_or_create(
            codigo="ORINA",
            defaults={"nombre": "Orina", "activo": True},
        )
        self.medio, _ = MedioCultivo.objects.get_or_create(
            codigo=f"CLED{suf[:3]}",
            defaults={"nombre": "CLED", "activo": True},
        )
        self.eco, _ = Microorganismo.objects.get_or_create(
            codigo=f"ECO{suf[:4]}",
            defaults={"nombre": "E. coli", "activo": True},
        )
        self.kleb, _ = Microorganismo.objects.get_or_create(
            codigo=f"KLE{suf[:4]}",
            defaults={"nombre": "K. pneumoniae", "activo": True},
        )
        self.ahora = timezone.now()

    def _estudio(self, *, estado="INFORMADO", cultivo=None, created_delta_days=0):
        e = EstudioMicrobiologia.objects.create(
            paciente=self.pac,
            tipo_cultivo=cultivo or self.cultivo,
            tipo_muestra_micro=self.muestra,
            tipo_estudio=(cultivo or self.cultivo).codigo,
            estado=estado,
        )
        if created_delta_days:
            EstudioMicrobiologia.objects.filter(pk=e.pk).update(
                created_at=self.ahora - timedelta(days=created_delta_days)
            )
            e.refresh_from_db()
        return e

    def _lectura(self, estudio, crecimiento):
        siembra = SiembraMicrobiologia.objects.create(
            estudio=estudio,
            medio=self.medio,
            sembrado_por=self.lab,
        )
        return LecturaCultivo.objects.create(
            estudio=estudio,
            siembra=siembra,
            crecimiento=crecimiento,
            leido_por=self.lab,
        )

    def _aislado(self, estudio, lectura, micro):
        return AisladoMicrobiologico.objects.create(
            estudio=estudio,
            lectura_origen=lectura,
            microorganismo=micro,
            estado="IDENTIFICADO",
            creado_por=self.lab,
        )

    def test_incluye_cualquier_organismo_previo_mismo_cultivo(self):
        """No filtrar por microorganismo: E. coli previo aparece aunque el actual sea Klebsiella."""
        prev = self._estudio(estado="INFORMADO", created_delta_days=30)
        lec = self._lectura(prev, "ABUNDANTE")
        self._aislado(prev, lec, self.eco)

        actual = self._estudio(estado="SEMBRADO", created_delta_days=0)
        # Episodio actual con otro organismo (aún no importa para el historial).
        lec_act = self._lectura(actual, "MODERADO")
        self._aislado(actual, lec_act, self.kleb)

        payload = historial_cultivo_estudio(actual, limit=10)
        self.assertEqual(len(payload["previos"]), 1)
        ep = payload["previos"][0]
        self.assertEqual(ep["desarrollo"], "CON_DESARROLLO")
        nombres = {m["nombre"] for m in ep["microorganismos"]}
        self.assertIn("E. coli", nombres)
        self.assertNotIn("K. pneumoniae", nombres)

    def test_sin_desarrollo_sin_organismos(self):
        prev = self._estudio(estado="VALIDADO", created_delta_days=10)
        self._lectura(prev, "SIN_DESARROLLO")
        actual = self._estudio(estado="PENDIENTE", created_delta_days=0)
        payload = historial_cultivo_estudio(actual, limit=10)
        self.assertEqual(len(payload["previos"]), 1)
        self.assertEqual(payload["previos"][0]["desarrollo"], "SIN_DESARROLLO")
        self.assertEqual(payload["previos"][0]["microorganismos"], [])

    def test_no_mezcla_otro_tipo_cultivo(self):
        prev_uro = self._estudio(estado="INFORMADO", cultivo=self.cultivo, created_delta_days=5)
        self._lectura(prev_uro, "SIN_DESARROLLO")
        prev_hemo = self._estudio(
            estado="INFORMADO", cultivo=self.otro_cultivo, created_delta_days=4
        )
        lec = self._lectura(prev_hemo, "ABUNDANTE")
        self._aislado(prev_hemo, lec, self.eco)

        actual = self._estudio(estado="PENDIENTE", cultivo=self.cultivo, created_delta_days=0)
        payload = historial_cultivo_estudio(actual, limit=10)
        self.assertEqual(len(payload["previos"]), 1)
        self.assertEqual(payload["previos"][0]["estudio_id"], prev_uro.pk)

    def test_clasificar_desarrollo(self):
        e = self._estudio(estado="INFORMADO")
        self.assertEqual(clasificar_desarrollo(e), "SIN_LECTURA")
        self._lectura(e, "SIN_DESARROLLO")
        e = EstudioMicrobiologia.objects.prefetch_related("lecturas", "aislados").get(pk=e.pk)
        self.assertEqual(clasificar_desarrollo(e), "SIN_DESARROLLO")

    def test_api_historial_cultivo(self):
        prev = self._estudio(estado="INFORMADO", created_delta_days=7)
        lec = self._lectura(prev, "ESCASO")
        self._aislado(prev, lec, self.kleb)
        actual = self._estudio(estado="RECIBIDO", created_delta_days=0)

        self.client.force_authenticate(self.lab)
        r = self.client.get(
            f"/api/lab/microbiologia/estudios/{actual.pk}/historial-cultivo/",
            {"n": 5},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(len(r.data["previos"]), 1)
        self.assertEqual(r.data["previos"][0]["desarrollo"], "CON_DESARROLLO")
        self.assertEqual(r.data["previos"][0]["microorganismos"][0]["nombre"], "K. pneumoniae")
