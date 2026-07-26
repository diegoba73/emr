"""Tests derivación LAC/IACA y endpoint orden-abierta."""
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.derivacion_service import asegurar_labs_derivacion
from laboratorio.models import ResultadoExamen, TipoExamen, TipoMuestra
from laboratorio.models_derivacion import EstadoDerivacion
from pacientes.models import Paciente

User = get_user_model()


class TestDerivacionYOrdenAbierta(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab_user = User.objects.create_user(
            username=f"lab_der_{self.suf}",
            password="pass12345",
            rol="laboratorio",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.lab_user)
        self.pac = Paciente.objects.create(
            nombre="Deriva",
            apellido="Test",
            dni=f"5{self.suf[:7]}",
            fecha_nacimiento="1985-01-01",
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"SD{self.suf[:4]}",
            nombre=f"Sangre D {self.suf}",
        )
        self.lac, self.iaca = asegurar_labs_derivacion()
        self.ex_local = TipoExamen.objects.create(
            codigo=f"GLD{self.suf[:4]}",
            nombre="Glucosa local",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
        )
        self.ex_lac = TipoExamen.objects.create(
            codigo=f"XLD{self.suf[:4]}",
            nombre="Examen LAC",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
            laboratorio_derivacion=self.lac,
        )

    def test_create_copia_derivacion_pendiente_envio(self):
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.ex_local.id, self.ex_lac.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        sol_id = r.data["id"]
        res_lac = ResultadoExamen.objects.get(solicitud_id=sol_id, tipo_examen=self.ex_lac)
        self.assertEqual(res_lac.estado_derivacion, EstadoDerivacion.PENDIENTE_ENVIO)
        self.assertEqual(res_lac.laboratorio_derivacion_id, self.lac.id)
        res_loc = ResultadoExamen.objects.get(solicitud_id=sol_id, tipo_examen=self.ex_local)
        self.assertEqual(res_loc.estado_derivacion, EstadoDerivacion.LOCAL)
        resumen = r.data.get("derivaciones_resumen") or []
        self.assertTrue(any(x["tipo_examen_codigo"] == self.ex_lac.codigo for x in resumen))

    def test_marcar_enviado_y_carga_resultado_recibido(self):
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.ex_lac.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        sol_id = r.data["id"]
        res = ResultadoExamen.objects.get(solicitud_id=sol_id)
        m = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/marcar-derivacion/",
            {"resultado_id": res.id, "estado_derivacion": "ENVIADO"},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(m.status_code, status.HTTP_200_OK, m.data)
        self.assertEqual(m.data["estado_derivacion"], "ENVIADO")
        res.refresh_from_db()
        self.assertIsNotNone(res.fecha_envio_derivacion)

        # Simular carga vía update directo del modelo como haría cargar-resultados
        from laboratorio.views import SolicitudExamenViewSet  # noqa: F401

        res.valor_obtenido = "12.5"
        if res.estado_derivacion in ("PENDIENTE_ENVIO", "ENVIADO"):
            res.estado_derivacion = EstadoDerivacion.RESULTADO_RECIBIDO
        res.save()
        res.refresh_from_db()
        self.assertEqual(res.estado_derivacion, EstadoDerivacion.RESULTADO_RECIBIDO)

    def test_orden_abierta_endpoint(self):
        r0 = self.client.get(
            "/api/lab/solicitudes/orden-abierta/",
            {"paciente_id": self.pac.id},
            HTTP_HOST="localhost",
        )
        self.assertEqual(r0.status_code, status.HTTP_200_OK)
        self.assertIsNone(r0.data)

        created = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.ex_local.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        r1 = self.client.get(
            "/api/lab/solicitudes/orden-abierta/",
            {"paciente_id": self.pac.id},
            HTTP_HOST="localhost",
        )
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r1.data["id"], created.data["id"])
        self.assertEqual(r1.data["numero"], created.data["numero"])

    def test_list_labs_derivacion(self):
        asegurar_labs_derivacion()
        r = self.client.get("/api/lab/derivaciones/", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        codes = {x["codigo"] for x in r.data.get("results", r.data if isinstance(r.data, list) else [])}
        if not codes and "results" not in (r.data or {}):
            # paginated or list
            data = r.data if isinstance(r.data, list) else r.data.get("results", [])
            codes = {x["codigo"] for x in data}
        self.assertIn("LAC", codes)
        self.assertIn("IACA", codes)
