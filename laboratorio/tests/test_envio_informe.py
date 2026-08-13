"""Tests envío de informes LIMS (email / WhatsApp)."""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from laboratorio.informe_entrega_token import (
    crear_token_entrega_informe,
    verificar_token_entrega_informe,
)
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.services_envio_informe import enviar_informe_solicitud
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestInformeEntregaToken:
    def test_token_roundtrip(self):
        tok = crear_token_entrega_informe(42)
        assert verificar_token_entrega_informe(tok) == 42


@pytest.mark.django_db
class TestEnvioInformeAPI(APITestCase):
    def setUp(self):
        suf = "ENV"
        self.user_lab = User.objects.create_user(
            username="lab_env",
            email="lab-env@test.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.tipo_muestra = TipoMuestra.objects.create(
            codigo=f"SNG{suf}", nombre="Sangre", activo=True
        )
        self.tipo_examen = TipoExamen.objects.create(
            codigo=f"GLU{suf}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tipo_muestra,
            precio=1,
            activo=True,
        )
        self.paciente = Paciente.objects.create(
            dni="99887766",
            nombre="Ana",
            apellido="Env",
            email="paciente.env@test.com",
            telefono="01155556666",
        )
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="E", matricula=f"M{suf}", especialidad=esp
        )
        self.client.force_authenticate(user=self.user_lab)

    def _sol_finalizada(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_examen)
        res = ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=self.tipo_examen, valor_obtenido="100"
        )
        sol.estado = "FINALIZADO"
        sol.save(update_fields=["estado"])
        return sol

    @patch("laboratorio.services_envio_informe.EmailMessage.send", return_value=1)
    def test_enviar_email_adjunta_pdf(self, mock_send):
        sol = self._sol_finalizada()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.id}/enviar-informe/",
            {"email": True, "whatsapp": False},
            format="json",
            HTTP_HOST="localhost:8000",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.json()["envio"]["email_enviado"])
        self.assertTrue(r.json()["envio"]["email_adjunto_pdf"])
        mock_send.assert_called_once()

    @patch("laboratorio.services_envio_informe.EmailMessage.send", return_value=1)
    def test_enviar_email_medico_solicitante(self, mock_send):
        user_med = User.objects.create_user(
            username="med_env",
            email="medico.env@test.com",
            password="x",
            rol="medico",
            telefono="01144445555",
        )
        self.medico.user = user_med
        self.medico.save(update_fields=["user"])
        sol = self._sol_finalizada()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.id}/enviar-informe/",
            {
                "email": False,
                "whatsapp": False,
                "email_medico": True,
                "whatsapp_medico": False,
            },
            format="json",
            HTTP_HOST="localhost:8000",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        envio = r.json()["envio"]
        self.assertTrue(envio["email_enviado"])
        self.assertIn("medico.env@test.com", envio["email_destino"])
        self.assertEqual(envio["email_destinos"], ["medico.env@test.com"])
        mock_send.assert_called_once()

    @patch("laboratorio.services_envio_informe._intentar_twilio_whatsapp")
    @patch("laboratorio.services_envio_informe.EmailMessage.send", return_value=1)
    def test_enviar_paciente_y_medico(self, mock_send, mock_wa):
        mock_wa.return_value = (True, None)
        user_med = User.objects.create_user(
            username="med_env2",
            email="medico2.env@test.com",
            password="x",
            rol="medico",
            telefono="01166667777",
        )
        self.medico.user = user_med
        self.medico.save(update_fields=["user"])
        sol = self._sol_finalizada()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.id}/enviar-informe/",
            {
                "email": True,
                "whatsapp": False,
                "email_medico": True,
                "whatsapp_medico": True,
            },
            format="json",
            HTTP_HOST="localhost:8000",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        envio = r.json()["envio"]
        self.assertTrue(envio["email_enviado"])
        self.assertEqual(len(envio["email_destinos"]), 2)
        self.assertTrue(envio["whatsapp_enviado"])
        roles = {e["rol"] for e in envio["whatsapp_enlaces"]}
        self.assertIn("medico", roles)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(mock_wa.call_count, 1)

    @patch("laboratorio.services_envio_informe._intentar_twilio_whatsapp")
    def test_enviar_whatsapp_incluye_url_pdf(self, mock_wa):
        sol = self._sol_finalizada()
        mock_wa.return_value = (True, None)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.id}/enviar-informe/",
            {"email": False, "whatsapp": True},
            format="json",
            HTTP_HOST="localhost:8000",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        envio = r.json()["envio"]
        self.assertTrue(envio["whatsapp_enviado"])
        self.assertIn("informe-entrega", envio["informe_enlace_descarga"])
        mock_wa.assert_called_once()
        media_url = mock_wa.call_args.kwargs.get("media_url") or mock_wa.call_args[1].get("media_url")
        assert media_url and "informe-entrega" in media_url

    def test_informe_entrega_publico_con_token(self):
        sol = self._sol_finalizada()
        from laboratorio.informe_entrega_token import asignar_token_entrega

        tok = asignar_token_entrega(sol, renovar=True)
        sol.save(update_fields=["informe_entrega_token", "informe_entrega_token_expira"])
        self.client.force_authenticate(user=None)
        r = self.client.get(f"/api/lab/solicitudes/informe-entrega/?t={tok}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertIn(b"%PDF", r.content[:10])

    @patch("laboratorio.services_envio_informe.EmailMessage.send", return_value=1)
    def test_secretaria_envia_informe_finalizado(self, mock_send):
        sec = User.objects.create_user(
            username="sec_env",
            email="sec.env@test.com",
            password="x",
            rol="secretaria",
        )
        sol = self._sol_finalizada()
        self.client.force_authenticate(user=sec)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.id}/enviar-informe/",
            {"email": True, "whatsapp": False},
            format="json",
            HTTP_HOST="localhost:8000",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertTrue(r.json()["envio"]["email_enviado"])
        mock_send.assert_called_once()

    def test_secretaria_no_envia_si_no_finalizado(self):
        sec = User.objects.create_user(
            username="sec_env2",
            email="sec.env2@test.com",
            password="x",
            rol="secretaria",
        )
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        self.client.force_authenticate(user=sec)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.id}/enviar-informe/",
            {"email": True, "whatsapp": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_enfermeria_no_envia_informe(self):
        enf = User.objects.create_user(
            username="enf_env",
            email="enf.env@test.com",
            password="x",
            rol="enfermeria",
        )
        sol = self._sol_finalizada()
        self.client.force_authenticate(user=enf)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.id}/enviar-informe/",
            {"email": True, "whatsapp": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestEnvioInformeServicio:
    @patch("laboratorio.services_envio_informe._intentar_twilio_whatsapp")
    @patch("laboratorio.services_envio_informe.EmailMessage.send")
    def test_whatsapp_recibe_media_url(self, mock_mail, mock_wa):
        mock_wa.return_value = (True, None)
        user = User.objects.create_user(username="u", password="x", rol="laboratorio")
        tm = TipoMuestra.objects.create(codigo="T1", nombre="S", activo=True)
        te = TipoExamen.objects.create(
            codigo="E1", nombre="E", tipo_muestra_requerida=tm, precio=1, activo=True
        )
        p = Paciente.objects.create(
            dni="111", nombre="P", apellido="X", telefono="5491111222233", email="a@b.com"
        )
        sol = SolicitudExamen.objects.create(
            paciente=p, origen_solicitud="AMBULATORIO_CEHTA", estado="EN_PROCESO"
        )
        sol.tipos_examen.add(te)
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=te, valor_obtenido="1")
        sol.estado = "FINALIZADO"
        sol.save(update_fields=["estado"])
        res = enviar_informe_solicitud(
            sol,
            enviar_email=False,
            enviar_whatsapp=True,
            actor=user,
            view="test",
            public_base_url="https://api.clinica.test",
        )
        assert res.whatsapp_enviado
        assert res.informe_enlace_descarga
        mock_wa.assert_called_once()
        media_url = mock_wa.call_args.kwargs.get("media_url")
        assert media_url and "informe-entrega" in media_url
        sol.refresh_from_db()
        assert sol.informe_entrega_token
        assert f"t={sol.informe_entrega_token}" in media_url
