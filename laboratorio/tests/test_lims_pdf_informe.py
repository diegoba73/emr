"""
LIMS PDF-1 — tests de descarga de informe básico en PDF.
"""
from __future__ import annotations

import json
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
from laboratorio.muestra_estado import aplicar_recibir, aplicar_tomar, crear_muestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()

SENSITIVE_BARCODE = "PDF-CODE-SENSITIVE-123"
SENSITIVE_DNI = "PDF-DNI-SENSIBLE-999"


def _audit_blob(*events: AuditEvent) -> str:
    return json.dumps(
        [{"metadata": ev.metadata} for ev in events],
        ensure_ascii=False,
        default=str,
    )


@pytest.mark.django_db
class TestLimsPdfInforme(TestCase):
    """Descarga protegida de informe LIMS en PDF."""

    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.client = APIClient(enforce_csrf_checks=False)
        self.esp = Especialidad.objects.create(nombre=f"Esp PDF {self.suf}")
        self.paciente = Paciente.objects.create(
            dni=SENSITIVE_DNI,
            nombre="Pac",
            apellido="PDF",
        )
        self.med_user = User.objects.create_user(
            username=f"med_pdf_{self.suf}",
            email=f"mpdf{self.suf}@test.invalid",
            password="x",
            rol="medico",
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="PDF",
            matricula=f"MP{self.suf}",
            especialidad=self.esp,
            user=self.med_user,
        )
        self.lab = User.objects.create_user(
            username=f"lab_pdf_{self.suf}",
            email=f"lpdf{self.suf}@test.invalid",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_pdf_{self.suf}",
            email=f"apdf{self.suf}@test.invalid",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"TMP{self.suf[:6]}",
            nombre="Sangre",
            activo=True,
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{self.suf[:6]}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tm,
            precio=1,
            activo=True,
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        self.sol.tipos_examen.add(self.te)
        self.resultado = ResultadoExamen.objects.create(
            solicitud=self.sol,
            tipo_examen=self.te,
            valor_obtenido="5.5",
            es_patologico=False,
        )
        self.muestra = crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test_lims_pdf",
            codigo_barra=SENSITIVE_BARCODE,
        )
        aplicar_tomar(self.muestra.pk, actor=None, view="test_lims_pdf")
        aplicar_recibir(self.muestra.pk, actor=None, view="test_lims_pdf")
        self.resultado.muestra_id = self.muestra.pk
        self.resultado.save(update_fields=["muestra_id"])

    def _url(self, sol_id=None):
        return f"/api/lab/solicitudes/{sol_id or self.sol.pk}/informe-pdf/"

    def test_laboratorio_puede_descargar_informe_pdf(self):
        self.client.force_authenticate(self.lab)
        audit_antes = AuditEvent.objects.filter(
            metadata__accion="lims_informe_pdf_download",
            metadata__solicitud_id=self.sol.pk,
        ).count()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.get(self._url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertIn(f"informe-lims-solicitud-{self.sol.pk}.pdf", r["Content-Disposition"])
        body = r.content
        self.assertTrue(body.startswith(b"%PDF"))
        self.assertNotIn(SENSITIVE_BARCODE.encode(), body)
        self.assertEqual(
            AuditEvent.objects.filter(
                metadata__accion="lims_informe_pdf_download",
                metadata__solicitud_id=self.sol.pk,
            ).count(),
            audit_antes + 1,
        )

    def test_medico_con_acceso_puede_descargar_informe_pdf(self):
        self.client.force_authenticate(self.med_user)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_secretaria_enfermeria_paciente_no_descargan_informe_pdf(self):
        sec = User.objects.create_user(
            username=f"sec_pdf_{self.suf}",
            email=f"spdf{self.suf}@test.invalid",
            password="x",
            rol="secretaria",
        )
        enf = User.objects.create_user(
            username=f"enf_pdf_{self.suf}",
            email=f"epdf{self.suf}@test.invalid",
            password="x",
            rol="enfermeria",
        )
        pac = User.objects.create_user(
            username=f"pac_pdf_{self.suf}",
            email=f"ppdf{self.suf}@test.invalid",
            password="x",
            rol="paciente",
        )
        for user in (sec, enf, pac):
            self.client.force_authenticate(user)
            r = self.client.get(self._url())
            self.assertEqual(
                r.status_code,
                status.HTTP_403_FORBIDDEN,
                msg=f"rol={user.rol}",
            )

    def test_medico_sin_acceso_recibe_404(self):
        otro_med = Medico.objects.create(
            nombre="Otro",
            apellido="Med",
            matricula=f"OM{self.suf}",
            especialidad=self.esp,
            user=User.objects.create_user(
                username=f"om_pdf_{self.suf}",
                email=f"om{self.suf}@test.invalid",
                password="x",
                rol="medico",
            ),
        )
        self.client.force_authenticate(otro_med.user)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_pdf_no_expone_codigo_barra(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertNotIn(SENSITIVE_BARCODE.encode(), r.content)

    def test_auditoria_segura_sin_phi_ni_codigo_barra(self):
        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.get(self._url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ev = (
            AuditEvent.objects.filter(
                metadata__accion="lims_informe_pdf_download",
                metadata__solicitud_id=self.sol.pk,
            )
            .order_by("-id")
            .first()
        )
        self.assertIsNotNone(ev)
        meta = ev.metadata or {}
        self.assertEqual(meta.get("accion"), "lims_informe_pdf_download")
        self.assertEqual(meta.get("solicitud_id"), self.sol.pk)
        self.assertEqual(
            meta.get("view"),
            "SolicitudExamenViewSet.informe_pdf",
        )
        blob = _audit_blob(ev)
        self.assertNotIn(SENSITIVE_BARCODE, blob)
        self.assertNotIn(SENSITIVE_DNI, blob)
        self.assertNotIn("5.5", blob)
        self.assertNotIn(self.paciente.nombre, blob)
        self.assertTrue(
            ev.entity_repr.startswith("laboratorio.SolicitudExamen:")
        )

    def test_descarga_no_cambia_estado(self):
        estado_sol_antes = self.sol.estado
        estado_res_antes = self.resultado.valor_obtenido
        estado_muestra_antes = Muestra.objects.get(pk=self.muestra.pk).estado
        n_resultados_antes = ResultadoExamen.objects.filter(solicitud=self.sol).count()
        self.client.force_authenticate(self.lab)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.sol.refresh_from_db()
        self.resultado.refresh_from_db()
        self.assertEqual(self.sol.estado, estado_sol_antes)
        self.assertEqual(self.resultado.valor_obtenido, estado_res_antes)
        self.assertEqual(
            Muestra.objects.get(pk=self.muestra.pk).estado,
            estado_muestra_antes,
        )
        self.assertEqual(
            ResultadoExamen.objects.filter(solicitud=self.sol).count(),
            n_resultados_antes,
        )

    def test_intento_bloqueado_no_audita_exito(self):
        sec = User.objects.create_user(
            username=f"sec2_pdf_{self.suf}",
            email=f"s2pdf{self.suf}@test.invalid",
            password="x",
            rol="secretaria",
        )
        audit_antes = AuditEvent.objects.filter(
            metadata__accion="lims_informe_pdf_download",
            metadata__solicitud_id=self.sol.pk,
        ).count()
        self.client.force_authenticate(sec)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.get(self._url())
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            AuditEvent.objects.filter(
                metadata__accion="lims_informe_pdf_download",
                metadata__solicitud_id=self.sol.pk,
            ).count(),
            audit_antes,
        )
