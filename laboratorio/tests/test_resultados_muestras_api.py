"""
Tests API cargar-resultados / validar con muestra_id (LIMS Fase B2).
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
from laboratorio.muestra_estado import (
    aplicar_cancelar,
    aplicar_descartar,
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
class TestCargarResultadosMuestraAPI(APITestCase):
    """cargar-resultados con muestra_id."""

    def setUp(self):
        suf = "B2API"
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
            dni="11112222", nombre="Ana", apellido="Test"
        )
        esp = Especialidad.objects.create(nombre=f"Cardio {suf}")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="X", matricula="M-B2", especialidad=esp
        )
        self.user_lab = User.objects.create_user(
            username="lab_b2",
            email="lab-b2@test.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_admin = User.objects.create_user(
            username="adm_b2",
            email="adm-b2@test.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user_lab)

    def _solicitud_en_proceso_con_resultado(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_examen)
        res = ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_examen,
            valor_obtenido="",
        )
        return sol, res

    def _muestra_recibida(self, sol):
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        m.refresh_from_db()
        return m

    def test_carga_sin_muestra_id_sigue_funcionando(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "100", "es_patologico": False},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.valor_obtenido == "100"
        assert res.muestra_id is None

    def test_carga_con_muestra_recibida_ok(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = self._muestra_recibida(sol)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {
                        "id": res.pk,
                        "valor": "99",
                        "muestra_id": m.pk,
                        "es_patologico": False,
                    },
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.muestra_id == m.pk
        assert res.valor_obtenido == "99"

    def test_carga_muestra_id_null_limpia_asociacion_y_audita_cambio(self):
        """muestra_id: null limpia FK; auditoría con muestra_anterior_id / muestra_nueva_id."""
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = self._muestra_recibida(sol)
        r1 = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {
                        "id": res.pk,
                        "valor": "10",
                        "muestra_id": m.pk,
                    },
                ]
            },
            format="json",
        )
        assert r1.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.muestra_id == m.pk

        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
                {
                    "resultados": [
                        {
                            "id": res.pk,
                            "valor": "88",
                            "muestra_id": None,
                        },
                    ]
                },
                format="json",
            )
        assert r2.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.muestra_id is None
        assert res.valor_obtenido == "88"

        ev = (
            AuditEvent.objects.filter(
                entity_type=ResultadoExamen._meta.label,
                entity_id=str(res.pk),
                module="laboratorio",
                action="UPDATE",
            )
            .order_by("-id")
            .first()
        )
        assert ev is not None
        meta = ev.metadata or {}
        assert meta.get("muestra_anterior_id") == m.pk
        assert meta.get("muestra_nueva_id") is None

    def test_carga_sin_clave_muestra_id_preserva_fk_sin_auditoria_cambio_muestra(self):
        """Sin clave muestra_id: solo actualiza valor; no toca auditoría de cambio de muestra."""
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = self._muestra_recibida(sol)
        self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "10", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        res.refresh_from_db()
        assert res.muestra_id == m.pk

        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
                {
                    "resultados": [
                        {"id": res.pk, "valor": "77"},
                    ]
                },
                format="json",
            )
        assert r.status_code == status.HTTP_200_OK
        res.refresh_from_db()
        assert res.muestra_id == m.pk
        assert res.valor_obtenido == "77"

        ev = (
            AuditEvent.objects.filter(
                entity_type=ResultadoExamen._meta.label,
                entity_id=str(res.pk),
                module="laboratorio",
                action="UPDATE",
            )
            .order_by("-id")
            .first()
        )
        assert ev is not None
        meta = ev.metadata or {}
        assert "muestra_anterior_id" not in meta
        assert "muestra_nueva_id" not in meta

    def test_carga_muestra_otra_solicitud_400(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        sol2 = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol2.tipos_examen.add(self.tipo_examen)
        m_otra = self._muestra_recibida(sol2)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "1", "muestra_id": m_otra.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_carga_muestra_rechazada_400(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_rechazar(m.pk, actor=None, view="t", motivo_rechazo="x")
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "1", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_carga_muestra_pendiente_toma_400(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        assert m.estado == "PENDIENTE_TOMA"
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "1", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_carga_muestra_descartada_400(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = self._muestra_recibida(sol)
        aplicar_descartar(m.pk, actor=None, view="t")
        m.refresh_from_db()
        assert m.estado == "DESCARTADA"
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "1", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        res.refresh_from_db()
        assert res.muestra_id is None

    def test_carga_muestra_cancelada_400(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_cancelar(m.pk, actor=None, view="t", motivo="por test")
        m.refresh_from_db()
        assert m.estado == "CANCELADA"
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "1", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        res.refresh_from_db()
        assert res.muestra_id is None

    def test_carga_primer_resultado_transiciona_muestra_a_en_proceso(self):
        """B2.1: muestra RECIBIDA pasa a EN_PROCESO al asociarse al primer resultado."""
        sol, res = self._solicitud_en_proceso_con_resultado()
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
        m.refresh_from_db()
        assert m.estado == "EN_PROCESO"
        eventos = list(m.eventos.values_list("accion", "estado_anterior", "estado_nuevo"))
        assert ("EN_PROCESO", "RECIBIDA", "EN_PROCESO") in eventos
        assert AuditEvent.objects.filter(
            entity_type="laboratorio.Muestra",
            entity_id=str(m.pk),
            action="UPDATE",
            metadata__estado_nuevo="EN_PROCESO",
        ).exists()

    def test_carga_segundo_resultado_misma_muestra_idempotente(self):
        """B2.1: cargar de nuevo con la misma muestra (ya EN_PROCESO) no falla ni genera evento extra."""
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = self._muestra_recibida(sol)
        r1 = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "10", "muestra_id": m.pk}]},
            format="json",
        )
        assert r1.status_code == status.HTTP_200_OK
        m.refresh_from_db()
        assert m.estado == "EN_PROCESO"
        eventos_iniciales = m.eventos.filter(accion="EN_PROCESO").count()
        r2 = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "11", "muestra_id": m.pk}]},
            format="json",
        )
        assert r2.status_code == status.HTTP_200_OK
        m.refresh_from_db()
        assert m.estado == "EN_PROCESO"
        # No se duplicó la transición.
        assert m.eventos.filter(accion="EN_PROCESO").count() == eventos_iniciales

    def test_carga_muestra_tomada_no_recibida_400(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.pk,
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
            {
                "resultados": [
                    {"id": res.pk, "valor": "1", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_respuesta_incluye_muestra_id(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = self._muestra_recibida(sol)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "5", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        out_res = next(x for x in r.data["resultados"] if x["id"] == res.pk)
        assert out_res.get("muestra_id") == m.pk

    def test_paciente_corrupto_en_bd_rechaza(self):
        sol, res = self._solicitud_en_proceso_con_resultado()
        m = self._muestra_recibida(sol)
        otro = Paciente.objects.create(
            dni=str(uuid.uuid4().int)[-8:], nombre="O", apellido="P"
        )
        Muestra.objects.filter(pk=m.pk).update(paciente_id=otro.pk)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": res.pk, "valor": "1", "muestra_id": m.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestValidarConMuestraAPI(APITestCase):
    def setUp(self):
        suf = "B2VAL"
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
            dni="33334444", nombre="Bo", apellido="Test"
        )
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="Y", matricula="M-V", especialidad=esp
        )
        self.user_admin = User.objects.create_user(
            username="adm_val_b2",
            email="a@test.com",
            password="x",
            rol="admin",
            is_staff=True,
        )

    def test_validar_vacio_sigue_fallando(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_examen)
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_examen,
            valor_obtenido="",
        )
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_validar_sin_muestra_ok(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_examen)
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_examen,
            valor_obtenido="100",
        )
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/")
        assert r.status_code == status.HTTP_200_OK

    def test_validar_muestra_recibida_ok(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_examen)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_examen,
            valor_obtenido="100",
            muestra=m,
        )
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/")
        assert r.status_code == status.HTTP_200_OK

    def _solicitud_resultado_con_muestra(self, estado_muestra_final=None):
        """Crea solicitud EN_PROCESO con un resultado vinculado a muestra RECIBIDA.

        Si `estado_muestra_final` es provisto, transiciona la muestra a ese estado
        después de asociarla al resultado (simulando TOCTOU entre carga y validar).
        """
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_examen)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_examen,
            valor_obtenido="100",
            muestra=m,
        )
        if estado_muestra_final == "DESCARTADA":
            from laboratorio.muestra_estado import aplicar_descartar
            aplicar_descartar(m.pk, actor=None, view="t")
        elif estado_muestra_final == "CANCELADA":
            from laboratorio.muestra_estado import aplicar_cancelar
            aplicar_cancelar(m.pk, actor=None, view="t", motivo="test")
        return sol, m

    def test_validar_muestra_descartada_falla(self):
        """B2.1 TOCTOU defensivo: validar rechaza si muestra asociada pasó a DESCARTADA."""
        sol, m = self._solicitud_resultado_con_muestra(estado_muestra_final="DESCARTADA")
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        sol.refresh_from_db()
        assert sol.estado == "EN_PROCESO"

    def test_validar_muestra_cancelada_falla(self):
        """B2.1 TOCTOU defensivo: validar rechaza si muestra asociada pasó a CANCELADA."""
        sol, m = self._solicitud_resultado_con_muestra(estado_muestra_final="CANCELADA")
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        sol.refresh_from_db()
        assert sol.estado == "EN_PROCESO"

    def test_validar_releyendo_muestras_con_select_for_update(self):
        """B2.1: confirma que `validar` releyó el estado de las muestras dentro de la
        transacción (no usa el snapshot del momento de carga). Mutamos la muestra a
        un estado inválido vía servicio justo antes de invocar `validar`.
        """
        sol, m = self._solicitud_resultado_con_muestra()
        # Mutación posterior fuera de cliente (simula otro proceso en otra sesión).
        from laboratorio.muestra_estado import aplicar_rechazar
        aplicar_rechazar(m.pk, actor=None, view="t", motivo_rechazo="hemolisis")
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        sol.refresh_from_db()
        assert sol.estado == "EN_PROCESO"

    def test_validar_muestra_rechazada_falla(self):
        from laboratorio.muestra_estado import aplicar_rechazar

        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.tipo_examen)
        m = crear_muestra(
            solicitud=sol,
            tipo_muestra_id=self.tipo_muestra.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.tipo_examen,
            valor_obtenido="100",
            muestra=m,
        )
        aplicar_rechazar(m.pk, actor=None, view="t", motivo_rechazo="Calidad")
        self.client.force_authenticate(user=self.user_admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCargarMuestraPermisosAPI(APITestCase):
    def setUp(self):
        suf = "B2PRM"
        self.tm = TipoMuestra.objects.create(codigo=f"S{suf}", nombre="S", activo=True)
        self.te = TipoExamen.objects.create(
            codigo=f"G{suf}", nombre="G", tipo_muestra_requerida=self.tm, precio=1, activo=True
        )
        self.pac = Paciente.objects.create(dni="99990000", nombre="P", apellido="R")
        esp = Especialidad.objects.create(nombre=f"E{suf}")
        self.med = Medico.objects.create(
            nombre="M", apellido="D", matricula="MD", especialidad=esp
        )
        self.u_lab = User.objects.create_user(
            username="lb2", email="l@test.com", password="x", rol="laboratorio", is_staff=True
        )
        self.u_med = User.objects.create_user(
            username="mb2", email="m@test.com", password="x", rol="medico"
        )
        self.med.user = self.u_med
        self.med.save()
        self.sol = SolicitudExamen.objects.create(
            paciente=self.pac,
            medico_interno=self.med,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        self.sol.tipos_examen.add(self.te)
        self.res = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te, valor_obtenido=""
        )
        m = crear_muestra(
            solicitud=self.sol,
            tipo_muestra_id=self.tm.pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        self.m_recibida = m

    def test_laboratorio_puede_cargar_con_muestra(self):
        self.client.force_authenticate(user=self.u_lab)
        r = self.client.post(
            f"/api/lab/solicitudes/{self.sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": self.res.pk, "valor": "10", "muestra_id": self.m_recibida.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK

    def test_medico_no_puede_cargar_con_muestra(self):
        self.client.force_authenticate(user=self.u_med)
        r = self.client.post(
            f"/api/lab/solicitudes/{self.sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": self.res.pk, "valor": "10", "muestra_id": self.m_recibida.pk},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN
