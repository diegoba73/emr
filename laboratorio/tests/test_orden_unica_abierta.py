"""Orden única abierta: merge en create y lock post-toma / post-etiquetas."""
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
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
        from django.utils import timezone

        return self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": examenes_ids,
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": timezone.localdate().isoformat(),
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

    def _poner_en_proceso(self, sol_id, estado="EN_PROCESO"):
        sol = SolicitudExamen.objects.get(pk=sol_id)
        if not Muestra.objects.filter(solicitud_id=sol_id).exists():
            Muestra.objects.create(
                solicitud=sol,
                paciente=self.pac,
                tipo_muestra=self.tm,
                tipo_contenedor=self.hep,
                estado="TOMADA",
                fecha_toma=timezone.now(),
            )
        sol.estado = estado
        sol.save(update_fields=["estado"])
        return sol

    def test_post_tomada_permite_agregar_mismo_tubo_y_bloquea_nueva_orden_mismo_dia(self):
        from datetime import timedelta

        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)
        self.assertFalse(orden_esta_abierta(SolicitudExamen.objects.get(pk=sol_id)))

        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_200_OK, r_add.data)
        self.assertTrue(r_add.data.get("puede_agregar_examenes"))
        self.assertTrue(r_add.data.get("puede_quitar_examenes"))
        self.assertEqual(
            set(
                ResultadoExamen.objects.filter(solicitud_id=sol_id).values_list(
                    "tipo_examen_id", flat=True
                )
            ),
            {self.glu.id, self.crea.id},
        )

        # Mismo día: no se puede crear otra mientras hay una en proceso
        r2 = self._create([self.urea.id])
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST, r2.data)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 1)
        self.assertIn("día de extracción", str(r2.data).lower())

        # Otro día (mañana): sí se puede
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        r3 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.urea.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": manana,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED, r3.data)
        self.assertFalse(r3.data.get("merged"))
        self.assertNotEqual(r3.data["id"], sol_id)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 2)

    def test_etiquetas_impresas_crean_tubo_nuevo_y_bloquean_nueva_orden_mismo_dia(self):
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        r_tom = self._imprimir_etiquetas(sol_id)
        self.assertEqual(r_tom.status_code, status.HTTP_200_OK, getattr(r_tom, "data", r_tom))

        sol = SolicitudExamen.objects.prefetch_related("muestras").get(pk=sol_id)
        self.assertFalse(orden_esta_abierta(sol))
        self.assertEqual(sol.estado, "PENDIENTE")
        self.assertTrue(sol.muestras.filter(estado="PENDIENTE_TOMA").exists())
        n_antes = Muestra.objects.filter(solicitud_id=sol_id).count()

        # Orina = otro tubo → se crea tubo PENDIENTE_TOMA en la misma orden
        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.orina.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_200_OK, r_add.data)
        self.assertTrue(
            ResultadoExamen.objects.filter(
                solicitud_id=sol_id, tipo_examen_id=self.orina.id
            ).exists()
        )
        self.assertEqual(Muestra.objects.filter(solicitud_id=sol_id).count(), n_antes + 1)
        self.assertTrue(
            Muestra.objects.filter(
                solicitud_id=sol_id,
                tipo_contenedor=self.frasco,
                estado="PENDIENTE_TOMA",
            ).exists()
        )

        r_get = self.client.get(
            f"/api/lab/solicitudes/{sol_id}/",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_get.status_code, status.HTTP_200_OK)
        self.assertFalse(r_get.data.get("orden_abierta"))
        self.assertTrue(r_get.data.get("esperando_recepcion"))
        self.assertTrue(r_get.data.get("puede_agregar_examenes"))
        self.assertFalse(r_get.data.get("pedido_adicional"))

        # Mismo día con etiquetas pendientes: nueva orden bloqueada (agregar a la existente)
        r2 = self._create([self.urea.id])
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST, r2.data)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 1)

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

    def test_etiquetas_impresas_crean_tubo_si_excede_capacidad(self):
        """11 unidades del mismo (tc,tm) → ceil(11/10)=2 tubos; con 1 impreso crea el 2º."""
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
        self.assertEqual(r_add.status_code, status.HTTP_200_OK, r_add.data)
        self.assertTrue(
            ResultadoExamen.objects.filter(
                solicitud_id=sol_id, tipo_examen_id=extras[9].id
            ).exists()
        )
        self.assertEqual(
            Muestra.objects.filter(solicitud_id=sol_id, estado="PENDIENTE_TOMA").count(),
            2,
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
        from django.utils import timezone
        from laboratorio.origen_solicitud import INTERNACION_UCO

        hoy = timezone.localdate().isoformat()
        r1 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.glu.id],
                "origen_solicitud": INTERNACION_UCO,
                "fecha_programada_toma": hoy,
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
                "fecha_programada_toma": hoy,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST, r2.data)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 1)
        self.assertIn("en proceso", str(r2.data).lower())

    def test_tras_finalizar_permite_nueva_orden_mismo_dia(self):
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id, estado="FINALIZADO")

        r2 = self._create([self.crea.id])
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, r2.data)
        self.assertFalse(r2.data.get("merged"))
        self.assertNotEqual(r2.data["id"], sol_id)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 2)

        # Si la 2ª también se finaliza, se puede una 3ª el mismo día
        self._poner_en_proceso(r2.data["id"], estado="FINALIZADO")
        r3 = self._create([self.urea.id])
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED, r3.data)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 3)

    def test_internacion_hoy_en_proceso_permite_orden_manana(self):
        from datetime import timedelta
        from laboratorio.origen_solicitud import INTERNACION_UCO

        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        r1 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.glu.id],
                "origen_solicitud": INTERNACION_UCO,
                "fecha_programada_toma": hoy.isoformat(),
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
                "fecha_programada_toma": manana.isoformat(),
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, r2.data)
        self.assertNotEqual(r2.data["id"], r1.data["id"])
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 2)

    def test_en_proceso_agregar_mismo_tubo_ok(self):
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)
        r_get = self.client.get(f"/api/lab/solicitudes/{sol_id}/", HTTP_HOST="localhost")
        self.assertTrue(r_get.data.get("puede_agregar_examenes"))
        self.assertTrue(r_get.data.get("puede_quitar_examenes"))

        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_200_OK, r_add.data)
        self.assertTrue(
            ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.crea).exists()
        )
        n_muestras = Muestra.objects.filter(solicitud_id=sol_id).count()
        self.assertEqual(n_muestras, 1)

    def test_en_proceso_agregar_panel_mismo_tubo(self):
        pan = PanelExamen.objects.create(
            codigo=f"PX{self.suf[:4]}", nombre="Panel X OU", activo=True
        )
        pan.tipos_examen.add(self.crea, self.urea)
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)
        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"paneles_ids": [pan.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_200_OK, r_add.data)
        tipos = set(
            ResultadoExamen.objects.filter(solicitud_id=sol_id).values_list(
                "tipo_examen_id", flat=True
            )
        )
        self.assertEqual(tipos, {self.glu.id, self.crea.id, self.urea.id})
        sol = SolicitudExamen.objects.get(pk=sol_id)
        self.assertIn(pan.id, set(sol.paneles.values_list("id", flat=True)))

    def test_en_proceso_agrega_tubo_nuevo(self):
        r1 = self._create([self.glu.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)
        n_antes = Muestra.objects.filter(solicitud_id=sol_id).count()
        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.orina.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_200_OK, r_add.data)
        self.assertTrue(
            ResultadoExamen.objects.filter(
                solicitud_id=sol_id, tipo_examen=self.orina
            ).exists()
        )
        self.assertEqual(Muestra.objects.filter(solicitud_id=sol_id).count(), n_antes + 1)
        self.assertTrue(
            Muestra.objects.filter(
                solicitud_id=sol_id,
                tipo_contenedor=self.frasco,
                estado="PENDIENTE_TOMA",
            ).exists()
        )

    def test_finalizado_bloquea_agregar_y_quitar(self):
        r1 = self._create([self.glu.id, self.crea.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id, estado="FINALIZADO")
        r_get = self.client.get(f"/api/lab/solicitudes/{sol_id}/", HTTP_HOST="localhost")
        self.assertFalse(r_get.data.get("puede_agregar_examenes"))
        self.assertFalse(r_get.data.get("puede_quitar_examenes"))

        r_add = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
            {"examenes_ids": [self.urea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_add.status_code, status.HTTP_400_BAD_REQUEST)

        r_del = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/quitar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_del.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.crea).exists()
        )

    def test_quitar_examen_vacio_ok(self):
        r1 = self._create([self.glu.id, self.crea.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)
        r_del = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/quitar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_del.status_code, status.HTTP_200_OK, r_del.data)
        self.assertFalse(
            ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.crea).exists()
        )
        self.assertTrue(
            ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.glu).exists()
        )
        sol = SolicitudExamen.objects.get(pk=sol_id)
        self.assertNotIn(self.crea.id, set(sol.tipos_examen.values_list("id", flat=True)))

    def test_quitar_examen_con_valor_rechaza(self):
        r1 = self._create([self.glu.id, self.crea.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)
        ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.crea).update(
            valor_obtenido="1.2"
        )
        r_del = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/quitar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_del.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("resultado", (r_del.data.get("detail") or "").lower())
        self.assertTrue(
            ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.crea).exists()
        )

    def test_quitar_examen_validado_rechaza(self):
        r1 = self._create([self.glu.id, self.crea.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)
        ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.crea).update(
            validado_por=self.lab,
            fecha_validacion=timezone.now(),
        )
        r_del = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/quitar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_del.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("validado", (r_del.data.get("detail") or "").lower())

    def test_quitar_panel_solo_componentes_exclusivos(self):
        pan_a = PanelExamen.objects.create(
            codigo=f"PA{self.suf[:4]}", nombre="Panel A OU", activo=True
        )
        pan_b = PanelExamen.objects.create(
            codigo=f"PB{self.suf[:4]}", nombre="Panel B OU", activo=True
        )
        pan_a.tipos_examen.add(self.glu, self.crea)
        pan_b.tipos_examen.add(self.crea, self.urea)
        r1 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.orina.id],
                "paneles_ids": [pan_a.id, pan_b.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": timezone.localdate().isoformat(),
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)

        r_del = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/quitar-examenes/",
            {"paneles_ids": [pan_a.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_del.status_code, status.HTTP_200_OK, r_del.data)
        tipos = set(
            ResultadoExamen.objects.filter(solicitud_id=sol_id).values_list(
                "tipo_examen_id", flat=True
            )
        )
        self.assertNotIn(self.glu.id, tipos)
        self.assertIn(self.crea.id, tipos)
        self.assertIn(self.urea.id, tipos)
        self.assertIn(self.orina.id, tipos)
        sol = SolicitudExamen.objects.get(pk=sol_id)
        self.assertNotIn(pan_a.id, set(sol.paneles.values_list("id", flat=True)))
        self.assertIn(pan_b.id, set(sol.paneles.values_list("id", flat=True)))

    def test_quitar_examen_cubierto_por_panel_restante_rechaza(self):
        pan_a = PanelExamen.objects.create(
            codigo=f"PC{self.suf[:4]}", nombre="Panel C OU", activo=True
        )
        pan_a.tipos_examen.add(self.glu, self.crea)
        r1 = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [],
                "paneles_ids": [pan_a.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": timezone.localdate().isoformat(),
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)
        sol_id = r1.data["id"]
        r_del = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/quitar-examenes/",
            {"examenes_ids": [self.glu.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_del.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("panel", (r_del.data.get("detail") or "").lower())
        self.assertTrue(
            ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.glu).exists()
        )

    def test_medico_no_puede_quitar_en_proceso(self):
        r1 = self._create([self.glu.id, self.crea.id])
        sol_id = r1.data["id"]
        self._poner_en_proceso(sol_id)
        medico = User.objects.create_user(
            username=f"med_ou_{self.suf}",
            password="pass12345",
            rol="medico",
        )
        self.client.force_authenticate(medico)
        r_del = self.client.post(
            f"/api/lab/solicitudes/{sol_id}/quitar-examenes/",
            {"examenes_ids": [self.crea.id]},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r_del.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            ResultadoExamen.objects.filter(solicitud_id=sol_id, tipo_examen=self.crea).exists()
        )


class TestRepeticionControl(TestCase):
    """2ª orden mismo día solo con ensayos informados de INFORMADO_PARCIAL."""

    def setUp(self):
        self.suf = uuid.uuid4().hex[:8]
        self.lab = User.objects.create_user(
            username=f"lab_rc_{self.suf}",
            password="pass12345",
            rol="laboratorio",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.lab)
        self.pac = Paciente.objects.create(
            nombre="Rita",
            apellido="Control",
            dni=f"6{self.suf[:7]}",
            fecha_nacimiento="1988-01-01",
        )
        self.tm = TipoMuestra.objects.create(
            codigo=f"RC{self.suf[:4]}",
            nombre=f"Sangre RC {self.suf}",
        )
        self.trop = TipoExamen.objects.create(
            codigo=f"TRP{self.suf[:4]}",
            nombre="Troponina RC",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
        )
        self.crea = TipoExamen.objects.create(
            codigo=f"CRC{self.suf[:4]}",
            nombre="Creatinina RC",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
        )
        self.urea = TipoExamen.objects.create(
            codigo=f"URC{self.suf[:4]}",
            nombre="Urea RC",
            tipo_muestra_requerida=self.tm,
            tipo_resultado="NUMERICO",
        )
        self.panel = PanelExamen.objects.create(
            codigo=f"PRC{self.suf[:4]}",
            nombre="Panel RC",
            activo=True,
        )
        self.panel.tipos_examen.add(self.crea)
        self.hoy = timezone.localdate()

    def _create_parcial_con_trop_informada(self) -> SolicitudExamen:
        sol = SolicitudExamen.objects.create(
            paciente=self.pac,
            estado="INFORMADO_PARCIAL",
            origen_solicitud="AMBULATORIO_CEHTA",
            fecha_programada_toma=self.hoy,
        )
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.trop,
            valor_obtenido="0.04",
        )
        ResultadoExamen.objects.create(
            solicitud=sol,
            tipo_examen=self.crea,
            valor_obtenido="",
        )
        return sol

    def test_endpoint_candidatos_lista_solo_informados(self):
        origen = self._create_parcial_con_trop_informada()
        r = self.client.get(
            "/api/lab/solicitudes/repeticion-control/",
            {
                "paciente_id": self.pac.id,
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            HTTP_HOST="localhost",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertTrue(r.data["disponible"])
        self.assertEqual(r.data["orden_origen"]["id"], origen.id)
        ids = {ex["id"] for ex in r.data["examenes"]}
        self.assertEqual(ids, {self.trop.id})
        self.assertEqual(r.data["examenes"][0]["valor_obtenido"], "0.04")

    def test_endpoint_sin_parcial_no_disponible(self):
        r = self.client.get(
            "/api/lab/solicitudes/repeticion-control/",
            {
                "paciente_id": self.pac.id,
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            HTTP_HOST="localhost",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["disponible"])
        self.assertEqual(r.data["examenes"], [])

    def test_create_repeticion_ok_misma_fecha(self):
        origen = self._create_parcial_con_trop_informada()
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.trop.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": self.hoy.isoformat(),
                "repeticion_control": True,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertNotEqual(r.data["id"], origen.id)
        self.assertEqual(SolicitudExamen.objects.filter(paciente=self.pac).count(), 2)
        nueva = SolicitudExamen.objects.get(pk=r.data["id"])
        self.assertIn("Repetición/control", nueva.observaciones or "")
        self.assertTrue(
            ResultadoExamen.objects.filter(
                solicitud=nueva, tipo_examen=self.trop
            ).exists()
        )

    def test_create_sin_flag_sigue_bloqueado(self):
        self._create_parcial_con_trop_informada()
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.trop.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": self.hoy.isoformat(),
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        detail = r.data if isinstance(r.data, str) else str(r.data)
        self.assertIn("pendiente o en proceso", detail)

    def test_create_rechaza_ensayo_no_informado(self):
        self._create_parcial_con_trop_informada()
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.crea.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": self.hoy.isoformat(),
                "repeticion_control": True,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)

    def test_create_rechaza_paneles(self):
        self._create_parcial_con_trop_informada()
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.trop.id],
                "paneles_ids": [self.panel.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": self.hoy.isoformat(),
                "repeticion_control": True,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)

    def test_create_rechaza_ensayo_ajeno(self):
        from laboratorio.solicitud_orden_abierta import MENSAJE_ORDEN_ACTIVA_MISMO_DIA

        self._create_parcial_con_trop_informada()
        r = self.client.post(
            "/api/lab/solicitudes/",
            {
                "paciente_id": self.pac.id,
                "examenes_ids": [self.urea.id],
                "origen_solicitud": "AMBULATORIO_CEHTA",
                "fecha_programada_toma": self.hoy.isoformat(),
                "repeticion_control": True,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertNotIn(MENSAJE_ORDEN_ACTIVA_MISMO_DIA, str(r.data))
