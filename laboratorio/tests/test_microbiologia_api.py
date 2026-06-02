"""
Tests API — LIMS Fase B3.1 (Microbiología base).

Cubre:
- catálogo MedioCultivo (lectura/escritura por rol);
- creación de EstudioMicrobiologia con validaciones de muestra y permisos;
- siembras y lecturas con transiciones automáticas del estudio;
- cancelación con motivo obligatorio;
- bloqueos por estudio/siembra cancelada;
- auditoría.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
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
from laboratorio.muestra_estado import (
    aplicar_cancelar,
    aplicar_conservar,
    aplicar_descartar,
    aplicar_rechazar,
    aplicar_recibir,
    aplicar_tomar,
    crear_muestra,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


def _muestra_recibida(sol, tm):
    m = crear_muestra(
        solicitud=sol,
        tipo_muestra_id=tm.pk,
        tipo_contenedor_id=None,
        observaciones="",
        actor=None,
        view="t",
    )
    aplicar_tomar(m.pk, actor=None, view="t")
    aplicar_recibir(m.pk, actor=None, view="t")
    m.refresh_from_db()
    return m


def _muestra_conservada(sol, tm):
    m = _muestra_recibida(sol, tm)
    aplicar_conservar(m.pk, actor=None, view="t")
    m.refresh_from_db()
    return m


@pytest.mark.django_db
class TestMedioCultivoAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_mc_{self.suf}", email=f"lmc{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_mc_{self.suf}", email=f"amc{self.suf}@t.com",
            password="x", rol="admin", is_staff=True,
        )
        self.med = User.objects.create_user(
            username=f"med_mc_{self.suf}", email=f"mmc{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_mc_{self.suf}", email=f"pmc{self.suf}@t.com",
            password="x", rol="paciente",
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def test_anonimo_bloqueado(self):
        r = self.client.get("/api/lab/microbiologia/medios/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_laboratorio_lista_medios(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/lab/microbiologia/medios/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_paciente_no_lista_medios(self):
        self.client.force_authenticate(self.pac_u)
        r = self.client.get("/api/lab/microbiologia/medios/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_crea_medio(self):
        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/lab/microbiologia/medios/",
                {"codigo": f"AGS{self.suf}", "nombre": f"Agar {self.suf}", "tipo": "solido"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=MedioCultivo._meta.label,
                action="CREATE",
            ).exists()
        )

    def test_laboratorio_no_crea_medio(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/microbiologia/medios/",
            {"codigo": f"AGS{self.suf}", "nombre": f"X {self.suf}"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_alias_laboratorio_medios(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/microbiologia/medios/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestEstudioMicrobiologiaAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_em_{self.suf}", email=f"lem{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_em_{self.suf}", email=f"aem{self.suf}@t.com",
            password="x", rol="admin", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_em_{self.suf}", email=f"mem{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_em_{self.suf}", email=f"pem{self.suf}@t.com",
            password="x", rol="paciente",
        )
        self.esp = Especialidad.objects.create(nombre=f"Esp {self.suf}")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="X", matricula=f"M{self.suf}",
            especialidad=self.esp, user=self.med_user,
        )
        self.paciente = Paciente.objects.create(
            dni=f"D{self.suf}", nombre="P", apellido="X", user=self.pac_u,
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"TM{self.suf}", nombre="Sangre", activo=True
        )
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{self.suf}", nombre="Glu", tipo_muestra_requerida=self.tm,
            precio=1, activo=True,
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="PENDIENTE",
        )
        self.sol.tipos_examen.add(self.te)
        self.muestra = _muestra_recibida(self.sol, self.tm)
        self.medio = MedioCultivo.objects.create(
            codigo=f"AGS{self.suf}", nombre="Agar sangre", activo=True
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def _crear_estudio(self):
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
        return r.json()

    def test_anonimo_bloqueado(self):
        r = self.client.post(
            "/api/lab/microbiologia/estudios/",
            {"solicitud_id": self.sol.pk, "muestra_id": self.muestra.pk},
            format="json",
        )
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_laboratorio_crea_estudio(self):
        data = self._crear_estudio()
        self.assertEqual(data["estado"], "PENDIENTE")
        self.assertTrue(data["numero"].startswith("MIC-"))
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=EstudioMicrobiologia._meta.label,
                entity_id=str(data["id"]),
                action="CREATE",
            ).exists()
        )

    def test_api_crear_estudio_microbiologia_con_muestra_conservada(self):
        m = _muestra_conservada(self.sol, self.tm)
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/lab/microbiologia/estudios/",
                {
                    "solicitud_id": self.sol.pk,
                    "muestra_id": m.pk,
                    "tipo_estudio": "CULTIVO_RUTINA",
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertEqual(r.json()["estado"], "PENDIENTE")
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=EstudioMicrobiologia._meta.label,
                entity_id=str(r.json()["id"]),
                action="CREATE",
            ).exists()
        )

    def test_laboratorio_no_crea_estudio_con_muestra_rechazada(self):
        # rechazar la muestra antes
        aplicar_rechazar(self.muestra.pk, actor=None, view="t", motivo_rechazo="x")
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/microbiologia/estudios/",
            {"solicitud_id": self.sol.pk, "muestra_id": self.muestra.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_laboratorio_no_crea_estudio_con_muestra_descartada(self):
        aplicar_descartar(self.muestra.pk, actor=None, view="t")
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/microbiologia/estudios/",
            {"solicitud_id": self.sol.pk, "muestra_id": self.muestra.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_laboratorio_no_crea_estudio_con_muestra_pendiente_toma(self):
        m = crear_muestra(
            solicitud=self.sol, tipo_muestra_id=self.tm.pk, tipo_contenedor_id=None,
            observaciones="", actor=None, view="t",
        )
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/microbiologia/estudios/",
            {"solicitud_id": self.sol.pk, "muestra_id": m.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_laboratorio_no_crea_estudio_con_muestra_tomada(self):
        m = crear_muestra(
            solicitud=self.sol, tipo_muestra_id=self.tm.pk, tipo_contenedor_id=None,
            observaciones="", actor=None, view="t",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/microbiologia/estudios/",
            {"solicitud_id": self.sol.pk, "muestra_id": m.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_medico_no_crea_estudio(self):
        self.client.force_authenticate(self.med_user)
        r = self.client.post(
            "/api/lab/microbiologia/estudios/",
            {"solicitud_id": self.sol.pk, "muestra_id": self.muestra.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_paciente_no_lista_estudios(self):
        self.client.force_authenticate(self.pac_u)
        r = self.client.get("/api/lab/microbiologia/estudios/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_medico_ve_su_estudio(self):
        data = self._crear_estudio()
        self.client.force_authenticate(self.med_user)
        r = self.client.get(f"/api/lab/microbiologia/estudios/{data['id']}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_iniciar_estudio_idempotente(self):
        data = self._crear_estudio()
        eid = data["id"]
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r1 = self.client.post(f"/api/lab/microbiologia/estudios/{eid}/iniciar/", {}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r1.json()["estado"], "RECIBIDO")
        # Idempotente: invocar de nuevo no falla.
        r2 = self.client.post(f"/api/lab/microbiologia/estudios/{eid}/iniciar/", {}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.json()["estado"], "RECIBIDO")

    def test_cancelar_estudio_sin_motivo_falla(self):
        data = self._crear_estudio()
        eid = data["id"]
        self.client.force_authenticate(self.lab)
        r = self.client.post(f"/api/lab/microbiologia/estudios/{eid}/cancelar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelar_estudio_con_motivo(self):
        data = self._crear_estudio()
        eid = data["id"]
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/api/lab/microbiologia/estudios/{eid}/cancelar/",
                {"motivo": "muestra insuficiente"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertEqual(r.json()["estado"], "CANCELADO")
        # Auditoría con metadata.accion=cancelar
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=EstudioMicrobiologia._meta.label,
                entity_id=str(eid),
                action="UPDATE",
                metadata__accion="cancelar",
            ).exists()
        )

    def test_patch_estudio_no_cambia_estado(self):
        data = self._crear_estudio()
        eid = data["id"]
        self.client.force_authenticate(self.lab)
        r = self.client.patch(
            f"/api/lab/microbiologia/estudios/{eid}/",
            {"estado": "CANCELADO", "observaciones": "nota"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        e = EstudioMicrobiologia.objects.get(pk=eid)
        self.assertEqual(e.estado, "PENDIENTE")
        self.assertEqual(e.observaciones, "nota")


@pytest.mark.django_db
class TestSiembraLecturaAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_sl_{self.suf}", email=f"lsl{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_sl_{self.suf}", email=f"msl{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.esp = Especialidad.objects.create(nombre=f"Esp {self.suf}")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="X", matricula=f"M{self.suf}",
            especialidad=self.esp, user=self.med_user,
        )
        self.paciente = Paciente.objects.create(dni=f"D{self.suf}", nombre="P", apellido="X")
        self.tm = TipoMuestra.objects.create(codigo=f"TM{self.suf}", nombre="Sangre", activo=True)
        self.te = TipoExamen.objects.create(
            codigo=f"GLU{self.suf}", nombre="Glu", tipo_muestra_requerida=self.tm,
            precio=1, activo=True,
        )
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="EMR",
            estado="PENDIENTE",
        )
        self.sol.tipos_examen.add(self.te)
        self.muestra = _muestra_recibida(self.sol, self.tm)
        self.medio = MedioCultivo.objects.create(
            codigo=f"AGS{self.suf}", nombre="Agar sangre", activo=True
        )
        self.estudio = EstudioMicrobiologia.objects.create(
            solicitud=self.sol, muestra=self.muestra, paciente=self.paciente,
        )
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(self.lab)

    def test_crear_siembra_y_estudio_a_sembrado(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/lab/microbiologia/siembras/",
                {
                    "estudio_id": self.estudio.pk,
                    "medio_id": self.medio.pk,
                    "atmosfera": "aerobia",
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.estudio.refresh_from_db()
        self.assertEqual(self.estudio.estado, "SEMBRADO")
        # Auditoría CREATE de Siembra + UPDATE auto_sembrado del Estudio
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=SiembraMicrobiologia._meta.label,
                action="CREATE",
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=EstudioMicrobiologia._meta.label,
                entity_id=str(self.estudio.pk),
                action="UPDATE",
                metadata__accion="auto_sembrado",
            ).exists()
        )

    def test_api_crear_siembra_con_muestra_conservada(self):
        m = _muestra_conservada(self.sol, self.tm)
        estudio = EstudioMicrobiologia.objects.create(
            solicitud=self.sol, muestra=m, paciente=self.paciente,
        )
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/lab/microbiologia/siembras/",
                {
                    "estudio_id": estudio.pk,
                    "medio_id": self.medio.pk,
                    "atmosfera": "aerobia",
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        estudio.refresh_from_db()
        self.assertEqual(estudio.estado, "SEMBRADO")

    def test_no_sembrar_estudio_cancelado(self):
        EstudioMicrobiologia.objects.filter(pk=self.estudio.pk).update(estado="CANCELADO")
        r = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {"estudio_id": self.estudio.pk, "medio_id": self.medio.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_sembrar_medio_inactivo(self):
        self.medio.activo = False
        self.medio.save()
        r = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {"estudio_id": self.estudio.pk, "medio_id": self.medio.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def _crear_siembra(self):
        r = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {"estudio_id": self.estudio.pk, "medio_id": self.medio.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        return r.json()

    def test_crear_lectura(self):
        s = self._crear_siembra()
        r = self.client.post(
            "/api/lab/microbiologia/lecturas/",
            {"siembra_id": s["id"], "crecimiento": "SIN_DESARROLLO"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)

    def test_lectura_preliminar_avanza_estudio(self):
        s = self._crear_siembra()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/lab/microbiologia/lecturas/",
                {
                    "siembra_id": s["id"],
                    "crecimiento": "MODERADO",
                    "es_preliminar": True,
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.estudio.refresh_from_db()
        self.assertEqual(self.estudio.estado, "LECTURA_PRELIMINAR")

    def test_no_leer_estudio_cancelado(self):
        s = self._crear_siembra()
        EstudioMicrobiologia.objects.filter(pk=self.estudio.pk).update(estado="CANCELADO")
        r = self.client.post(
            "/api/lab/microbiologia/lecturas/",
            {"siembra_id": s["id"], "crecimiento": "PENDIENTE"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_leer_siembra_cancelada(self):
        s = self._crear_siembra()
        SiembraMicrobiologia.objects.filter(pk=s["id"]).update(estado="CANCELADA")
        r = self.client.post(
            "/api/lab/microbiologia/lecturas/",
            {"siembra_id": s["id"], "crecimiento": "PENDIENTE"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_medico_no_crea_siembra(self):
        self.client.force_authenticate(self.med_user)
        r = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {"estudio_id": self.estudio.pk, "medio_id": self.medio.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_alias_laboratorio_estudios(self):
        r = self.client.get("/api/laboratorio/microbiologia/estudios/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# B3.2 — Microorganismos / Aislados / Identificaciones (API)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMicroorganismoAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_mo_{self.suf}", email=f"lmo{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_mo_{self.suf}", email=f"amo{self.suf}@t.com",
            password="x", rol="admin", is_staff=True,
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_mo_{self.suf}", email=f"pmo{self.suf}@t.com",
            password="x", rol="paciente",
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def test_anonimo_bloqueado(self):
        r = self.client.get("/api/lab/microbiologia/microorganismos/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_laboratorio_lista_microorganismos(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/lab/microbiologia/microorganismos/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_admin_crea_microorganismo(self):
        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/lab/microbiologia/microorganismos/",
                {"codigo": f"EC{self.suf}", "nombre": "E. coli", "genero": "Escherichia", "especie": "coli"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=Microorganismo._meta.label,
                action="CREATE",
            ).exists()
        )

    def test_laboratorio_no_crea_microorganismo(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/microbiologia/microorganismos/",
            {"codigo": f"X{self.suf}", "nombre": "X"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_paciente_bloqueado(self):
        self.client.force_authenticate(self.pac_u)
        r = self.client.get("/api/lab/microbiologia/microorganismos/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_alias_laboratorio_microorganismos(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/microbiologia/microorganismos/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


def _setup_estudio_con_lectura(suf, lab_user, med_user=None):
    esp = Especialidad.objects.create(nombre=f"Esp {suf}")
    medico = Medico.objects.create(
        nombre="Dr", apellido="X", matricula=f"M{suf}",
        especialidad=esp, user=med_user,
    )
    paciente = Paciente.objects.create(dni=f"D{suf}", nombre="P", apellido="X")
    tm = TipoMuestra.objects.create(codigo=f"TM{suf}", nombre="Sangre", activo=True)
    te = TipoExamen.objects.create(
        codigo=f"GLU{suf}", nombre="Glu", tipo_muestra_requerida=tm,
        precio=1, activo=True,
    )
    sol = SolicitudExamen.objects.create(
        paciente=paciente, medico_interno=medico,
        origen_solicitud="EMR", estado="PENDIENTE",
    )
    sol.tipos_examen.add(te)
    muestra = _muestra_recibida(sol, tm)
    medio = MedioCultivo.objects.create(codigo=f"AGS{suf}", nombre="Agar sangre", activo=True)
    estudio = EstudioMicrobiologia.objects.create(
        solicitud=sol, muestra=muestra, paciente=paciente
    )
    siembra = SiembraMicrobiologia.objects.create(
        estudio=estudio, muestra=muestra, medio=medio
    )
    EstudioMicrobiologia.objects.filter(pk=estudio.pk).update(estado="SEMBRADO")
    estudio.refresh_from_db()
    lectura = LecturaCultivo.objects.create(
        siembra=siembra, estudio=estudio, crecimiento="MODERADO"
    )
    return {
        "sol": sol, "muestra": muestra, "estudio": estudio,
        "siembra": siembra, "lectura": lectura, "paciente": paciente,
        "medico": medico,
    }


@pytest.mark.django_db
class TestAisladoAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_ai_{self.suf}", email=f"lai{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_ai_{self.suf}", email=f"mai{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_ai_{self.suf}", email=f"pai{self.suf}@t.com",
            password="x", rol="paciente",
        )
        self.ctx = _setup_estudio_con_lectura(self.suf, self.lab, self.med_user)
        self.micro = Microorganismo.objects.create(
            codigo=f"EC{self.suf}", nombre="E. coli",
            genero="Escherichia", especie="coli", activo=True,
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def _post_aislado(self, **extra):
        body = {
            "estudio_id": self.ctx["estudio"].pk,
            "lectura_id": self.ctx["lectura"].pk,
        }
        body.update(extra)
        return self.client.post("/api/lab/microbiologia/aislados/", body, format="json")

    def test_anonimo_bloqueado(self):
        r = self._post_aislado()
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_laboratorio_crea_aislado(self):
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self._post_aislado(significancia="SIGNIFICATIVO", requiere_antibiograma=True)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        data = r.json()
        self.assertEqual(data["estado"], "SOSPECHADO")
        self.assertTrue(data["requiere_antibiograma"])
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=AisladoMicrobiologico._meta.label,
                action="CREATE",
            ).exists()
        )

    def test_medico_no_crea_aislado(self):
        self.client.force_authenticate(self.med_user)
        r = self._post_aislado()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_paciente_no_crea_aislado(self):
        self.client.force_authenticate(self.pac_u)
        r = self._post_aislado()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_lectura_de_otro_estudio_falla(self):
        otro = _setup_estudio_con_lectura(uuid.uuid4().hex[:8], self.lab, None)
        self.client.force_authenticate(self.lab)
        r = self._post_aislado(lectura_id=otro["lectura"].pk)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_estudio_cancelado_bloquea(self):
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="CANCELADO")
        self.client.force_authenticate(self.lab)
        r = self._post_aislado()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_microorganismo_inactivo_bloquea(self):
        self.micro.activo = False
        self.micro.save()
        self.client.force_authenticate(self.lab)
        r = self._post_aislado(microorganismo_id=self.micro.pk)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_descartar_aislado_con_motivo(self):
        self.client.force_authenticate(self.lab)
        r = self._post_aislado()
        aid = r.json()["id"]
        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                f"/api/lab/microbiologia/aislados/{aid}/descartar/",
                {"motivo": "contaminación"},
                format="json",
            )
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.content)
        self.assertEqual(r2.json()["estado"], "DESCARTADO")
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=AisladoMicrobiologico._meta.label,
                entity_id=str(aid),
                action="UPDATE",
                metadata__accion="descartar_aislado",
            ).exists()
        )

    def test_descartar_aislado_sin_motivo_falla(self):
        self.client.force_authenticate(self.lab)
        r = self._post_aislado()
        aid = r.json()["id"]
        r2 = self.client.post(
            f"/api/lab/microbiologia/aislados/{aid}/descartar/",
            {},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_aislado_no_cambia_estado(self):
        self.client.force_authenticate(self.lab)
        r = self._post_aislado()
        aid = r.json()["id"]
        r2 = self.client.patch(
            f"/api/lab/microbiologia/aislados/{aid}/",
            {"estado": "IDENTIFICADO", "descripcion": "nota"},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        a = AisladoMicrobiologico.objects.get(pk=aid)
        self.assertEqual(a.estado, "SOSPECHADO")
        self.assertEqual(a.descripcion, "nota")

    def test_alias_laboratorio_aislados(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/microbiologia/aislados/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestIdentificacionAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_id_{self.suf}", email=f"lid{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_id_{self.suf}", email=f"mid{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.ctx = _setup_estudio_con_lectura(self.suf, self.lab, self.med_user)
        self.micro = Microorganismo.objects.create(
            codigo=f"EC{self.suf}", nombre="E. coli",
            genero="Escherichia", especie="coli", activo=True,
        )
        self.aislado = AisladoMicrobiologico.objects.create(
            estudio=self.ctx["estudio"], lectura_origen=self.ctx["lectura"]
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def _post_identificacion(self, **extra):
        body = {
            "aislado_id": self.aislado.pk,
            "microorganismo_id": self.micro.pk,
            "metodo": "MALDI-TOF",
            "resultado": "E. coli",
            "confianza": "98.50",
        }
        body.update(extra)
        return self.client.post("/api/lab/microbiologia/identificaciones/", body, format="json")

    def test_laboratorio_crea_identificacion_actualiza_aislado_y_estudio(self):
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self._post_identificacion()
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.aislado.refresh_from_db()
        self.ctx["estudio"].refresh_from_db()
        self.assertEqual(self.aislado.estado, "IDENTIFICADO")
        self.assertEqual(self.aislado.microorganismo_id, self.micro.pk)
        self.assertEqual(self.ctx["estudio"].estado, "IDENTIFICACION")
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=IdentificacionMicroorganismo._meta.label,
                action="CREATE",
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=EstudioMicrobiologia._meta.label,
                entity_id=str(self.ctx["estudio"].pk),
                action="UPDATE",
                metadata__accion="auto_identificacion",
            ).exists()
        )

    def test_no_identificar_aislado_descartado(self):
        AisladoMicrobiologico.objects.filter(pk=self.aislado.pk).update(estado="DESCARTADO")
        self.client.force_authenticate(self.lab)
        r = self._post_identificacion()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_identificar_estudio_cancelado(self):
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="CANCELADO")
        self.client.force_authenticate(self.lab)
        r = self._post_identificacion()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_microorganismo_inactivo_falla(self):
        self.micro.activo = False
        self.micro.save()
        self.client.force_authenticate(self.lab)
        r = self._post_identificacion()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_medico_no_crea_identificacion(self):
        self.client.force_authenticate(self.med_user)
        r = self._post_identificacion()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_identificacion_no_admite_patch(self):
        self.client.force_authenticate(self.lab)
        r = self._post_identificacion()
        iid = r.json()["id"]
        r2 = self.client.patch(
            f"/api/lab/microbiologia/identificaciones/{iid}/",
            {"resultado": "otro"},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_alias_laboratorio_identificaciones(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/microbiologia/identificaciones/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# B3.3 — API: Antibióticos / Antibiogramas / Resultados de antibiótico
# ---------------------------------------------------------------------------


def _setup_aislado_identificado(suf, lab_user, med_user=None):
    ctx = _setup_estudio_con_lectura(suf, lab_user, med_user)
    micro = Microorganismo.objects.create(
        codigo=f"EC{suf}", nombre="E. coli",
        genero="Escherichia", especie="coli", activo=True,
    )
    aislado = AisladoMicrobiologico.objects.create(
        estudio=ctx["estudio"], lectura_origen=ctx["lectura"]
    )
    IdentificacionMicroorganismo.objects.create(
        aislado=aislado, microorganismo=micro,
        metodo="MALDI-TOF", resultado="E. coli", confianza=99,
    )
    AisladoMicrobiologico.objects.filter(pk=aislado.pk).update(
        estado="IDENTIFICADO", microorganismo=micro
    )
    aislado.refresh_from_db()
    EstudioMicrobiologia.objects.filter(pk=ctx["estudio"].pk).update(estado="IDENTIFICACION")
    ctx["estudio"].refresh_from_db()
    ctx["aislado"] = aislado
    ctx["microorganismo"] = micro
    return ctx


@pytest.mark.django_db
class TestAntibioticoAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.admin = User.objects.create_user(
            username=f"adm_ab_{self.suf}", email=f"aab{self.suf}@t.com",
            password="x", rol="admin", is_staff=True,
        )
        self.lab = User.objects.create_user(
            username=f"lab_ab_{self.suf}", email=f"lab{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.med = User.objects.create_user(
            username=f"med_ab_{self.suf}", email=f"mab{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_ab_{self.suf}", email=f"pab{self.suf}@t.com",
            password="x", rol="paciente",
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def test_anonimo_bloqueado(self):
        r = self.client.get("/api/lab/microbiologia/antibioticos/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_paciente_bloqueado(self):
        self.client.force_authenticate(self.pac_u)
        r = self.client.get("/api/lab/microbiologia/antibioticos/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_laboratorio_lista_antibioticos(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/lab/microbiologia/antibioticos/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_admin_crea_antibiotico_y_audita(self):
        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/lab/microbiologia/antibioticos/",
                {"codigo": f"AB{self.suf}", "nombre": "Ampicilina", "familia": "betalactamicos"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=Antibiotico._meta.label, action="CREATE"
            ).exists()
        )

    def test_laboratorio_no_crea_antibiotico(self):
        self.client.force_authenticate(self.lab)
        r = self.client.post(
            "/api/lab/microbiologia/antibioticos/",
            {"codigo": f"AB{self.suf}", "nombre": "Ampicilina"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_desactiva_antibiotico_y_audita(self):
        self.client.force_authenticate(self.admin)
        ab = Antibiotico.objects.create(codigo=f"AB{self.suf}", nombre="Ampi")
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.patch(
                f"/api/lab/microbiologia/antibioticos/{ab.pk}/",
                {"activo": False},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        ab.refresh_from_db()
        self.assertFalse(ab.activo)
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=Antibiotico._meta.label,
                entity_id=str(ab.pk),
                action="UPDATE",
                metadata__accion="actualizar_antibiotico",
            ).exists()
        )

    def test_no_destroy(self):
        self.client.force_authenticate(self.admin)
        ab = Antibiotico.objects.create(codigo=f"AB{self.suf}", nombre="Ampi")
        r = self.client.delete(f"/api/lab/microbiologia/antibioticos/{ab.pk}/")
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_alias_laboratorio_antibioticos(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/microbiologia/antibioticos/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestAntibiogramaAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_ag_{self.suf}", email=f"lag{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_ag_{self.suf}", email=f"mag{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.med_user_otro = User.objects.create_user(
            username=f"med_ag2_{self.suf}", email=f"mag2{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_ag_{self.suf}", email=f"pag{self.suf}@t.com",
            password="x", rol="paciente",
        )
        self.ctx = _setup_aislado_identificado(self.suf, self.lab, self.med_user)
        self.client = APIClient(enforce_csrf_checks=False)

    def _post_antibiograma(self, **extra):
        body = {"aislado_id": self.ctx["aislado"].pk, "metodo": "Disco difusión"}
        body.update(extra)
        return self.client.post("/api/lab/microbiologia/antibiogramas/", body, format="json")

    def test_anonimo_bloqueado(self):
        r = self._post_antibiograma()
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_paciente_bloqueado(self):
        self.client.force_authenticate(self.pac_u)
        r = self._post_antibiograma()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_medico_no_crea_antibiograma(self):
        self.client.force_authenticate(self.med_user)
        r = self._post_antibiograma()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_laboratorio_crea_antibiograma_y_avanza_estudio(self):
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self._post_antibiograma()
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        data = r.json()
        self.assertEqual(data["estado"], "PENDIENTE")
        self.ctx["estudio"].refresh_from_db()
        self.assertEqual(self.ctx["estudio"].estado, "ANTIBIOGRAMA")
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=Antibiograma._meta.label, action="CREATE",
                metadata__accion="crear_antibiograma",
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=EstudioMicrobiologia._meta.label,
                entity_id=str(self.ctx["estudio"].pk),
                action="UPDATE",
                metadata__accion="auto_antibiograma",
            ).exists()
        )

    def test_aislado_descartado_devuelve_400(self):
        AisladoMicrobiologico.objects.filter(pk=self.ctx["aislado"].pk).update(estado="DESCARTADO")
        self.client.force_authenticate(self.lab)
        r = self._post_antibiograma()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_aislado_no_identificado_devuelve_400(self):
        AisladoMicrobiologico.objects.filter(pk=self.ctx["aislado"].pk).update(
            estado="SOSPECHADO", microorganismo=None
        )
        self.client.force_authenticate(self.lab)
        r = self._post_antibiograma()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_estudio_cancelado_devuelve_400(self):
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="CANCELADO")
        self.client.force_authenticate(self.lab)
        r = self._post_antibiograma()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_completar_sin_resultados_falla(self):
        self.client.force_authenticate(self.lab)
        r = self._post_antibiograma()
        ag_id = r.json()["id"]
        r2 = self.client.post(
            f"/api/lab/microbiologia/antibiogramas/{ag_id}/completar/", {}, format="json"
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelar_sin_motivo_falla(self):
        self.client.force_authenticate(self.lab)
        r = self._post_antibiograma()
        ag_id = r.json()["id"]
        r2 = self.client.post(
            f"/api/lab/microbiologia/antibiogramas/{ag_id}/cancelar/", {}, format="json"
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelar_con_motivo_audita(self):
        self.client.force_authenticate(self.lab)
        r = self._post_antibiograma()
        ag_id = r.json()["id"]
        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                f"/api/lab/microbiologia/antibiogramas/{ag_id}/cancelar/",
                {"motivo": "muestra contaminada"},
                format="json",
            )
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.content)
        self.assertEqual(r2.json()["estado"], "CANCELADO")
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=Antibiograma._meta.label,
                entity_id=str(ag_id),
                action="UPDATE",
                metadata__accion="cancelar_antibiograma",
            ).exists()
        )

    def test_patch_antibiograma_completo_falla(self):
        self.client.force_authenticate(self.lab)
        r = self._post_antibiograma()
        ag_id = r.json()["id"]
        Antibiograma.objects.filter(pk=ag_id).update(estado="COMPLETO")
        r2 = self.client.patch(
            f"/api/lab/microbiologia/antibiogramas/{ag_id}/",
            {"observaciones": "x"},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_medico_lee_solo_su_antibiograma(self):
        self.client.force_authenticate(self.lab)
        r = self._post_antibiograma()
        ag_id = r.json()["id"]
        # Médico vinculado: ve el antibiograma.
        self.client.force_authenticate(self.med_user)
        r2 = self.client.get(f"/api/lab/microbiologia/antibiogramas/{ag_id}/")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        # Médico ajeno: no ve.
        self.client.force_authenticate(self.med_user_otro)
        r3 = self.client.get(f"/api/lab/microbiologia/antibiogramas/{ag_id}/")
        self.assertEqual(r3.status_code, status.HTTP_404_NOT_FOUND)

    def test_alias_laboratorio_antibiogramas(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/microbiologia/antibiogramas/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestResultadoAntibioticoAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_ra_{self.suf}", email=f"lra{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_ra_{self.suf}", email=f"mra{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.ctx = _setup_aislado_identificado(self.suf, self.lab, self.med_user)
        self.antibiograma = Antibiograma.objects.create(aislado=self.ctx["aislado"])
        # Estudio queda en IDENTIFICACION; lo subimos a ANTIBIOGRAMA igual que el flujo real.
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        self.ctx["estudio"].refresh_from_db()
        self.ab = Antibiotico.objects.create(codigo=f"AB{self.suf}", nombre="Ampicilina")
        self.ab2 = Antibiotico.objects.create(codigo=f"AB2{self.suf}", nombre="Ceftriaxona")
        self.ab_inactivo = Antibiotico.objects.create(
            codigo=f"AB3{self.suf}", nombre="X", activo=False
        )
        self.client = APIClient(enforce_csrf_checks=False)

    def _post_resultado(self, **extra):
        body = {
            "antibiograma_id": self.antibiograma.pk,
            "antibiotico_id": self.ab.pk,
            "interpretacion": "S",
            "halo_mm": "20.00",
        }
        body.update(extra)
        return self.client.post(
            "/api/lab/microbiologia/resultados-antibiotico/", body, format="json"
        )

    def test_laboratorio_carga_resultado_y_pasa_a_en_proceso(self):
        self.client.force_authenticate(self.lab)
        with self.captureOnCommitCallbacks(execute=True):
            r = self._post_resultado()
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.antibiograma.refresh_from_db()
        self.assertEqual(self.antibiograma.estado, "EN_PROCESO")
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=ResultadoAntibiotico._meta.label, action="CREATE"
            ).exists()
        )

    def test_duplicar_antibiotico_falla(self):
        self.client.force_authenticate(self.lab)
        r = self._post_resultado()
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        r2 = self._post_resultado(interpretacion="R")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_antibiotico_inactivo_falla(self):
        self.client.force_authenticate(self.lab)
        r = self._post_resultado(antibiotico_id=self.ab_inactivo.pk)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_se_carga_si_antibiograma_completo(self):
        self.client.force_authenticate(self.lab)
        r = self._post_resultado()
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        Antibiograma.objects.filter(pk=self.antibiograma.pk).update(estado="COMPLETO")
        r2 = self._post_resultado(antibiotico_id=self.ab2.pk, interpretacion="R")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_se_carga_si_antibiograma_cancelado(self):
        Antibiograma.objects.filter(pk=self.antibiograma.pk).update(estado="CANCELADO")
        self.client.force_authenticate(self.lab)
        r = self._post_resultado()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_completar_con_resultados_funciona(self):
        self.client.force_authenticate(self.lab)
        self._post_resultado()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/api/lab/microbiologia/antibiogramas/{self.antibiograma.pk}/completar/",
                {}, format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.antibiograma.refresh_from_db()
        self.assertEqual(self.antibiograma.estado, "COMPLETO")
        self.assertIsNotNone(self.antibiograma.fecha_resultado)
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=Antibiograma._meta.label,
                entity_id=str(self.antibiograma.pk),
                action="UPDATE",
                metadata__accion="completar_antibiograma",
            ).exists()
        )

    def test_patch_resultado_bloqueado_si_completo(self):
        self.client.force_authenticate(self.lab)
        r = self._post_resultado()
        rid = r.json()["id"]
        Antibiograma.objects.filter(pk=self.antibiograma.pk).update(estado="COMPLETO")
        r2 = self.client.patch(
            f"/api/lab/microbiologia/resultados-antibiotico/{rid}/",
            {"interpretacion": "R"},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_alias_laboratorio_resultados(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/microbiologia/resultados-antibiotico/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestInformeMicrobiologiaAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_inf_{self.suf}", email=f"linf{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_inf_{self.suf}", email=f"ainf{self.suf}@t.com",
            password="x", rol="admin", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_inf_{self.suf}", email=f"minf{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.med_user_otro = User.objects.create_user(
            username=f"med_inf2_{self.suf}", email=f"minf2{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.pac_u = User.objects.create_user(
            username=f"pac_inf_{self.suf}", email=f"pinf{self.suf}@t.com",
            password="x", rol="paciente",
        )
        self.ctx = _setup_estudio_con_lectura(self.suf, self.lab, self.med_user)
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        self.ctx["estudio"].refresh_from_db()
        self.client = APIClient(enforce_csrf_checks=False)

    def _post_informe(self, tipo="FINAL", texto="borrador", estudio_id=None):
        body = {
            "estudio_id": estudio_id or self.ctx["estudio"].pk,
            "tipo": tipo,
            "texto": texto,
        }
        return self.client.post("/api/lab/microbiologia/informes/", body, format="json")

    def test_laboratorio_crea_preliminar(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="PRELIMINAR", texto="nota")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        self.assertEqual(r.json()["tipo"], "PRELIMINAR")
        self.assertEqual(r.json()["estado"], "BORRADOR")

    def test_final_sin_preliminar_emit_y_estudio_listo(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="borrador final")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        iid = r.json()["id"]
        r2 = self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/emitir/",
            {"texto": "Informe final cultivo."},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.content)
        self.ctx["estudio"].refresh_from_db()
        self.assertEqual(self.ctx["estudio"].estado, "LISTO_PARA_VALIDAR")

    def test_segundo_final_devuelve_400(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="a")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        r2 = self._post_informe(tipo="FINAL", texto="b")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_laboratorio_validar_falla_403(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="x")
        iid = r.json()["id"]
        self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/emitir/",
            {"texto": "Final emitido."},
            format="json",
        )
        r2 = self.client.post(f"/api/lab/microbiologia/informes/{iid}/validar/", {}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_valida_final(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="x")
        iid = r.json()["id"]
        self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/emitir/",
            {"texto": "Final para validar."},
            format="json",
        )
        self.client.force_authenticate(self.admin)
        r2 = self.client.post(f"/api/lab/microbiologia/informes/{iid}/validar/", {}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.content)
        self.assertEqual(r2.json()["estado"], "VALIDADO")
        self.ctx["estudio"].refresh_from_db()
        self.assertEqual(self.ctx["estudio"].estado, "VALIDADO")

    def test_medico_lee_informe_final(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="x")
        iid = r.json()["id"]
        self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/emitir/",
            {"texto": "Texto final."},
            format="json",
        )
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/lab/microbiologia/informes/{iid}/validar/", {}, format="json")
        self.client.force_authenticate(self.med_user)
        r2 = self.client.get(f"/api/lab/microbiologia/informes/{iid}/")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)

    def test_medico_ajeno_no_lee(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="x")
        iid = r.json()["id"]
        self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/emitir/",
            {"texto": "Texto."},
            format="json",
        )
        self.client.force_authenticate(self.med_user_otro)
        r2 = self.client.get(f"/api/lab/microbiologia/informes/{iid}/")
        self.assertEqual(r2.status_code, status.HTTP_404_NOT_FOUND)

    def test_paciente_bloqueado(self):
        self.client.force_authenticate(self.pac_u)
        r = self._post_informe()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_anular_exige_motivo(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="PRELIMINAR", texto="x")
        iid = r.json()["id"]
        r2 = self.client.post(f"/api/lab/microbiologia/informes/{iid}/anular/", {}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anular_con_motivo_audita(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="PRELIMINAR", texto="x")
        iid = r.json()["id"]
        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                f"/api/lab/microbiologia/informes/{iid}/anular/",
                {"motivo": "error de tipeo"},
                format="json",
            )
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.content)
        self.assertEqual(r2.json()["estado"], "ANULADO")
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=InformeMicrobiologia._meta.label,
                entity_id=str(iid),
                action="UPDATE",
                metadata__accion="anular_informe",
            ).exists()
        )

    def test_no_patch_informe_validado(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="x")
        iid = r.json()["id"]
        self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/emitir/",
            {"texto": "Emitido."},
            format="json",
        )
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/lab/microbiologia/informes/{iid}/validar/", {}, format="json")
        self.client.force_authenticate(self.lab)
        r2 = self.client.patch(
            f"/api/lab/microbiologia/informes/{iid}/",
            {"texto": "cambio no permitido"},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_emitir_audita(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="x")
        iid = r.json()["id"]
        with self.captureOnCommitCallbacks(execute=True):
            r2 = self.client.post(
                f"/api/lab/microbiologia/informes/{iid}/emitir/",
                {"texto": "Emitido con auditoría."},
                format="json",
            )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertTrue(
            AuditEvent.objects.filter(
                entity_type=InformeMicrobiologia._meta.label,
                entity_id=str(iid),
                action="UPDATE",
                metadata__accion="emitir_informe",
            ).exists()
        )

    def test_marcar_informado_estudio(self):
        self.client.force_authenticate(self.lab)
        r = self._post_informe(tipo="FINAL", texto="x")
        iid = r.json()["id"]
        self.client.post(
            f"/api/lab/microbiologia/informes/{iid}/emitir/",
            {"texto": "Final."},
            format="json",
        )
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/lab/microbiologia/informes/{iid}/validar/", {}, format="json")
        self.client.force_authenticate(self.lab)
        r3 = self.client.post(
            f"/api/lab/microbiologia/estudios/{self.ctx['estudio'].pk}/marcar-informado/",
            {},
            format="json",
        )
        self.assertEqual(r3.status_code, status.HTTP_200_OK, r3.content)
        self.assertEqual(r3.json()["estado"], "INFORMADO")

    def test_alias_laboratorio_informes(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get("/api/laboratorio/microbiologia/informes/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# B3-frontend-validación-A — estudios cerrados bloquean operación técnica
# ---------------------------------------------------------------------------


def _promover_estudio_a_validado(client, lab, admin, estudio_pk):
    client.force_authenticate(lab)
    r = client.post(
        "/api/lab/microbiologia/informes/",
        {"estudio_id": estudio_pk, "tipo": "FINAL", "texto": "x"},
        format="json",
    )
    assert r.status_code == status.HTTP_201_CREATED, r.content
    iid = r.json()["id"]
    client.post(
        f"/api/lab/microbiologia/informes/{iid}/emitir/",
        {"texto": "Final."},
        format="json",
    )
    client.force_authenticate(admin)
    r2 = client.post(f"/api/lab/microbiologia/informes/{iid}/validar/", {}, format="json")
    assert r2.status_code == status.HTTP_200_OK, r2.content
    estudio = EstudioMicrobiologia.objects.get(pk=estudio_pk)
    assert estudio.estado == "VALIDADO"
    return estudio


def _promover_estudio_a_informado(client, lab, admin, estudio_pk):
    _promover_estudio_a_validado(client, lab, admin, estudio_pk)
    client.force_authenticate(lab)
    r = client.post(
        f"/api/lab/microbiologia/estudios/{estudio_pk}/marcar-informado/",
        {},
        format="json",
    )
    assert r.status_code == status.HTTP_200_OK, r.content
    estudio = EstudioMicrobiologia.objects.get(pk=estudio_pk)
    assert estudio.estado == "INFORMADO"
    return estudio


@pytest.mark.django_db
class TestEstudioMicroCerradoOperacionAPI(TestCase):
    """CANCELADO / VALIDADO / INFORMADO bloquean mutaciones técnicas."""

    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_cerr_{self.suf}", email=f"lc{self.suf}@t.com",
            password="x", rol="laboratorio", is_staff=True,
        )
        self.admin = User.objects.create_user(
            username=f"adm_cerr_{self.suf}", email=f"ac{self.suf}@t.com",
            password="x", rol="admin", is_staff=True,
        )
        self.med_user = User.objects.create_user(
            username=f"med_cerr_{self.suf}", email=f"mc{self.suf}@t.com",
            password="x", rol="medico",
        )
        self.ctx = _setup_aislado_identificado(self.suf, self.lab, self.med_user)
        self.antibiograma = Antibiograma.objects.create(aislado=self.ctx["aislado"])
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        self.ctx["estudio"].refresh_from_db()
        self.ab = Antibiotico.objects.create(codigo=f"AB{self.suf}", nombre="Ampicilina")
        self.medio = MedioCultivo.objects.get(pk=self.ctx["siembra"].medio_id)
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(self.lab)

    def test_validado_bloquea_operaciones_tecnicas(self):
        estudio_pk = self.ctx["estudio"].pk
        _promover_estudio_a_validado(self.client, self.lab, self.admin, estudio_pk)
        n_siembras = SiembraMicrobiologia.objects.filter(estudio_id=estudio_pk).count()
        n_audit_siembra = AuditEvent.objects.filter(
            entity_type=SiembraMicrobiologia._meta.label, action="CREATE"
        ).count()

        r_siembra = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {"estudio_id": estudio_pk, "medio_id": self.medio.pk, "atmosfera": "aerobia"},
            format="json",
        )
        self.assertEqual(r_siembra.status_code, status.HTTP_400_BAD_REQUEST)

        r_aislado = self.client.post(
            "/api/lab/microbiologia/aislados/",
            {
                "estudio_id": estudio_pk,
                "lectura_id": self.ctx["lectura"].pk,
            },
            format="json",
        )
        self.assertEqual(r_aislado.status_code, status.HTTP_400_BAD_REQUEST)

        r_resultado = self.client.post(
            "/api/lab/microbiologia/resultados-antibiotico/",
            {
                "antibiograma_id": self.antibiograma.pk,
                "antibiotico_id": self.ab.pk,
                "interpretacion": "S",
            },
            format="json",
        )
        self.assertEqual(r_resultado.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            SiembraMicrobiologia.objects.filter(estudio_id=estudio_pk).count(),
            n_siembras,
        )
        self.assertEqual(
            AuditEvent.objects.filter(
                entity_type=SiembraMicrobiologia._meta.label, action="CREATE"
            ).count(),
            n_audit_siembra,
        )

    def test_informado_bloquea_operaciones_tecnicas(self):
        estudio_pk = self.ctx["estudio"].pk
        _promover_estudio_a_informado(self.client, self.lab, self.admin, estudio_pk)

        r_siembra = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {"estudio_id": estudio_pk, "medio_id": self.medio.pk},
            format="json",
        )
        self.assertEqual(r_siembra.status_code, status.HTTP_400_BAD_REQUEST)

        r_lectura = self.client.post(
            "/api/lab/microbiologia/lecturas/",
            {
                "siembra_id": self.ctx["siembra"].pk,
                "crecimiento": "MODERADO",
            },
            format="json",
        )
        self.assertEqual(r_lectura.status_code, status.HTTP_400_BAD_REQUEST)

        r_aislado = self.client.post(
            "/api/lab/microbiologia/aislados/",
            {
                "estudio_id": estudio_pk,
                "lectura_id": self.ctx["lectura"].pk,
            },
            format="json",
        )
        self.assertEqual(r_aislado.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validado_permite_marcar_informado(self):
        estudio_pk = self.ctx["estudio"].pk
        _promover_estudio_a_validado(self.client, self.lab, self.admin, estudio_pk)
        r = self.client.post(
            f"/api/lab/microbiologia/estudios/{estudio_pk}/marcar-informado/",
            {},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertEqual(r.json()["estado"], "INFORMADO")

    def test_cancelado_sigue_bloqueando_siembra(self):
        EstudioMicrobiologia.objects.filter(pk=self.ctx["estudio"].pk).update(estado="CANCELADO")
        r = self.client.post(
            "/api/lab/microbiologia/siembras/",
            {"estudio_id": self.ctx["estudio"].pk, "medio_id": self.medio.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
