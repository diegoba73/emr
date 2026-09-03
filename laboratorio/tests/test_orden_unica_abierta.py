"""Orden única abierta: merge en create y lock post-toma / post-etiquetas."""
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra, TipoContenedor
from laboratorio.solicitud_orden_abierta import orden_esta_abierta
from pacientes.models import Paciente

User = get_user_model()


class TestOrdenUnicaAbierta(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_ou_{self.suf}",
            password="pass12345",
            rol="laboratorio",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.lab)
        self.pac = Paciente.objects.create(
            nombre="Ana",
            apellido="Orden",
            dni=f"4{self.suf[:7]}",
            fecha_nacimiento="1990-01-01",
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"S{self.suf[:4]}",
            nombre=f"Sangre {self.suf}",
        )
        self.tm_orina = TipoMuestra.objects.create(
            codigo=f"O{self.suf[:4]}",
            nombre=f"Orina {self.suf}",
        )
        self.hep = TipoContenedor.objects.create(
            codigo=f"HEP{self.suf[:4]}",
            nombre="Heparina OU",
            activo=True,
        )
        self.frasco = TipoContenedor.objects.create(
            codigo=f"FRA{self.suf[:4]}",
            nombre="Frasco OU",
            activo=True,
        )
        self.glu = TipoExamen.objects.create(
            codigo=f"GLU{self.suf[:4]}",
            nombre="Glucosa OU",
            tipo_muestra_requerida=self.tm,
            tipo_contenedor=self.hep,
            tipo_resultado="NUMERICO",
        )
        self.crea = TipoExamen.objects.create(
            codigo=f"CRE{self.suf[:4]}",
            nombre="Creatinina OU",
            tipo_muestra_requerida=self.tm,
            tipo_contenedor=self.hep,
            tipo_resultado="NUMERICO",
        )
        self.urea = TipoExamen.objects.create(
            codigo=f"URE{self.suf[:4]}",
            nombre="Urea OU",
            tipo_muestra_requerida=self.tm,
            tipo_contenedor=self.hep,
            tipo_resultado="NUMERICO",
        )
        self.orina = TipoExamen.objects.create(
            codigo=f"ORI{self.suf[:4]}",
            nombre="Orina simple OU",
            tipo_muestra_requerida=self.tm_orina,
            tipo_contenedor=self.frasco,
            tipo_resultado="TEXTO",
        )

    def _create(self, examenes_ids):
        return self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": examenes_ids,
                "origen_solicitud": "AMBULATORIO_CEHTA",
            },
            format="json",
            HTTP_HOST="localhost",
        )

    def _imprimir_etiquetas(self, sol_id):
        return self.client.post(
            f"/api/lab/solicitudes/{sol_id}/tomar-muestra/",
            {},
            format="json",
            HTTP_HOST="localhost",
        )

    def test_segunda_orden_merge_misma_numero(self):
        r1 = self._create([self.glu.id])
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)
        self.assertFalse(r1.data.get("merged"))
        numero = r1.data["numero"]
        id1 = r1.data["id"]

        r2 = self._create([self.crea.id])
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.data)
        self.assertTrue(r2.data.get("merged"))
        self.assertEqual(r2.data["id"], id1)
        self.assertEqual(r2.data["numero"], numero)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 1)
        tipos = set(
            ResultadoExamen.objects.filter(solicitud_id=id1).values_list(
                "tipo_examen_id", flat=True
            )
        )
        self.assertEqual(tipos, {self.glu.id, self.crea.id})

    def test_dedup_mismo_examen(self):
        r1 = self._create([self.glu.id])
        id1 = r1.data["id"]
        r2 = self._create([self.glu.id, self.urea.id])
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            ResultadoExamen.objects.filter(solicitud_id=id1, tipo_examen=self.glu).count(),
            1,
        )
        self.assertTrue(
            ResultadoExamen.objects.filter(solicitud_id=id1, tipo_examen=self.urea).exists()
        )

    def test_post_tomada_permite_nueva_orden_y_bloquea_agregar(self):
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        sol = SolicitudExamen.objects.get(pk=sol_id)
        Muestra.objects.create(
            solicitud=sol,
            paciente=self.pac,
            tipo_muestra=self.tm,
            tipo_contenedor=self.hep,
            estado="TOMADA",
            fecha_toma=timezone.now(),
        )
        sol.estado = "EN_PROCESO"
        sol.save(update_fields=["estado"])
        self.assertFalse(orden_esta_abierta(SolicitudExamen.objects.get(pk=sol_id)))

        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_400_BAD_REQUEST)

        r2 = self._create([self.crea.id])
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, r2.data)
        self.assertFalse(r2.data.get("merged"))
        self.assertNotEqual(r2.data["id"], sol_id)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 2)
        self.assertTrue(r2.data.get("pedido_adicional"))
        self.assertTrue(r2.data.get("orden_abierta"))
        self.assertFalse(r2.data.get("esperando_recepcion"))

    def test_etiquetas_impresas_bloquean_tubo_nuevo_y_permiten_nueva_orden(self):
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        r_tom = self._imprimir_etiquetas(sol_id)
        self.assertEqual(r_tom.status_code, status.HTTP_200_OK, getattr(r_tom, "data", r_tom))

        sol = SolicitudExamen.objects.prefetch_related("muestras").get(pk=sol_id)
        self.assertFalse(orden_esta_abierta(sol))
        self.assertEqual(sol.estado, "PENDIENTE")
        self.assertTrue(sol.muestras.filter(estado="PENDIENTE_TOMA").exists())

        # Orina = otro tubo → rechazado
        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.orina.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tubo", (r_add.data.get("detail") or "").lower())

        r_get = self.client.get(
            f"/api/lab/solicitudes/{sol_id}/",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_get.status_code, status.HTTP_200_OK)
        self.assertFalse(r_get.data.get("orden_abierta"))
        self.assertTrue(r_get.data.get("esperando_recepcion"))
        self.assertTrue(r_get.data.get("puede_agregar_examenes"))
        self.assertFalse(r_get.data.get("pedido_adicional"))

        r2 = self._create([self.orina.id])
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, r2.data)
        self.assertFalse(r2.data.get("merged"))
        self.assertNotEqual(r2.data["id"], sol_id)
        self.assertTrue(r2.data.get("orden_abierta"))
        self.assertFalse(r2.data.get("esperando_recepcion"))
        # La 1ª orden sigue PENDIENTE esperando recepción → pedido adicional
        self.assertTrue(r2.data.get("pedido_adicional"))

    def test_etiquetas_impresas_permiten_agregar_mismo_tubo(self):
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        r_tom = self._imprimir_etiquetas(sol_id)
        self.assertEqual(r_tom.status_code, status.HTTP_200_OK, getattr(r_tom, "data", r_tom))
        n_muestras = Muestra.objects.filter(solicitud_id=sol_id).count()

        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_200_OK, r_add.data)
        self.assertTrue(r_add.data.get("merged"))
        self.assertFalse(r_add.data.get("orden_abierta"))
        self.assertTrue(r_add.data.get("esperando_recepcion"))
        self.assertTrue(r_add.data.get("puede_agregar_examenes"))
        self.assertEqual(
            ResultadoExamen.objects.filter(solicitud_id=sol_id).count(),
            2,
        )
        # No se crean tubos nuevos
        self.assertEqual(Muestra.objects.filter(solicitud_id=sol_id).count(), n_muestras)

    def test_etiquetas_impresas_rechazan_si_excede_capacidad_tubo(self):
        """11 unidades del mismo (tc,tm) → ceil(11/10)=2 tubos; con 1 impreso rechaza."""
        extras = []
        for i in range(10):
            extras.append(
                TipoExamen.objects.create(
                    codigo=f"X{i}{self.suf[:3]}",
                    nombre=f"Extra {i} OU",
                    tipo_muestra_requerida=self.tm,
                    tipo_contenedor=self.hep,
                    tipo_resultado="NUMERICO",
                )
            )
        r1 = self._create([self.glu.id] + [e.id for e in extras[:9]])
        sol_id = r1.data["id"]
        # 10 unidades → 1 tubo
        r_tom = self._imprimir_etiquetas(sol_id)
        self.assertEqual(r_tom.status_code, status.HTTP_200_OK, getattr(r_tom, "data", r_tom))
        self.assertEqual(
            Muestra.objects.filter(solicitud_id=sol_id, estado="PENDIENTE_TOMA").count(),
            1,
        )

        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [extras[9].id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tubo", (r_add.data.get("detail") or "").lower())
        self.assertFalse(
            ResultadoExamen.objects.filter(
                solicitud_id=sol_id, tipo_examen_id=extras[9].id
            ).exists()
        )

    def test_agregar_examenes_endpoint_ok(self):
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_200_OK, r_add.data)
        self.assertTrue(r_add.data.get("merged"))
        self.assertTrue(r_add.data.get("orden_abierta"))
        self.assertTrue(r_add.data.get("puede_agregar_examenes"))
        self.assertEqual(
            ResultadoExamen.objects.filter(solicitud_id=sol_id).count(),
            2,
        )

    def test_internacion_bloquea_nueva_orden_si_hay_analisis_en_proceso(self):
        from laboratorio.origen_solicitud import INTERNACION_UCO

        r1 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.glu.id],
                "origen_solicitud": INTERNACION_UCO,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)
        sol = SolicitudExamen.objects.get(pk=r1.data["id"])
        sol.estado = "EN_PROCESO"
        sol.save(update_fields=["estado"])

        r2 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.crea.id],
                "origen_solicitud": INTERNACION_UCO,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST, r2.data)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 1)
        self.assertIn("en proceso", str(r2.data).lower())
