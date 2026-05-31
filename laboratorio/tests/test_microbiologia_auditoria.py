"""
Tests de auditoría — LIMS Fase B3-audit (endurecimiento microbiología).

Verifica que metadata y snapshots genéricos no incluyan codigo_barra ni
resultados microbiológicos crudos, conservando IDs técnicos.
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
from auditoria.snapshot import safe_model_snapshot
from laboratorio.microbiologia_estado import (
    crear_estudio,
    crear_informe_borrador,
    crear_lectura,
    crear_resultado_antibiotico,
    crear_siembra,
)
from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_microbiologia import (
    AisladoMicrobiologico,
    Antibiograma,
    Antibiotico,
    EstudioMicrobiologia,
    IdentificacionMicroorganismo,
    InformeMicrobiologia,
    LecturaCultivo,
    MedioCultivo,
    Microorganismo,
    ResultadoAntibiotico,
    SiembraMicrobiologia,
)
from laboratorio.muestra_estado import aplicar_recibir, aplicar_tomar, crear_muestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()

SENSITIVE_BARCODE = "MICRO-CODE-SENSIBLE"
SENSITIVE_MIC = "CIM-SENSIBLE-123"
SENSITIVE_OBS = "OBS-MICRO-SENSIBLE"
SENSITIVE_INFORME = "TEXTO-INFORME-MICRO-SENSIBLE"


def _audit_blob(*events: AuditEvent) -> str:
    return json.dumps(
        [
            {
                "metadata": ev.metadata,
                "before_state": ev.before_state,
                "after_state": ev.after_state,
            }
            for ev in events
        ],
        ensure_ascii=False,
        default=str,
    )


def _muestra_con_barra(sol, tm, codigo_barra: str):
    m = crear_muestra(
        solicitud=sol,
        tipo_muestra_id=tm.pk,
        tipo_contenedor_id=None,
        observaciones="",
        actor=None,
        view="test_micro_auditoria",
        codigo_barra=codigo_barra,
    )
    aplicar_tomar(m.pk, actor=None, view="test_micro_auditoria")
    aplicar_recibir(m.pk, actor=None, view="test_micro_auditoria")
    m.refresh_from_db()
    return m


def _setup_solicitud(suf: str):
    tm = TipoMuestra.objects.create(codigo=f"TM{suf}", nombre="Sangre", activo=True)
    te = TipoExamen.objects.create(
        codigo=f"GLU{suf}",
        nombre="Glu",
        tipo_muestra_requerida=tm,
        precio=1,
        activo=True,
    )
    pac = Paciente.objects.create(dni=f"D{suf}", nombre="P", apellido="X")
    esp = Especialidad.objects.create(nombre=f"Esp {suf}")
    med = Medico.objects.create(nombre="Dr", apellido="X", matricula=f"M{suf}", especialidad=esp)
    sol = SolicitudExamen.objects.create(
        paciente=pac,
        medico_interno=med,
        origen_solicitud="EMR",
        estado="PENDIENTE",
    )
    sol.tipos_examen.add(te)
    return sol, tm, pac


def _setup_aislado_identificado(sol, tm, muestra, suf: str):
    medio = MedioCultivo.objects.create(codigo=f"AG{suf[:6]}", nombre="Agar sangre", activo=True)
    estudio = EstudioMicrobiologia.objects.create(
        solicitud=sol, muestra=muestra, paciente=sol.paciente
    )
    siembra = SiembraMicrobiologia.objects.create(
        estudio=estudio, muestra=muestra, medio=medio
    )
    EstudioMicrobiologia.objects.filter(pk=estudio.pk).update(estado="SEMBRADO")
    estudio.refresh_from_db()
    lectura = LecturaCultivo.objects.create(
        siembra=siembra, estudio=estudio, crecimiento="MODERADO"
    )
    micro = Microorganismo.objects.create(
        codigo=f"EC{suf[:6]}",
        nombre="E. coli",
        genero="Escherichia",
        especie="coli",
        activo=True,
    )
    aislado = AisladoMicrobiologico.objects.create(
        estudio=estudio, lectura_origen=lectura
    )
    IdentificacionMicroorganismo.objects.create(
        aislado=aislado,
        microorganismo=micro,
        metodo="MALDI-TOF",
        resultado="E. coli",
        confianza=99,
    )
    AisladoMicrobiologico.objects.filter(pk=aislado.pk).update(
        estado="IDENTIFICADO", microorganismo=micro
    )
    aislado.refresh_from_db()
    EstudioMicrobiologia.objects.filter(pk=estudio.pk).update(estado="ANTIBIOGRAMA")
    estudio.refresh_from_db()
    antibiograma = Antibiograma.objects.create(aislado=aislado)
    return {
        "sol": sol,
        "muestra": muestra,
        "estudio": estudio,
        "siembra": siembra,
        "lectura": lectura,
        "aislado": aislado,
        "antibiograma": antibiograma,
    }


@pytest.mark.django_db
class TestMicrobiologiaAuditoria(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_ma_{self.suf}",
            email=f"lma{self.suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.sol, self.tm, _ = _setup_solicitud(self.suf)
        self.muestra = _muestra_con_barra(self.sol, self.tm, SENSITIVE_BARCODE)
        self.medio = MedioCultivo.objects.create(
            codigo=f"AGS{self.suf}", nombre="Agar sangre", activo=True
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def test_micro_estudio_create_no_audita_codigo_barra(self):
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/lab/microbiologia/estudios/",
                {
                    "solicitud_id": self.sol.pk,
                    "muestra_id": self.muestra.pk,
                    "tipo_estudio": "CULTIVO_RUTINA",
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        estudio_id = r.json()["id"]
        ev = AuditEvent.objects.filter(
            entity_type=EstudioMicrobiologia._meta.label,
            entity_id=str(estudio_id),
            action="CREATE",
        ).first()
        self.assertIsNotNone(ev)
        blob = _audit_blob(ev)
        self.assertNotIn("codigo_barra", blob)
        self.assertNotIn(SENSITIVE_BARCODE, blob)
        meta = ev.metadata or {}
        self.assertIn("muestra_id", meta)
        self.assertIn("solicitud_id", meta)
        self.assertIn("estudio_id", meta)

    def test_micro_siembra_y_lectura_no_auditan_codigo_barra(self):
        estudio = EstudioMicrobiologia.objects.create(
            solicitud=self.sol,
            muestra=self.muestra,
            paciente=self.sol.paciente,
        )
        with self.captureOnCommitCallbacks(execute=True):
            siembra = crear_siembra(
                estudio_id=estudio.pk,
                medio_id=self.medio.pk,
                fecha_siembra=None,
                condicion_incubacion="",
                temperatura_c=None,
                atmosfera="",
                observaciones="obs siembra",
                actor=self.lab,
                view="test_micro_auditoria",
            )
            lectura = crear_lectura(
                siembra_id=siembra.pk,
                fecha_lectura=None,
                horas_incubacion=24,
                crecimiento="MODERADO",
                descripcion_colonias="colonias sensibles",
                tincion_gram="gram positivo",
                observaciones="obs lectura",
                es_preliminar=True,
                actor=self.lab,
                view="test_micro_auditoria",
            )

        ev_siembra = AuditEvent.objects.filter(
            entity_type=SiembraMicrobiologia._meta.label,
            entity_id=str(siembra.pk),
            action="CREATE",
        ).first()
        ev_lectura = AuditEvent.objects.filter(
            entity_type=LecturaCultivo._meta.label,
            entity_id=str(lectura.pk),
            action="CREATE",
        ).first()
        self.assertIsNotNone(ev_siembra)
        self.assertIsNotNone(ev_lectura)

        for ev in (ev_siembra, ev_lectura):
            blob = _audit_blob(ev)
            self.assertNotIn("codigo_barra", blob)
            self.assertNotIn(SENSITIVE_BARCODE, blob)

    def test_resultado_antibiotico_no_audita_cim_diametro_interpretacion(self):
        ctx = _setup_aislado_identificado(self.sol, self.tm, self.muestra, self.suf)
        ab = Antibiotico.objects.create(codigo=f"AB{self.suf[:6]}", nombre="Ampicilina")
        with self.captureOnCommitCallbacks(execute=True):
            resultado = crear_resultado_antibiotico(
                antibiograma_id=ctx["antibiograma"].pk,
                antibiotico_id=ab.pk,
                halo_mm="37.00",
                mic=SENSITIVE_MIC,
                interpretacion="R",
                observaciones=SENSITIVE_OBS,
                actor=self.lab,
                view="test_micro_auditoria",
            )

        ev = AuditEvent.objects.filter(
            entity_type=ResultadoAntibiotico._meta.label,
            entity_id=str(resultado.pk),
            action="CREATE",
        ).first()
        self.assertIsNotNone(ev)
        blob = _audit_blob(ev)
        for needle in (SENSITIVE_MIC, "37.00", '"R"', SENSITIVE_OBS, "codigo_barra"):
            self.assertNotIn(needle, blob, msg=f"Encontrado {needle!r} en auditoría")

        after = ev.after_state or {}
        self.assertNotIn(SENSITIVE_MIC, json.dumps(after, default=str))
        self.assertNotIn(SENSITIVE_OBS, json.dumps(after, default=str))
        self.assertTrue(
            after.get("mic") == "<resultado microbiológico redactado>"
            or "mic" not in after
        )
        self.assertTrue(
            after.get("interpretacion") == "<resultado microbiológico redactado>"
            or "interpretacion" not in after
        )

    def test_informe_microbiologia_snapshot_redacta_texto(self):
        ctx = _setup_aislado_identificado(self.sol, self.tm, self.muestra, self.suf)
        with self.captureOnCommitCallbacks(execute=True):
            informe = crear_informe_borrador(
                estudio_id=ctx["estudio"].pk,
                tipo="PRELIMINAR",
                texto=SENSITIVE_INFORME,
                observaciones="obs informe sensible",
                reemplaza_a_id=None,
                actor=self.lab,
                view="test_micro_auditoria",
            )

        ev = AuditEvent.objects.filter(
            entity_type=InformeMicrobiologia._meta.label,
            entity_id=str(informe.pk),
            action="CREATE",
        ).first()
        self.assertIsNotNone(ev)
        blob = _audit_blob(ev)
        self.assertNotIn(SENSITIVE_INFORME, blob)
        self.assertNotIn("obs informe sensible", blob)

        snap = safe_model_snapshot(informe)
        self.assertEqual(snap.get("texto"), "<texto clínico redactado>")
        self.assertNotIn(SENSITIVE_INFORME, json.dumps(snap, default=str))

    def test_micro_auditoria_conserva_ids_tecnicos(self):
        ctx = _setup_aislado_identificado(self.sol, self.tm, self.muestra, self.suf)
        ab = Antibiotico.objects.create(codigo=f"A2{self.suf[:6]}", nombre="Ceftriaxona")

        with self.captureOnCommitCallbacks(execute=True):
            estudio = crear_estudio(
                solicitud=ctx["sol"],
                muestra=ctx["muestra"],
                tipo_estudio="CULTIVO_RUTINA",
                observaciones="",
                actor=self.lab,
                view="test_micro_auditoria",
            )
            resultado = crear_resultado_antibiotico(
                antibiograma_id=ctx["antibiograma"].pk,
                antibiotico_id=ab.pk,
                halo_mm="20.00",
                mic="<=1",
                interpretacion="S",
                observaciones="",
                actor=self.lab,
                view="test_micro_auditoria",
            )

        ev_estudio = AuditEvent.objects.filter(
            entity_type=EstudioMicrobiologia._meta.label,
            entity_id=str(estudio.pk),
            action="CREATE",
        ).first()
        ev_resultado = AuditEvent.objects.filter(
            entity_type=ResultadoAntibiotico._meta.label,
            entity_id=str(resultado.pk),
            action="CREATE",
        ).first()
        self.assertIsNotNone(ev_estudio)
        self.assertIsNotNone(ev_resultado)

        meta_est = ev_estudio.metadata or {}
        meta_res = ev_resultado.metadata or {}
        self.assertEqual(meta_est.get("muestra_id"), ctx["muestra"].pk)
        self.assertEqual(meta_est.get("solicitud_id"), ctx["sol"].pk)
        self.assertEqual(meta_est.get("estudio_id"), estudio.pk)
        self.assertEqual(meta_res.get("muestra_id"), ctx["muestra"].pk)
        self.assertEqual(meta_res.get("solicitud_id"), ctx["sol"].pk)
        self.assertEqual(meta_res.get("estudio_id"), ctx["estudio"].pk)
        self.assertEqual(meta_res.get("antibiograma_id"), ctx["antibiograma"].pk)
        self.assertEqual(meta_res.get("resultado_antibiotico_id"), resultado.pk)
        self.assertEqual(meta_res.get("aislado_id"), ctx["aislado"].pk)
