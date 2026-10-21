"""Tests del examen microscópico directo (fresco / Gram / KOH / parasitológico)."""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from laboratorio.examen_fresco_micro import (
    estudio_admite_examen_fresco,
    examen_fresco_tiene_datos,
    normalizar_examen_fresco,
    perfil_examen_fresco,
    secciones_examen_directo,
    titulo_informe_examen_fresco,
)
from laboratorio.models_microbiologia import EstudioMicrobiologia, TipoCultivoMicrobiologia
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestExamenFrescoMicro(TestCase):
    def setUp(self):
        tag = uuid.uuid4().hex[:6]
        self.paciente = Paciente.objects.create(
            dni=f"D{tag}", nombre="Ana", apellido="Test"
        )

        def cultivo(codigo, nombre):
            obj, _ = TipoCultivoMicrobiologia.objects.update_or_create(
                codigo=codigo,
                defaults={"nombre": nombre, "activo": True},
            )
            return obj

        self.cultivo_vag = cultivo("VAGINAL", "Cultivo vaginal")
        self.cultivo_copro = cultivo("COPROCULTIVO", "Coprocultivo")
        self.cultivo_esputo = cultivo("ESPUTO", "Cultivo de esputo")
        self.cultivo_hemo = cultivo("HEMOCULTIVO", "Hemocultivo")
        self.cultivo_lcr = cultivo("LCR", "Cultivo de LCR")
        self.cultivo_uro = cultivo("UROCULTIVO", "Urocultivo")

        def estudio(cult):
            return EstudioMicrobiologia.objects.create(
                paciente=self.paciente,
                tipo_cultivo=cult,
                tipo_estudio=cult.codigo,
                estado="RECIBIDO",
            )

        self.estudio_vag = estudio(self.cultivo_vag)
        self.estudio_copro = estudio(self.cultivo_copro)
        self.estudio_esputo = estudio(self.cultivo_esputo)
        self.estudio_hemo = estudio(self.cultivo_hemo)
        self.estudio_lcr = estudio(self.cultivo_lcr)
        self.estudio_uro = estudio(self.cultivo_uro)

        self.user = User.objects.create_user(
            username=f"lab{tag}",
            email=f"lab{tag}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_tecnicas_por_cultivo(self):
        self.assertEqual(
            [s["tecnica"] for s in secciones_examen_directo(self.estudio_vag)],
            ["fresco", "koh"],
        )
        self.assertEqual(
            [s["tecnica"] for s in secciones_examen_directo(self.estudio_esputo)],
            ["gram"],
        )
        self.assertEqual(
            [s["tecnica"] for s in secciones_examen_directo(self.estudio_lcr)],
            ["fresco", "gram"],
        )
        self.assertEqual(
            [s["tecnica"] for s in secciones_examen_directo(self.estudio_hemo)],
            ["gram"],
        )
        self.assertEqual(perfil_examen_fresco(self.estudio_copro), "parasito")
        self.assertFalse(estudio_admite_examen_fresco(self.estudio_uro))
        self.assertEqual(
            titulo_informe_examen_fresco(self.estudio_vag),
            "EXAMEN MICROSCOPICO DIRECTO",
        )

    def test_normalizar_filtra_claves(self):
        data = normalizar_examen_fresco(
            {"EXF_CEL": " 6-10 ", "HACK": "x", "EXF_GRAM": "BGN"}
        )
        self.assertEqual(data["EXF_CEL"], "6-10")
        self.assertEqual(data["EXF_GRAM"], "BGN")
        self.assertNotIn("HACK", data)

    def test_tiene_datos(self):
        self.assertFalse(examen_fresco_tiene_datos(None))
        self.assertFalse(examen_fresco_tiene_datos({"EXF_CEL": ""}))
        self.assertTrue(examen_fresco_tiene_datos({"EXF_GRAM": "BGN"}))

    def test_patch_fresco_y_koh_vaginal(self):
        url = f"/api/lab/microbiologia/estudios/{self.estudio_vag.pk}/"
        resp = self.client.patch(
            url,
            {
                "examen_fresco": {
                    "EXF_CEL": "6-10 por campo",
                    "EXF_MICOL": "No se observan elementos fúngicos",
                }
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["examen_fresco"]["EXF_CEL"], "6-10 por campo")
        self.assertEqual(
            resp.data["examen_fresco"]["EXF_MICOL"],
            "No se observan elementos fúngicos",
        )

    def test_patch_gram_esputo(self):
        url = f"/api/lab/microbiologia/estudios/{self.estudio_esputo.pk}/"
        resp = self.client.patch(
            url,
            {"examen_fresco": {"EXF_GRAM": "Bacilos Gram negativos"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["examen_fresco"]["EXF_GRAM"], "Bacilos Gram negativos")

    def test_patch_rechaza_uro(self):
        url = f"/api/lab/microbiologia/estudios/{self.estudio_uro.pk}/"
        resp = self.client.patch(
            url,
            {"examen_fresco": {"EXF_GRAM": "x"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
