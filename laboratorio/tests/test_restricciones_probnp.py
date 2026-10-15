"""Bloqueo de frecuencia PROBNP (obra social, 31 días) + revisión ambulatorio."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.restricciones_frecuencia import (
    RestriccionFrecuenciaError,
    alertas_frecuencia_para_solicitud,
    assert_puede_agregar_ensayos,
    origen_exige_bloqueo_frecuencia,
    paciente_tiene_probnp_reciente,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class TestRestriccionProbnpFrecuencia(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="adm_probnp",
            email="adm-probnp@t.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.medico_user = User.objects.create_user(
            username="med_probnp",
            email="med-probnp@t.com",
            password="x",
            rol="medico",
        )
        self.lab = User.objects.create_user(
            username="lab_probnp",
            email="lab-probnp@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.bio = User.objects.create_user(
            username="bio_probnp",
            email="bio-probnp@t.com",
            password="x",
            rol="bioquimico",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            dni="9012001", nombre="P", apellido="Probnp"
        )
        esp = Especialidad.objects.create(nombre="Esp Probnp")
        self.medico = Medico.objects.create(
            user=self.medico_user,
            nombre="Dr",
            apellido="Probnp",
            matricula="M-PBNP",
            especialidad=esp,
            ambito_atencion=Medico.AMBITO_COMPLETO,
        )
        tm, _ = TipoMuestra.objects.get_or_create(
            codigo="SANGRE_EDTA",
            defaults={"nombre": "Sangre EDTA", "activo": True},
        )
        self.probnp, _ = TipoExamen.objects.get_or_create(
            codigo="PROBNP",
            defaults={
                "nombre": "Pro-BNP",
                "unidad_default": "pg/mL",
                "tipo_muestra_requerida": tm,
                "precio": 1,
                "activo": True,
            },
        )
        if self.probnp.tipo_muestra_requerida_id != tm.pk:
            self.probnp.tipo_muestra_requerida = tm
            self.probnp.save(update_fields=["tipo_muestra_requerida"])
        self.glu = TipoExamen.objects.create(
            codigo="GLU_PBNP",
            nombre="Glucosa PBNP",
            unidad_default="mg/dL",
            tipo_muestra_requerida=tm,
            precio=1,
            activo=True,
        )

    def _orden_con_probnp(self, *, dias_atras=0):
        dias = dias_atras or 1
        fecha_toma = timezone.localdate() - timedelta(days=dias)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            fecha_programada_toma=fecha_toma,
            material_pedido="SANGRE",
        )
        sol.tipos_examen.add(self.probnp)
        ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=self.probnp, valor_obtenido=""
        )
        if dias_atras:
            SolicitudExamen.objects.filter(pk=sol.pk).update(
                fecha_solicitud=timezone.now() - timedelta(days=dias_atras)
            )
            sol.refresh_from_db()
        return sol

    def _pedido_completo(self, user, examenes_ids, *, origen="GUARDIA"):
        self.client.force_authenticate(user=user)
        return self.client.post(
            "/api/lab/pedidos-completos/",
            {
                "paciente_id": self.paciente.pk,
                "medico_id": self.medico.pk,
                "origen_solicitud": origen,
                "fecha_programada_toma": timezone.localdate().isoformat(),
                "solicitudes_lab": [
                    {
                        "material_pedido": "SANGRE",
                        "examenes_ids": examenes_ids,
                        "paneles_ids": [],
                    }
                ],
            },
            format="json",
        )

    def test_origen_exige_bloqueo(self):
        self.assertTrue(origen_exige_bloqueo_frecuencia("GUARDIA"))
        self.assertTrue(origen_exige_bloqueo_frecuencia("INTERNACION_UCO"))
        self.assertFalse(origen_exige_bloqueo_frecuencia("AMBULATORIO_CEHTA"))
        self.assertFalse(origen_exige_bloqueo_frecuencia("EXTERNO_ICPL"))

    def test_helper_detecta_pedido_reciente(self):
        self._orden_con_probnp(dias_atras=10)
        self.assertTrue(paciente_tiene_probnp_reciente(self.paciente.pk))

    def test_helper_ignora_pedido_viejo(self):
        self._orden_con_probnp(dias_atras=40)
        self.assertFalse(paciente_tiene_probnp_reciente(self.paciente.pk))

    def test_assert_bloquea_medico_guardia(self):
        self._orden_con_probnp(dias_atras=5)
        with self.assertRaises(RestriccionFrecuenciaError) as ctx:
            assert_puede_agregar_ensayos(
                self.medico_user,
                self.paciente.pk,
                [self.probnp.pk],
                origen_solicitud="GUARDIA",
            )
        self.assertIn("proBNP", str(ctx.exception))

    def test_assert_ambulatorio_no_bloquea(self):
        self._orden_con_probnp(dias_atras=5)
        assert_puede_agregar_ensayos(
            self.medico_user,
            self.paciente.pk,
            [self.probnp.pk],
            origen_solicitud="AMBULATORIO_CEHTA",
        )

    def test_assert_lab_exento_guardia(self):
        self._orden_con_probnp(dias_atras=5)
        assert_puede_agregar_ensayos(
            self.lab,
            self.paciente.pk,
            [self.probnp.pk],
            origen_solicitud="GUARDIA",
        )

    def test_medico_pedido_completo_bloqueado_guardia(self):
        self._orden_con_probnp(dias_atras=5)
        r = self._pedido_completo(self.medico_user, [self.probnp.pk], origen="GUARDIA")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("proBNP", str(r.data))

    def test_medico_pedido_completo_ambulatorio_ok(self):
        self._orden_con_probnp(dias_atras=5)
        r = self._pedido_completo(
            self.medico_user, [self.probnp.pk], origen="AMBULATORIO_CEHTA"
        )
        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), r.data)

    def test_agregar_examenes_bloquea_medico_internacion(self):
        abierta = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="INTERNACION_UCO",
            estado="PENDIENTE",
            fecha_programada_toma=timezone.localdate(),
            material_pedido="SANGRE",
        )
        abierta.tipos_examen.add(self.glu)
        ResultadoExamen.objects.create(
            solicitud=abierta, tipo_examen=self.glu, valor_obtenido=""
        )
        self._orden_con_probnp(dias_atras=3)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.post(
            f"/api/lab/solicitudes/{abierta.pk}/agregar-examenes/",
            {"examenes_ids": [self.probnp.pk], "paneles_ids": []},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("proBNP", str(r.data.get("detail") or r.data))

    def test_agregar_examenes_ambulatorio_medico_ok(self):
        abierta = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
            fecha_programada_toma=timezone.localdate(),
            material_pedido="SANGRE",
        )
        abierta.tipos_examen.add(self.glu)
        ResultadoExamen.objects.create(
            solicitud=abierta, tipo_examen=self.glu, valor_obtenido=""
        )
        self._orden_con_probnp(dias_atras=3)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.post(
            f"/api/lab/solicitudes/{abierta.pk}/agregar-examenes/",
            {"examenes_ids": [self.probnp.pk], "paneles_ids": []},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

    def test_endpoint_restricciones_medico_bloqueado_guardia(self):
        self._orden_con_probnp(dias_atras=2)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.get(
            "/api/lab/solicitudes/restricciones-ensayos/",
            {"paciente_id": self.paciente.pk, "origen_solicitud": "GUARDIA"},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["PROBNP"]["bloqueado"])

    def test_endpoint_restricciones_ambulatorio_libre(self):
        self._orden_con_probnp(dias_atras=2)
        self.client.force_authenticate(user=self.medico_user)
        r = self.client.get(
            "/api/lab/solicitudes/restricciones-ensayos/",
            {
                "paciente_id": self.paciente.pk,
                "origen_solicitud": "AMBULATORIO_CEHTA",
            },
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["PROBNP"]["bloqueado"])

    def test_alertas_frecuencia_ambulatorio(self):
        self._orden_con_probnp(dias_atras=5)
        amb = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_ICPL",
            estado="PENDIENTE",
            fecha_programada_toma=timezone.localdate(),
            material_pedido="SANGRE",
        )
        amb.tipos_examen.add(self.probnp)
        ResultadoExamen.objects.create(
            solicitud=amb, tipo_examen=self.probnp, valor_obtenido=""
        )
        alertas = alertas_frecuencia_para_solicitud(amb)
        self.assertTrue(any(a["codigo"] == "PROBNP" for a in alertas))
        self.client.force_authenticate(user=self.lab)
        r = self.client.get(f"/api/lab/solicitudes/{amb.pk}/alertas-frecuencia/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["aplica_revision_etiquetas"])
        self.assertIn("PROBNP", [a["codigo"] for a in r.data["alertas"]])

    def test_alertas_frecuencia_guardia_sin_revision(self):
        self._orden_con_probnp(dias_atras=5)
        g = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="GUARDIA",
            estado="PENDIENTE",
            fecha_programada_toma=timezone.localdate(),
            material_pedido="SANGRE",
        )
        g.tipos_examen.add(self.probnp)
        ResultadoExamen.objects.create(
            solicitud=g, tipo_examen=self.probnp, valor_obtenido=""
        )
        self.client.force_authenticate(user=self.lab)
        r = self.client.get(f"/api/lab/solicitudes/{g.pk}/alertas-frecuencia/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["aplica_revision_etiquetas"])
        self.assertEqual(r.data["alertas"], [])
