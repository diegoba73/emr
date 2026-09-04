"""Órdenes ambulatorias: no validar ni emitir informe sin obra social autorizada."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.obra_social import MENSAJE_NO_AUTORIZADA
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


class TestValidarRequiereObraSocialAutorizada(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="adm_os_val",
            email="adm-os-val@t.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(dni="9011001", nombre="P", apellido="OS")
        esp = Especialidad.objects.create(nombre="Esp OS val")
        self.medico = Medico.objects.create(
            nombre="Dr", apellido="OS", matricula="M-OSV", especialidad=esp
        )
        tm = TipoMuestra.objects.create(codigo="TM_OSV", nombre="Sangre OS", activo=True)
        self.te = TipoExamen.objects.create(
            codigo="OSV_A",
            nombre="A",
            unidad_default="u",
            tipo_muestra_requerida=tm,
            precio=1,
            activo=True,
        )

    def _orden(self, *, origen, estado_os=""):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud=origen,
            estado="LISTO_PARA_VALIDAR",
            estado_obra_social=estado_os,
        )
        sol.tipos_examen.add(self.te)
        ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=self.te, valor_obtenido="10"
        )
        return sol

    def test_ambulatorio_sin_autorizar_no_valida(self):
        sol = self._orden(origen="AMBULATORIO_CEHTA", estado_os="FALTA_AUTORIZACION")
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("autorizada", (r.data.get("error") or "").lower())
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "LISTO_PARA_VALIDAR")

    def test_ambulatorio_sin_cargar_no_valida(self):
        sol = self._orden(origen="EXTERNO_ICPL", estado_os="")
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("obra social", (r.data.get("error") or MENSAJE_NO_AUTORIZADA).lower())

    def test_ambulatorio_debe_abonar_no_valida(self):
        sol = self._orden(origen="AMBULATORIO_CEHTA", estado_os="DEBE_ABONAR")
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "LISTO_PARA_VALIDAR")

    def test_ambulatorio_autorizado_valida(self):
        sol = self._orden(origen="AMBULATORIO_ICPL", estado_os="AUTORIZADO")
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "FINALIZADO")

    def test_internacion_sin_os_puede_validar(self):
        sol = self._orden(origen="INTERNACION_UCO", estado_os="")
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/validar/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        sol.refresh_from_db()
        self.assertEqual(sol.estado, "FINALIZADO")
