"""
PDF y envío de informe microbiológico — descarga protegida y email.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.informe_entrega_token import (
    crear_token_entrega_informe_micro,
    verificar_token_entrega_informe_micro,
)
from laboratorio.models_microbiologia import EstudioMicrobiologia
from laboratorio.tests.test_microbiologia_api import _setup_estudio_con_lectura
from pacientes.models import Paciente

User = get_user_model()

SENSITIVE_DNI = "MIC-DNI-SENSIBLE-777"


def _audit_blob(*events: AuditEvent) -> str:
    return json.dumps(
        [{"metadata": ev.metadata} for ev in events],
        ensure_ascii=False,
        default=str,
    )


@pytest.mark.django_db
class TestInformeEntregaTokenMicro:
    def test_token_roundtrip(self):
        tok = crear_token_entrega_informe_micro(99)
        assert verificar_token_entrega_informe_micro(tok) == 99


@pytest.mark.django_db
class TestMicroPdfInforme(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.client = APIClient(enforce_csrf_checks=False)
        self.lab = User.objects.create_user(
            username=f"lab_mpdf_{self.suf}",
            email=f"lmpdf{self.suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.bio = User.objects.create_user(
            username=f"bio_mpdf_{self.suf}",
            email=f"bmpdf{self.suf}@t.com",
            password="x",
            rol="bioquimico",
            is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_mpdf_{self.suf}",
            email=f"ampdf{self.suf}@t.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_mpdf_{self.suf}",
            email=f"mmpdf{self.suf}@t.com",
            password="x",
            rol="medico",
        )
        self.med_otro = User.objects.create_user(
            username=f"med2_mpdf_{self.suf}",
            email=f"m2mpdf{self.suf}@t.com",
            password="x",
            rol="medico",
        )
        self.ctx = _setup_estudio_con_lectura(self.suf, self.lab, self.med_user)
        Paciente.objects.filter(pk=self.ctx["paciente"].pk).update(
            dni=SENSITIVE_DNI,
            email=f"pac.mpdf{self.suf}@test.com",
            telefono="01155551234",
            nombre="Paciente",
            apellido="MicroPDF",
        )
        self.ctx["paciente"].refresh_from_db()
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(
            estado="ANTIBIOGRAMA"
        )
        self.ctx["estudio"].refresh_from_db()

    def _url_pdf(self, estudio_id=None):
        eid = estudio_id or self.ctx["estudio"].pk
        return f"/api/lab/microbiologia/estudios/{eid}/informe-pdf/"

    def _url_enviar(self, estudio_id=None):
        eid = estudio_id or self.ctx["estudio"].pk
        return f"/api/lab/microbiologia/estudios/{eid}/enviar-informe/"

    def _emitir_final(self, texto="Informe final cultivo negativo."):
        self.client.force_authenticate(self.bio)
        r = self.client.post(
            "/api/lab/microbiologia/informes/",
            {
                "estudio_id": self.ctx["estudio"].pk,
                "tipo": "FINAL",
                "texto": texto,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        iid = r.json()["id"]
        r2 = self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/emitir/",
            {"texto": texto},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.content)
        return iid

    def _validar_final(self, iid=None):
        if iid is None:
            iid = self._emitir_final()
        self.client.force_authenticate(self.admin)
        r = self.client.post(f"/api/lab/microbiologia/informes/{iid}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        return iid

    def test_sin_informe_emitido_devuelve_400(self):
        self.client.force_authenticate(self.bio)
        r = self.client.get(self._url_pdf())
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bioquimico_descarga_pdf_con_final_emitido(self):
        self._emitir_final()
        audit_antes = AuditEvent.objects.filter(
            metadata__accion="lims_micro_informe_pdf_download",
            metadata__estudio_id=self.ctx["estudio"].pk,
        ).count()
        self.client.force_authenticate(self.bio)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.get(self._url_pdf())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertIn(
            f"informe-micro-{self.ctx['estudio'].pk}.pdf",
            r["Content-Disposition"],
        )
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertEqual(
            AuditEvent.objects.filter(
                metadata__accion="lims_micro_informe_pdf_download",
                metadata__estudio_id=self.ctx["estudio"].pk,
            ).count(),
            audit_antes + 1,
        )

    def test_laboratorio_no_descarga_pdf_antes_de_validar(self):
        self._emitir_final()
        self.client.force_authenticate(self.lab)
        r = self.client.get(self._url_pdf())
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_medico_vinculado_no_descarga_antes_de_validar(self):
        self._emitir_final()
        self.client.force_authenticate(self.med_user)
        r = self.client.get(self._url_pdf())
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_medico_vinculado_descarga_pdf_validado(self):
        self._validar_final()
        self.client.force_authenticate(self.med_user)
        r = self.client.get(self._url_pdf())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_medico_ajeno_descarga_pdf_validado(self):
        self._validar_final()
        self.client.force_authenticate(self.med_otro)
        r = self.client.get(self._url_pdf())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_auditoria_sin_phi(self):
        self._validar_final()
        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.get(self._url_pdf())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ev = (
            AuditEvent.objects.filter(
                metadata__accion="lims_micro_informe_pdf_download",
                metadata__estudio_id=self.ctx["estudio"].pk,
            )
            .order_by("-id")
            .first()
        )
        self.assertIsNotNone(ev)
        meta = ev.metadata or {}
        self.assertEqual(meta.get("accion"), "lims_micro_informe_pdf_download")
        self.assertEqual(meta.get("estudio_id"), self.ctx["estudio"].pk)
        blob = _audit_blob(ev)
        self.assertNotIn(SENSITIVE_DNI, blob)
        self.assertNotIn("Paciente", blob)
        self.assertNotIn("MicroPDF", blob)

    @patch("laboratorio.services_envio_informe.EmailMessage.send", return_value=1)
    def test_enviar_email_smoke(self, mock_send):
        self._validar_final()
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            self._url_enviar(),
            {"email": True, "whatsapp": False},
            format="json",
            HTTP_HOST="localhost:8000",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertTrue(r.json()["envio"]["email_enviado"])
        self.assertTrue(r.json()["envio"]["email_adjunto_pdf"])
        mock_send.assert_called_once()

    def test_enviar_sin_informe_400(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            self._url_enviar(),
            {"email": True},
            format="json",
        )
        # Sin FINAL VALIDADO el object-permission deniega (403) o la vista responde 400.
        self.assertIn(r.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))

    def test_entrega_publica_con_token(self):
        self._validar_final()
        tok = crear_token_entrega_informe_micro(self.ctx["estudio"].pk)
        self.client.logout()
        r = self.client.get(
            f"/api/lab/microbiologia/estudios/informe-entrega/?t={tok}"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        from laboratorio.informe_entrega_token import segmento_path_token_micro

        seg = segmento_path_token_micro(tok)
        r2 = self.client.get(
            f"/api/lab/microbiologia/estudios/informe-entrega/{seg}/"
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertTrue(r2.content.startswith(b"%PDF"))

    def test_entrega_publica_token_invalido(self):
        self.client.logout()
        r = self.client.get(
            "/api/lab/microbiologia/estudios/informe-entrega/?t=token-invalido"
        )
        self.assertIn(
            r.status_code,
            (
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ),
        )
