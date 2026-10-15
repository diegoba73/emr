"""Restricciones PSA, Vitamina D, tiroides y T4/SEROS (bloqueo en guardia/internación)."""

from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.restricciones_frecuencia import (
    RestriccionFrecuenciaError,
    assert_puede_agregar_ensayos,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class TestRestriccionesEnsayosExtendidas(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="adm_restx", email="adm-rx@t.com", password="x", rol="admin", is_staff=True
        )
        self.medico_user = User.objects.create_user(
            username="med_restx", email="med-rx@t.com", password="x", rol="medico"
        )
        self.lab = User.objects.create_user(
            username="lab_restx", email="lab-rx@t.com", password="x", rol="laboratorio", is_staff=True
        )
        self.paciente = Paciente.objects.create(
            dni="9013001", nombre="P", apellido="RestX", obra_social="OSDE"
        )
        self.paciente_seros = Paciente.objects.create(
            dni="9013002", nombre="S", apellido="Seros", obra_social="SEROS"
        )
        esp = Especialidad.objects.create(nombre="Esp RestX")
        self.medico = Medico.objects.create(
            user=self.medico_user,
            nombre="Dr",
            apellido="RestX",
            matricula="M-RESTX",
            especialidad=esp,
            ambito_atencion=Medico.AMBITO_COMPLETO,
        )
        tm = TipoMuestra.objects.create(codigo="TM_RX", nombre="Sangre RX", activo=True)

        def te(codigo, nombre):
            obj, _ = TipoExamen.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "unidad_default": "u",
                    "tipo_muestra_requerida": tm,
                    "precio": 1,
                    "activo": True,
                },
            )
            return obj

        self.psa = te("PSA", "PSA")
        self.vitd = te("VITD", "Vitamina D")
        self.tsh = te("TSH", "TSH")
        self.t3 = te("T3", "T3")
        self.t4 = te("T4", "T4")
        self.t4l = te("T4L", "T4 libre")
        self.glu = te("GLU_RX", "Glucosa RX")

    def _orden_con(self, paciente, tipo, *, dias_atras=0, fecha_solicitud=None):
        dias = dias_atras or 1
        fecha_toma = timezone.localdate() - timedelta(days=dias)
        sol = SolicitudExamen.objects.create(
            paciente=paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            fecha_programada_toma=fecha_toma,
            material_pedido="SANGRE",
        )
        sol.tipos_examen.add(tipo)
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=tipo, valor_obtenido="")
        if fecha_solicitud is not None:
            SolicitudExamen.objects.filter(pk=sol.pk).update(fecha_solicitud=fecha_solicitud)
        elif dias_atras:
            SolicitudExamen.objects.filter(pk=sol.pk).update(
                fecha_solicitud=timezone.now() - timedelta(days=dias_atras)
            )
        sol.refresh_from_db()
        return sol

    def _assert_bloquea(self, paciente, tipo_id, *, origen="GUARDIA"):
        with self.assertRaises(RestriccionFrecuenciaError):
            assert_puede_agregar_ensayos(
                self.medico_user,
                paciente.pk,
                [tipo_id],
                origen_solicitud=origen,
            )

    def _assert_ok(self, paciente, tipo_id, *, origen="GUARDIA"):
        assert_puede_agregar_ensayos(
            self.medico_user,
            paciente.pk,
            [tipo_id],
            origen_solicitud=origen,
        )

    def test_medico_psa_bloqueado_si_ya_este_anio(self):
        self._orden_con(self.paciente, self.psa, dias_atras=10)
        self._assert_bloquea(self.paciente, self.psa.pk)

    def test_admin_puede_psa_aunque_este_anio(self):
        self._orden_con(self.paciente, self.psa, dias_atras=10)
        assert_puede_agregar_ensayos(
            self.admin,
            self.paciente.pk,
            [self.psa.pk],
            origen_solicitud="GUARDIA",
        )

    def test_medico_vitd_bloqueado_si_ya_este_anio(self):
        self._orden_con(self.paciente, self.vitd, dias_atras=20)
        self._assert_bloquea(self.paciente, self.vitd.pk)

    def test_psa_ok_si_anio_anterior(self):
        anio_prev = timezone.localdate().year - 1
        tz = timezone.get_current_timezone()
        fs = timezone.make_aware(datetime(anio_prev, 6, 15, 12, 0, 0), tz)
        self._orden_con(self.paciente, self.psa, dias_atras=400, fecha_solicitud=fs)
        self._assert_ok(self.paciente, self.psa.pk)

    def test_tsh_bloqueado_si_menos_de_2_meses(self):
        self._orden_con(self.paciente, self.tsh, dias_atras=30)
        with self.assertRaises(RestriccionFrecuenciaError) as ctx:
            assert_puede_agregar_ensayos(
                self.medico_user,
                self.paciente.pk,
                [self.tsh.pk],
                origen_solicitud="GUARDIA",
            )
        self.assertIn("2 meses", str(ctx.exception))

    def test_tsh_ok_si_mas_de_2_meses_y_menos_de_2_en_anio(self):
        self._orden_con(self.paciente, self.tsh, dias_atras=70)
        self._assert_ok(self.paciente, self.tsh.pk)

    def test_tsh_bloqueado_si_ya_dos_en_el_anio(self):
        self._orden_con(self.paciente, self.tsh, dias_atras=200)
        self._orden_con(self.paciente, self.tsh, dias_atras=100)
        with self.assertRaises(RestriccionFrecuenciaError) as ctx:
            assert_puede_agregar_ensayos(
                self.medico_user,
                self.paciente.pk,
                [self.tsh.pk],
                origen_solicitud="INTERNACION_UCE",
            )
        self.assertIn("dos veces", str(ctx.exception).lower())

    def test_t3_independiente_de_tsh(self):
        self._orden_con(self.paciente, self.tsh, dias_atras=10)
        self._assert_ok(self.paciente, self.t3.pk)

    def test_t4_seros_bloquea_medico(self):
        with self.assertRaises(RestriccionFrecuenciaError) as ctx:
            assert_puede_agregar_ensayos(
                self.medico_user,
                self.paciente_seros.pk,
                [self.t4.pk],
                origen_solicitud="GUARDIA",
            )
        self.assertIn("SEROS", str(ctx.exception))

    def test_t4_seros_lab_puede(self):
        assert_puede_agregar_ensayos(
            self.lab,
            self.paciente_seros.pk,
            [self.t4.pk],
            origen_solicitud="GUARDIA",
        )

    def test_t4l_seros_permitido(self):
        self._assert_ok(self.paciente_seros, self.t4l.pk)

    def test_psa_ambulatorio_no_bloquea(self):
        self._orden_con(self.paciente, self.psa, dias_atras=10)
        self._assert_ok(self.paciente, self.psa.pk, origen="AMBULATORIO_CEHTA")

    def test_endpoint_restricciones_incluye_codigos(self):
        self._orden_con(self.paciente, self.psa, dias_atras=5)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.get(
            "/api/lab/solicitudes/restricciones-ensayos/",
            {"paciente_id": self.paciente.pk, "origen_solicitud": "GUARDIA"},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["PSA"]["bloqueado"])
        self.assertIn("TSH", r.data)
        self.assertIn("VITD", r.data)
        self.assertFalse(r.data["TSH"]["bloqueado"])
