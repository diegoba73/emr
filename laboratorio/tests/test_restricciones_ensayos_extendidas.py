"""Frecuencia PSA/VITD/tiroides/T4-SEROS/iono-SEROS/HBA1C/LPA: aviso al imprimir."""

from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.restricciones_frecuencia import (
    alertas_frecuencia_para_solicitud,
    assert_puede_agregar_ensayos,
)
from medicos.models import Especialidad, Medico
from pacientes.models import ObraSocial, Paciente

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
        self.bio = User.objects.create_user(
            username="bio_restx", email="bio-rx@t.com", password="x", rol="bioquimico", is_staff=True
        )
        os_osde, _ = ObraSocial.objects.get_or_create(
            codigo="OSDE", defaults={"nombre": "OSDE", "activo": True}
        )
        os_seros, _ = ObraSocial.objects.get_or_create(
            codigo="SEROS", defaults={"nombre": "SEROS", "activo": True}
        )
        self.paciente = Paciente.objects.create(
            dni="9013001", nombre="P", apellido="RestX", obra_social=os_osde
        )
        self.paciente_seros = Paciente.objects.create(
            dni="9013002", nombre="S", apellido="Seros", obra_social=os_seros
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
        self.hba1c = te("HBA1C", "Hemoglobina glicosilada (HbA1c)")
        self.lpa = te("LPA", "Lipoproteína A")
        self.na = te("NA", "Sodio")
        self.k = te("K", "Potasio")
        self.cl = te("CL", "Cloro")
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

    def _assert_ok(self, paciente, tipo_id, *, origen="GUARDIA"):
        assert_puede_agregar_ensayos(
            self.medico_user,
            paciente.pk,
            [tipo_id],
            origen_solicitud=origen,
        )

    def _orden_actual(self, paciente, *tipos, origen="AMBULATORIO_CEHTA"):
        sol = SolicitudExamen.objects.create(
            paciente=paciente,
            medico_interno=self.medico,
            origen_solicitud=origen,
            estado="PENDIENTE",
            fecha_programada_toma=timezone.localdate(),
            material_pedido="SANGRE",
        )
        for t in tipos:
            sol.tipos_examen.add(t)
            ResultadoExamen.objects.create(solicitud=sol, tipo_examen=t, valor_obtenido="")
        return sol

    def test_medico_puede_pedir_psa_aunque_haya_previa(self):
        self._orden_con(self.paciente, self.psa, dias_atras=10)
        self._assert_ok(self.paciente, self.psa.pk)
        self._assert_ok(self.paciente, self.psa.pk, origen="AMBULATORIO_CEHTA")

    def test_admin_puede_psa_aunque_este_anio(self):
        self._orden_con(self.paciente, self.psa, dias_atras=10)
        assert_puede_agregar_ensayos(
            self.admin,
            self.paciente.pk,
            [self.psa.pk],
            origen_solicitud="GUARDIA",
        )

    def test_medico_puede_pedir_vitd_aunque_haya_previa(self):
        self._orden_con(self.paciente, self.vitd, dias_atras=20)
        self._assert_ok(self.paciente, self.vitd.pk)

    def test_alerta_psa_si_ya_este_anio(self):
        self._orden_con(self.paciente, self.psa, dias_atras=10)
        actual = self._orden_actual(self.paciente, self.psa)
        self.assertTrue(any(a["codigo"] == "PSA" for a in alertas_frecuencia_para_solicitud(actual)))

    def test_sin_alerta_psa_si_solo_anio_anterior(self):
        anio_prev = timezone.localdate().year - 1
        tz = timezone.get_current_timezone()
        fs = timezone.make_aware(datetime(anio_prev, 6, 15, 12, 0, 0), tz)
        self._orden_con(self.paciente, self.psa, dias_atras=400, fecha_solicitud=fs)
        sola = self._orden_actual(self.paciente, self.psa)
        self.assertFalse(any(a["codigo"] == "PSA" for a in alertas_frecuencia_para_solicitud(sola)))

    def test_alerta_tsh_si_menos_de_2_meses(self):
        self._orden_con(self.paciente, self.tsh, dias_atras=30)
        actual = self._orden_actual(self.paciente, self.tsh, origen="GUARDIA")
        alertas = alertas_frecuencia_para_solicitud(actual)
        self.assertTrue(any(a["codigo"] == "TSH" and "2 meses" in a["mensaje"] for a in alertas))

    def test_sin_alerta_tsh_si_mas_de_2_meses_y_menos_de_2_en_anio(self):
        self._orden_con(self.paciente, self.tsh, dias_atras=70)
        actual = self._orden_actual(self.paciente, self.tsh)
        self.assertFalse(any(a["codigo"] == "TSH" for a in alertas_frecuencia_para_solicitud(actual)))

    def test_alerta_tsh_si_ya_dos_en_el_anio(self):
        self._orden_con(self.paciente, self.tsh, dias_atras=200)
        self._orden_con(self.paciente, self.tsh, dias_atras=100)
        actual = self._orden_actual(self.paciente, self.tsh, origen="INTERNACION_UCE")
        alertas = alertas_frecuencia_para_solicitud(actual)
        self.assertTrue(any("dos veces" in (a["mensaje"] or "").lower() for a in alertas))

    def test_t3_independiente_de_tsh_sin_alerta(self):
        self._orden_con(self.paciente, self.tsh, dias_atras=10)
        actual = self._orden_actual(self.paciente, self.t3)
        self.assertFalse(any(a["codigo"] == "T3" for a in alertas_frecuencia_para_solicitud(actual)))

    def test_t4_seros_no_bloquea_al_pedir_pero_alerta_al_imprimir(self):
        self._assert_ok(self.paciente_seros, self.t4.pk)
        actual = self._orden_actual(self.paciente_seros, self.t4, origen="GUARDIA")
        alertas = alertas_frecuencia_para_solicitud(actual)
        self.assertTrue(any(a["codigo"] == "T4" and "SEROS" in a["mensaje"] for a in alertas))

    def test_t4_seros_lab_puede_pedir(self):
        assert_puede_agregar_ensayos(
            self.lab,
            self.paciente_seros.pk,
            [self.t4.pk],
            origen_solicitud="GUARDIA",
        )

    def test_t4l_seros_sin_alerta(self):
        actual = self._orden_actual(self.paciente_seros, self.t4l)
        self.assertFalse(any(a["codigo"] == "T4L" for a in alertas_frecuencia_para_solicitud(actual)))

    def test_iono_seros_no_bloquea_al_pedir_aunque_haya_previa(self):
        self._orden_con(self.paciente_seros, self.na, dias_atras=10)
        assert_puede_agregar_ensayos(
            self.medico_user,
            self.paciente_seros.pk,
            [self.na.pk, self.k.pk, self.cl.pk],
            origen_solicitud="GUARDIA",
        )
        assert_puede_agregar_ensayos(
            self.medico_user,
            self.paciente_seros.pk,
            [self.na.pk],
            origen_solicitud="AMBULATORIO_CEHTA",
        )

    def test_endpoint_iono_seros_nunca_bloqueado_al_pedir(self):
        self._orden_con(self.paciente_seros, self.na, dias_atras=5)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.get(
            "/api/lab/solicitudes/restricciones-ensayos/",
            {"paciente_id": self.paciente_seros.pk, "origen_solicitud": "GUARDIA"},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["PAN_IONO"]["bloqueado"])
        self.assertTrue(r.data["PAN_IONO"]["aviso"])
        self.assertIn("SEROS", r.data["PAN_IONO"]["mensaje"] or "")
        self.assertTrue(r.data["NA"]["aviso"])

    def test_alerta_iono_seros_al_imprimir_ambulatorio_y_guardia(self):
        self._orden_con(self.paciente_seros, self.na, dias_atras=10)
        for origen in ("AMBULATORIO_CEHTA", "GUARDIA"):
            amb = self._orden_actual(
                self.paciente_seros, self.na, self.k, self.cl, origen=origen
            )
            alertas = alertas_frecuencia_para_solicitud(amb)
            self.assertTrue(
                any(a["codigo"] == "PAN_IONO" for a in alertas),
                msg=f"origen={origen}",
            )
            self.client.force_authenticate(user=self.lab)
            r = self.client.get(f"/api/lab/solicitudes/{amb.pk}/alertas-frecuencia/")
            self.assertEqual(r.status_code, status.HTTP_200_OK)
            self.assertTrue(r.data["aplica_revision_etiquetas"])
            self.assertIn("PAN_IONO", [a["codigo"] for a in r.data["alertas"]])

    def test_endpoint_restricciones_nunca_bloquea_pero_avisa(self):
        self._orden_con(self.paciente, self.psa, dias_atras=5)
        self._orden_con(self.paciente, self.hba1c, dias_atras=5)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.get(
            "/api/lab/solicitudes/restricciones-ensayos/",
            {"paciente_id": self.paciente.pk, "origen_solicitud": "GUARDIA"},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        for codigo in ("PSA", "TSH", "VITD", "HBA1C", "LPA"):
            self.assertIn(codigo, r.data)
            self.assertFalse(r.data[codigo]["bloqueado"])
        self.assertTrue(r.data["PSA"]["aviso"])
        self.assertIn("año", (r.data["PSA"]["mensaje"] or "").lower())
        self.assertTrue(r.data["HBA1C"]["aviso"])
        self.assertIn("3 meses", r.data["HBA1C"]["mensaje"] or "")
        self.assertFalse(r.data["TSH"]["aviso"])
        self.assertIsNone(r.data["TSH"]["mensaje"])

    def test_medico_puede_pedir_hba1c_en_cualquier_origen(self):
        self._orden_con(self.paciente, self.hba1c, dias_atras=10)
        for origen in ("GUARDIA", "INTERNACION_UCE", "AMBULATORIO_CEHTA"):
            self._assert_ok(self.paciente, self.hba1c.pk, origen=origen)

    def test_alerta_hba1c_si_menos_de_90_dias_en_todos_los_origenes(self):
        self._orden_con(self.paciente, self.hba1c, dias_atras=30)
        for origen in ("GUARDIA", "INTERNACION_UCE", "AMBULATORIO_CEHTA"):
            actual = self._orden_actual(self.paciente, self.hba1c, origen=origen)
            alertas = alertas_frecuencia_para_solicitud(actual)
            self.assertTrue(
                any(a["codigo"] == "HBA1C" and "3 meses" in a["mensaje"] for a in alertas),
                msg=f"origen={origen}",
            )
            self.client.force_authenticate(user=self.lab)
            r = self.client.get(f"/api/lab/solicitudes/{actual.pk}/alertas-frecuencia/")
            self.assertEqual(r.status_code, status.HTTP_200_OK)
            self.assertTrue(r.data["aplica_revision_etiquetas"])
            self.assertIn("HBA1C", [a["codigo"] for a in r.data["alertas"]])

    def test_sin_alerta_hba1c_si_mas_de_90_dias(self):
        self._orden_con(self.paciente, self.hba1c, dias_atras=91)
        actual = self._orden_actual(self.paciente, self.hba1c)
        self.assertFalse(any(a["codigo"] == "HBA1C" for a in alertas_frecuencia_para_solicitud(actual)))

    def test_lab_y_bio_pueden_hba1c(self):
        self._orden_con(self.paciente, self.hba1c, dias_atras=10)
        assert_puede_agregar_ensayos(
            self.lab, self.paciente.pk, [self.hba1c.pk], origen_solicitud="GUARDIA"
        )
        assert_puede_agregar_ensayos(
            self.bio, self.paciente.pk, [self.hba1c.pk], origen_solicitud="INTERNACION_UCO"
        )

    def test_medico_puede_pedir_lpa_aunque_reciente(self):
        self._orden_con(self.paciente, self.lpa, dias_atras=10)
        for origen in ("GUARDIA", "INTERNACION_UCE", "AMBULATORIO_CEHTA"):
            self._assert_ok(self.paciente, self.lpa.pk, origen=origen)

    def test_alerta_lpa_si_menos_de_90_dias(self):
        self._orden_con(self.paciente, self.lpa, dias_atras=30)
        actual = self._orden_actual(self.paciente, self.lpa, origen="AMBULATORIO_CEHTA")
        alertas = alertas_frecuencia_para_solicitud(actual)
        self.assertTrue(
            any(a["codigo"] == "LPA" and "3 meses" in a["mensaje"] for a in alertas)
        )

    def test_sin_alerta_lpa_si_mas_de_90_dias(self):
        self._orden_con(self.paciente, self.lpa, dias_atras=91)
        actual = self._orden_actual(self.paciente, self.lpa)
        self.assertFalse(any(a["codigo"] == "LPA" for a in alertas_frecuencia_para_solicitud(actual)))
