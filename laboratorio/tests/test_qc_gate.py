"""Gate IQC Fase 1: corrida ACEPTADA hoy en equipo default; bloqueo en carga y validar."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_qc import CorridaQC, EquipoAnalizador, LoteControl, MaterialControl
from laboratorio.qc_service import (
    QcGateError,
    estado_iqc_solicitud,
    get_equipo_iqc_default,
    validar_qc_para_cierre,
    verificar_iqc_para_solicitud,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class _FakeSolicitud:
    def __init__(self, examen_ids):
        self.id = 1
        self._ids = list(examen_ids)

    @property
    def tipos_examen(self):
        return _Values(self._ids)

    @property
    def paneles(self):
        class _Empty:
            def prefetch_related(self, *_a):
                return self

            def all(self):
                return []

        return _Empty()

    @property
    def resultados(self):
        class _Empty:
            def values_list(self, *_a, **_k):
                return self

            def distinct(self):
                return []

        return _Empty()


class _Values:
    def __init__(self, ids):
        self._ids = ids

    def values_list(self, *_a, **_k):
        return self

    def __iter__(self):
        return iter(self._ids)


class TestQcGateEquipo(TestCase):
    def setUp(self):
        self.muestra = TipoMuestra.objects.create(codigo="SANGRE_QG", nombre="Sangre QG")
        self.examen = TipoExamen.objects.create(
            codigo="GLU_QG",
            nombre="Glucosa QG",
            tipo_muestra_requerida=self.muestra,
            tipo_resultado="NUMERICO",
        )
        self.equipo = EquipoAnalizador.objects.create(
            codigo="CM260",
            nombre="Autoanalizador CM260",
            marca_modelo="CM260",
            activo=True,
        )
        self.examen.equipo_analizador = self.equipo
        self.examen.save(update_fields=["equipo_analizador"])
        self.mat = MaterialControl.objects.create(
            nombre="Ctrl GLU S1",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=self.examen,
            equipo=self.equipo,
            media_target=Decimal("100"),
            de_target=Decimal("5"),
            activo=True,
        )
        self.lote = LoteControl.objects.create(
            material=self.mat,
            codigo_lote="L-QG",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        self.solicitud = _FakeSolicitud([self.examen.id])

    def _corrida(self, estado, minutes_ago=0, con_equipo=True):
        return CorridaQC.objects.create(
            lote_control=self.lote,
            equipo=self.equipo if con_equipo else None,
            fecha=timezone.now() - timedelta(minutes=minutes_ago),
            estado=estado,
        )

    def test_get_equipo_default_cm260(self):
        self.assertEqual(get_equipo_iqc_default().id, self.equipo.id)

    def test_aceptada_con_equipo_ok(self):
        self._corrida(CorridaQC.Estado.ACEPTADA, minutes_ago=5)
        validar_qc_para_cierre(self.solicitud)

    def test_aceptada_sin_equipo_no_cuenta(self):
        self._corrida(CorridaQC.Estado.ACEPTADA, minutes_ago=5, con_equipo=False)
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        self.assertIn("sin equipo", str(ctx.exception).lower())

    def test_rechazo_previo_y_aceptada_posterior_ok(self):
        self._corrida(CorridaQC.Estado.RECHAZADA, minutes_ago=60)
        self._corrida(CorridaQC.Estado.ACEPTADA, minutes_ago=5)
        validar_qc_para_cierre(self.solicitud)

    def test_ultima_rechazada_bloquea(self):
        self._corrida(CorridaQC.Estado.ACEPTADA, minutes_ago=60)
        self._corrida(CorridaQC.Estado.RECHAZADA, minutes_ago=5)
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        self.assertIn("GLU_QG", str(ctx.exception))
        self.assertIn("rechazado", str(ctx.exception).lower())

    def test_sin_corrida_bloquea(self):
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        self.assertIn("Sin corrida", str(ctx.exception))

    def test_estado_iqc_precheck(self):
        st = estado_iqc_solicitud(self.solicitud)
        self.assertFalse(st["ok"])
        self.assertTrue(st["aplicable"])
        self.assertEqual(st["equipo"]["codigo"], "CM260")
        self._corrida(CorridaQC.Estado.ACEPTADA)
        st2 = estado_iqc_solicitud(self.solicitud)
        self.assertTrue(st2["ok"])

    def test_override_admin(self):
        admin = User.objects.create_user(
            username="admin_qc", email="a@t.com", password="x", rol="admin", is_staff=True
        )
        validar_qc_para_cierre(
            self.solicitud,
            confirmar_qc_override=True,
            motivo_override="Urgencia documentada",
            actor=admin,
        )

    def test_carga_sin_override(self):
        with self.assertRaises(QcGateError):
            verificar_iqc_para_solicitud(self.solicitud, permitir_override=False)


class TestIqcGateApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_lab = User.objects.create_user(
            username="lab_iqc",
            email="lab-iqc@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_admin = User.objects.create_user(
            username="admin_iqc",
            email="admin-iqc@t.com",
            password="x",
            rol="admin",
            is_staff=True,
            is_superuser=True,
        )
        self.user_bio = User.objects.create_user(
            username="bio_iqc",
            email="bio-iqc@t.com",
            password="x",
            rol="bioquimico",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(dni="9002001", nombre="P", apellido="IQC")
        esp = Especialidad.objects.create(nombre="Lab IQC")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="I", matricula="M-IQC", especialidad=esp
        )
        tm = TipoMuestra.objects.create(codigo="TM_IQC", nombre="Sangre IQC", activo=True)
        self.te = TipoExamen.objects.create(
            codigo="GLU_IQC",
            nombre="Glucosa IQC",
            unidad_default="mg/dL",
            tipo_muestra_requerida=tm,
            precio=1,
            activo=True,
            tipo_resultado="NUMERICO",
        )
        self.equipo = EquipoAnalizador.objects.create(
            codigo="CM260",
            nombre="CM260",
            activo=True,
        )
        self.te.equipo_analizador = self.equipo
        self.te.save(update_fields=["equipo_analizador"])
        self.mat = MaterialControl.objects.create(
            nombre="Ctrl GLU IQC",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=self.te,
            equipo=self.equipo,
            media_target=Decimal("100"),
            de_target=Decimal("5"),
            activo=True,
        )
        self.lote = LoteControl.objects.create(
            material=self.mat,
            codigo_lote="L-IQC",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )

    def _solicitud(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.te)
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te, valor_obtenido="")
        return sol

    def test_cargar_bloqueado_sin_iqc(self):
        sol = self._solicitud()
        res = sol.resultados.get()
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "95"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("calidad", (r.data.get("error") or "").lower())

    def test_cargar_ok_con_iqc_aceptado(self):
        sol = self._solicitud()
        res = sol.resultados.get()
        CorridaQC.objects.create(
            lote_control=self.lote,
            equipo=self.equipo,
            fecha=timezone.now(),
            estado=CorridaQC.Estado.ACEPTADA,
        )
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "95"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_precheck_get_y_batch(self):
        sol = self._solicitud()
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.get("/api/lab/qc/precheck/", {"solicitud": sol.pk})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["ok"])
        self.assertTrue(r.data["aplicable"])

        rb = self.client.post(
            "/api/lab/qc/precheck-batch/",
            {"solicitud_ids": [sol.pk]},
            format="json",
        )
        self.assertEqual(rb.status_code, status.HTTP_200_OK)
        self.assertEqual(len(rb.data["results"]), 1)
        self.assertFalse(rb.data["results"][0]["ok"])

    def test_validar_override_admin(self):
        sol = self._solicitud()
        res = sol.resultados.get()
        res.valor_obtenido = "95"
        res.save(update_fields=["valor_obtenido"])
        sol.estado = "LISTO_PARA_VALIDAR"
        sol.save(update_fields=["estado"])

        self.client.force_authenticate(user=self.user_bio)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.user_admin)
        r2 = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/validar/",
            {
                "confirmar_qc_override": True,
                "motivo_qc_override": "Urgencia clínica documentada",
            },
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "FINALIZADO")

    def test_corrida_create_asigna_equipo_default(self):
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            "/api/lab/qc/corridas/",
            {
                "lote_control": self.lote.id,
                "fecha": timezone.now().isoformat(),
                "valor": "100",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        corrida = CorridaQC.objects.get(pk=r.data["id"])
        self.assertEqual(corrida.equipo_id, self.equipo.id)

    def test_iqc_exige_equipo_del_examen_no_cm260_ajeno(self):
        """HBA1C (Finecare): corrida en CM260 no habilita; hace falta Finecare."""
        finecare = EquipoAnalizador.objects.create(
            codigo="FINECARE", nombre="Finecare", activo=True
        )
        te_hba = TipoExamen.objects.create(
            codigo="HBA1C_IQC",
            nombre="HbA1c IQC",
            tipo_muestra_requerida=self.te.tipo_muestra_requerida,
            tipo_resultado="NUMERICO",
            activo=True,
            equipo_analizador=finecare,
        )
        mat = MaterialControl.objects.create(
            nombre="Ctrl HBA1C",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=te_hba,
            equipo=finecare,
            media_target=Decimal("5"),
            de_target=Decimal("0.3"),
            activo=True,
        )
        lote = LoteControl.objects.create(
            material=mat,
            codigo_lote="L-HBA",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        # Corrida en CM260 (equipo incorrecto) — no cuenta
        CorridaQC.objects.create(
            lote_control=lote,
            equipo=self.equipo,
            fecha=timezone.now(),
            estado=CorridaQC.Estado.ACEPTADA,
        )
        fake = _FakeSolicitud([te_hba.id])
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(fake)
        self.assertIn("FINECARE", str(ctx.exception))

        CorridaQC.objects.create(
            lote_control=lote,
            equipo=finecare,
            fecha=timezone.now(),
            estado=CorridaQC.Estado.ACEPTADA,
        )
        validar_qc_para_cierre(fake)
