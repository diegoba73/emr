"""
Tests LIMS B2-B / B2-B-A — obligatoriedad progresiva de muestra por TipoExamen.
"""
import json
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
from laboratorio.muestra_estado import (
    aplicar_recibir,
    aplicar_rechazar,
    aplicar_tomar,
    crear_muestra,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from auditoria.models import AuditEvent

User = get_user_model()


@pytest.mark.django_db
class TestTipoExamenMuestraRequerida(APITestCase):
    """cargar-resultados con requiere_muestra en TipoExamen."""

    def setUp(self):
        # TipoMuestra.codigo max_length=10 (PostgreSQL); suf corto para fixtures.
        tag = uuid.uuid4().hex[:4]
        suf = f"B2B{tag}"
        self.tipo_muestra_a = TipoMuestra.objects.create(
            codigo=f"SNG{tag}", nombre="Sangre", activo=True
        )
        self.tipo_muestra_b = TipoMuestra.objects.create(
            codigo=f"ORI{tag}", nombre="Orina", activo=True
        )
        assert len(self.tipo_muestra_a.codigo) <= 10
        assert len(self.tipo_muestra_b.codigo) <= 10
        self.tipo_examen_legacy = TipoExamen.objects.create(
            codigo=f"GLU{suf}",
            nombre="Glucosa",
            tipo_muestra_requerida=self.tipo_muestra_a,
            requiere_muestra=False,
            precio=1,
            activo=True,
        )
        self.tipo_examen_oblig = TipoExamen.objects.create(
            codigo=f"HEM{suf}",
            nombre="Hemograma",
            tipo_muestra_requerida=self.tipo_muestra_a,
            requiere_muestra=True,
            precio=1,
            activo=True,
        )
        self.paciente = Paciente.objects.create(
            dni=f"{suf[:8]}", nombre="Ana", apellido="Test"
        )
        esp = Especialidad.objects.create(nombre=f"Lab {suf}")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="X", matricula=f"M-{suf}", especialidad=esp
        )
        self.user_lab = User.objects.create_user(
            username=f"lab_{suf}",
            email=f"lab-{suf}@test.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_admin = User.objects.create_user(
            username=f"adm_{suf}",
            email=f"adm-{suf}@test.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user_lab)

    def _solicitud_con_tipo(self, tipo_examen):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(tipo_examen)
        res = ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=tipo_examen,
            valor_obtenido="",
        )
        return sol, res

    def _muestra_recibida(self, sol, tipo_muestra=None):
        tm = tipo_muestra or self.tipo_muestra_a
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        m.refresh_from_db()
        return m

    def test_tipo_examen_requiere_muestra_default_false(self):
        te = TipoExamen.objects.create(
            codigo=f"DEF{uuid.uuid4().hex[:4]}",
            nombre="Default",
            tipo_muestra_requerida=self.tipo_muestra_a,
            precio=0,
        )
        assert te.requiere_muestra is False

    def test_tipo_no_requiere_muestra_sin_muestra_sigue_funcionando(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_legacy)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "100"}]},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.valor_obtenido == "100"
        assert res.muestra_id is None

    def test_tipo_no_requiere_muestra_pero_si_se_envia_muestra_debe_coincidir_tipo(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_legacy)
        valor_antes = res.valor_obtenido
        m = self._muestra_recibida(sol, tipo_muestra=self.tipo_muestra_b)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
                {
                    "resultados": [
                        {"id": res.pk, "valor": "88", "muestra_id": m.pk},
                    ]
                },
                format="json",
            )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "tipo requerido" in (r.json().get("error") or "").lower()
        res.refresh_from_db()
        assert res.valor_obtenido == valor_antes
        assert res.muestra_id is None
        assert not m.eventos.filter(accion="PROCESAMIENTO").exists()
        assert not AuditEvent.objects.filter(
            entity_type=ResultadoExamen._meta.label,
            entity_id=str(res.pk),
            module="laboratorio",
            metadata__accion="cargar_resultados",
        ).exists()

    def test_tipo_no_requiere_muestra_con_muestra_correcta_funciona(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_legacy)
        m = self._muestra_recibida(sol, tipo_muestra=self.tipo_muestra_a)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "42", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.muestra_id == m.pk
        assert res.valor_obtenido == "42"

    def test_cargar_resultado_tipo_requiere_muestra_sin_muestra_falla(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        valor_antes = res.valor_obtenido
        muestra_antes = res.muestra_id
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
                {"resultados": [{"id": res.pk, "valor": "13.5"}]},
                format="json",
            )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "muestra" in (r.json().get("error") or "").lower()
        res.refresh_from_db()
        assert res.valor_obtenido == valor_antes
        assert res.muestra_id == muestra_antes
        assert not Muestra.objects.filter(
            eventos__accion="PROCESAMIENTO", solicitud_id=sol.pk
        ).exists()
        assert not AuditEvent.objects.filter(
            entity_type=ResultadoExamen._meta.label,
            entity_id=str(res.pk),
            module="laboratorio",
            metadata__accion="cargar_resultados",
        ).exists()

    def test_cargar_resultado_tipo_requiere_muestra_con_muestra_valida_funciona(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        m = self._muestra_recibida(sol)
        assert m.estado == "RECIBIDA"
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
                {
                    "resultados": [
                        {"id": res.pk, "valor": "12", "muestra_id": m.pk},
                    ]
                },
                format="json",
            )
        assert r.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.muestra_id == m.pk
        assert res.valor_obtenido == "12"
        m.refresh_from_db()
        assert m.estado == "EN_PROCESO"

    def test_cargar_resultado_rechaza_muestra_de_tipo_incorrecto(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        m = self._muestra_recibida(sol, tipo_muestra=self.tipo_muestra_b)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "1", "muestra_id": m.pk}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "tipo requerido" in (r.json().get("error") or "").lower()
        res.refresh_from_db()
        assert res.muestra_id is None

    def test_cargar_resultado_acepta_muestra_de_tipo_requerido(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        m = self._muestra_recibida(sol, tipo_muestra=self.tipo_muestra_a)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "9", "muestra_id": m.pk}]},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.muestra_id == m.pk

    def test_requiere_muestra_muestra_tomada_400(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra_a.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        m.refresh_from_db()
        assert m.estado == "TOMADA"
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "1", "muestra_id": m.pk}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_requiere_muestra_muestra_rechazada_400(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra_a.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_rechazar(m.pk, actor=None, view="t", motivo_rechazo="x")
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "1", "muestra_id": m.pk}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_requiere_muestra_muestra_descartada_400(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        m = self._muestra_recibida(sol)
        from laboratorio.muestra_estado import aplicar_descartar

        aplicar_descartar(m.pk, actor=None, view="t")
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "1", "muestra_id": m.pk}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_resultado_validado_no_cambia_muestra_aunque_tipo_requiera(self):
        from django.utils import timezone

        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        m1 = self._muestra_recibida(sol)
        res.muestra = m1
        res.valor_obtenido = "50"
        res.validado_por = self.user_admin
        res.fecha_validacion = timezone.now()
        res.save()
        m2 = self._muestra_recibida(sol)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "51", "muestra_id": m2.pk}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        res.refresh_from_db()
        assert res.muestra_id == m1.pk

    def test_fallo_por_muestra_obligatoria_no_audita_carga_exitosa(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        count_antes = AuditEvent.objects.filter(
            entity_type=ResultadoExamen._meta.label,
            entity_id=str(res.pk),
        ).count()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
                {"resultados": [{"id": res.pk, "valor": "99"}]},
                format="json",
            )
        assert (
            AuditEvent.objects.filter(
                entity_type=ResultadoExamen._meta.label,
                entity_id=str(res.pk),
            ).count()
            == count_antes
        )

    def test_carga_con_muestra_requerida_no_audita_codigo_barra_ni_valor(self):
        sol, res = self._solicitud_con_tipo(self.tipo_examen_oblig)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra_a.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
            codigo_barra="MUE-B2B-SENSIBLE",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
                {
                    "resultados": [
                        {
                            "id": res.pk,
                            "valor": "14.2-SENSIBLE",
                            "valor_numerico": "14.2",
                            "unidad": "g/dL",
                            "muestra_id": m.pk,
                        }
                    ]
                },
                format="json",
            )
        events = AuditEvent.objects.filter(
            entity_type=ResultadoExamen._meta.label,
            entity_id=str(res.pk),
            module="laboratorio",
        )
        blob = json.dumps(
            [{"metadata": e.metadata, "after_state": e.after_state} for e in events],
            default=str,
        )
        assert "MUE-B2B-SENSIBLE" not in blob
        assert "14.2-SENSIBLE" not in blob
        for ev in events:
            meta = ev.metadata or {}
            assert "codigo_barra" not in meta
            assert "valor" not in meta
