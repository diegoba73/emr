"""FSM LISTO_PARA_VALIDAR: carga completa, reapertura, parcial y validación."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class ListoParaValidarFsmTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_lab = User.objects.create_user(
            username="lab_lpv",
            email="lab-lpv@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.user_bio = User.objects.create_user(
            username="bio_lpv",
            email="bio-lpv@t.com",
            password="x",
            rol="bioquimico",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(dni="9001001", nombre="P", apellido="L")
        esp = Especialidad.objects.create(nombre="Lab LPV")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="L", matricula="M-LPV", especialidad=esp
        )
        tm = TipoMuestra.objects.create(codigo="TM_LPV", nombre="Sangre LPV", activo=True)
        self.te_a = TipoExamen.objects.create(
            codigo="LPV_A",
            nombre="A",
            unidad_default="u",
            tipo_muestra_requerida=tm,
            precio=1,
            activo=True,
        )
        self.te_b = TipoExamen.objects.create(
            codigo="LPV_B",
            nombre="B",
            unidad_default="u",
            tipo_muestra_requerida=tm,
            precio=1,
            activo=True,
        )

    def _solicitud(self, *examenes):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
            estado_obra_social="AUTORIZADO",
        )
        for te in examenes:
            sol.tipos_examen.add(te)
            ResultadoExamen.objects.create(solicitud=sol, tipo_examen=te, valor_obtenido="")
        return sol

    def test_completar_carga_pasa_a_listo_para_validar(self):
        sol = self._solicitud(self.te_a)
        res = sol.resultados.get()
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": res.pk, "valor": "1"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "LISTO_PARA_VALIDAR")

    def test_reabrir_a_en_proceso_si_borra_valor(self):
        sol = self._solicitud(self.te_a, self.te_b)
        ra = sol.resultados.get(tipo_examen=self.te_a)
        rb = sol.resultados.get(tipo_examen=self.te_b)
        self.client.force_authenticate(user=self.user_lab)
        self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "resultados": [
                    {"id": ra.pk, "valor": "1"},
                    {"id": rb.pk, "valor": "2"},
                ]
            },
            format="json",
        )
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "LISTO_PARA_VALIDAR")

        # Borrar un valor vía update directo + sync al guardar de nuevo (payload sin valor
        # no persiste vacío en ítems vacíos). Forzamos vacío en DB y re-sync vía carga
        # de un solo campo manteniendo el otro vacío: actualizamos rb a vacío en ORM
        # y luego cargamos solo ra (incompleto permanece).
        ResultadoExamen.objects.filter(pk=rb.pk).update(valor_obtenido="")
        r2 = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": ra.pk, "valor": "1.1"}]},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "EN_PROCESO")

    def test_informar_parcial_no_finaliza(self):
        sol = self._solicitud(self.te_a, self.te_b)
        ra = sol.resultados.get(tipo_examen=self.te_a)
        self.client.force_authenticate(user=self.user_lab)
        r = self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "informar_parcial": True,
                "resultados": [{"id": ra.pk, "valor": "9"}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "INFORMADO_PARCIAL")

    def test_validar_solo_desde_listo(self):
        sol = self._solicitud(self.te_a)
        res = sol.resultados.get()
        ResultadoExamen.objects.filter(pk=res.pk).update(valor_obtenido="5")
        self.client.force_authenticate(user=self.user_bio)
        r_fail = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r_fail.status_code, status.HTTP_400_BAD_REQUEST)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "EN_PROCESO")

        sol.estado = "LISTO_PARA_VALIDAR"
        sol.save(update_fields=["estado"])
        r_ok = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r_ok.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "FINALIZADO")

    def test_validar_incompletos_400(self):
        sol = self._solicitud(self.te_a, self.te_b)
        ra = sol.resultados.get(tipo_examen=self.te_a)
        ResultadoExamen.objects.filter(pk=ra.pk).update(valor_obtenido="1")
        sol.estado = "LISTO_PARA_VALIDAR"
        sol.save(update_fields=["estado"])
        self.client.force_authenticate(user=self.user_bio)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "LISTO_PARA_VALIDAR")

    def test_parcial_completo_pasa_a_listo_luego_validar(self):
        sol = self._solicitud(self.te_a, self.te_b)
        ra = sol.resultados.get(tipo_examen=self.te_a)
        rb = sol.resultados.get(tipo_examen=self.te_b)
        self.client.force_authenticate(user=self.user_lab)
        self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {
                "informar_parcial": True,
                "resultados": [{"id": ra.pk, "valor": "1"}],
            },
            format="json",
        )
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "INFORMADO_PARCIAL")
        self.client.post(
            f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
            {"resultados": [{"id": rb.pk, "valor": "2"}]},
            format="json",
        )
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "LISTO_PARA_VALIDAR")
        self.client.force_authenticate(user=self.user_bio)
        self.assertEqual(
            self.client.post(
                f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json"
            ).status_code,
            status.HTTP_200_OK,
        )
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "FINALIZADO")
