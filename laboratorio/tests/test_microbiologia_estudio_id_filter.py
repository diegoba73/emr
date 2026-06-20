"""
Tests — filtro server-side ?estudio_id= en endpoints de microbiología.
"""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
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
from laboratorio.muestra_estado import aplicar_recibir, aplicar_tomar, crear_muestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()

MICRO_LIST_ENDPOINTS = (
    "estudios",
    "siembras",
    "lecturas",
    "aislados",
    "identificaciones",
    "antibiogramas",
    "resultados-antibiotico",
    "informes",
)

INVALID_ESTUDIO_ID_QUERIES = (
    ("abc", "no entero"),
    ("", "vacío"),
    ("-1", "negativo"),
    ("0", "cero"),
)


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


def _results_ids(response):
    data = response.json()
    if isinstance(data, list):
        return {item["id"] for item in data}
    return {item["id"] for item in data.get("results", data)}


class TestMicroEstudioIdFilter(TestCase):
    """Filtro ?estudio_id= en listados microbiología."""

    @classmethod
    def setUpTestData(cls):
        cls.suf = uuid.uuid4().hex[:8]
        cls.lab = User.objects.create_user(
            username=f"lab_filt_{cls.suf}",
            email=f"lf{cls.suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        cls.admin = User.objects.create_user(
            username=f"adm_filt_{cls.suf}",
            email=f"af{cls.suf}@t.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        cls.superuser = User.objects.create_superuser(
            username=f"su_filt_{cls.suf}",
            email=f"su{cls.suf}@t.com",
            password="x",
        )
        cls.med_user = User.objects.create_user(
            username=f"med_filt_{cls.suf}",
            email=f"mf{cls.suf}@t.com",
            password="x",
            rol="medico",
        )
        cls.med_otro = User.objects.create_user(
            username=f"med2_filt_{cls.suf}",
            email=f"m2f{cls.suf}@t.com",
            password="x",
            rol="medico",
        )
        cls.pac_u = User.objects.create_user(
            username=f"pac_filt_{cls.suf}",
            email=f"pf{cls.suf}@t.com",
            password="x",
            rol="paciente",
        )
        cls.esp = Especialidad.objects.create(nombre=f"Esp {cls.suf}")
        cls.medico = Medico.objects.create(
            nombre="Dr",
            apellido="Uno",
            matricula=f"M1{cls.suf}",
            especialidad=cls.esp,
            user=cls.med_user,
        )
        cls.medico_ajeno = Medico.objects.create(
            nombre="Dr",
            apellido="Dos",
            matricula=f"M2{cls.suf}",
            especialidad=cls.esp,
            user=cls.med_otro,
        )
        cls.paciente = Paciente.objects.create(dni=f"D{cls.suf}", nombre="P", apellido="X")
        cls.tm = TipoMuestra.objects.create(codigo=f"TM{cls.suf}", nombre="Sangre", activo=True)
        cls.te = TipoExamen.objects.create(
            codigo=f"GLU{cls.suf}",
            nombre="Glu",
            tipo_muestra_requerida=cls.tm,
            precio=1,
            activo=True,
        )
        cls.medio = MedioCultivo.objects.create(codigo=f"AGS{cls.suf}", nombre="Agar", activo=True)
        cls.micro = Microorganismo.objects.create(
            codigo=f"ECO{cls.suf}", nombre="E. coli", activo=True
        )
        cls.antibiotico = Antibiotico.objects.create(
            codigo=f"AMP{cls.suf}", nombre="Ampicilina", activo=True
        )

        cls.sol = SolicitudExamen.objects.create(
            paciente=cls.paciente,
            medico_interno=cls.medico,
            origen_solicitud="EMR",
            estado="PENDIENTE",
        )
        cls.sol.tipos_examen.add(cls.te)
        cls.muestra = _muestra_recibida(cls.sol, cls.tm)

        cls.sol_ajena = SolicitudExamen.objects.create(
            paciente=cls.paciente,
            medico_interno=cls.medico_ajeno,
            origen_solicitud="EMR",
            estado="PENDIENTE",
        )
        cls.sol_ajena.tipos_examen.add(cls.te)
        cls.muestra_ajena = _muestra_recibida(cls.sol_ajena, cls.tm)

        cls.estudio_a = EstudioMicrobiologia.objects.create(
            solicitud=cls.sol, muestra=cls.muestra, paciente=cls.paciente
        )
        cls.estudio_b = EstudioMicrobiologia.objects.create(
            solicitud=cls.sol, muestra=cls.muestra, paciente=cls.paciente
        )
        cls.estudio_ajeno = EstudioMicrobiologia.objects.create(
            solicitud=cls.sol_ajena, muestra=cls.muestra_ajena, paciente=cls.paciente
        )

        cls.siembra_a = SiembraMicrobiologia.objects.create(
            estudio=cls.estudio_a, muestra=cls.muestra, medio=cls.medio
        )
        cls.siembra_b = SiembraMicrobiologia.objects.create(
            estudio=cls.estudio_b, muestra=cls.muestra, medio=cls.medio
        )
        cls.lectura_a = LecturaCultivo.objects.create(
            siembra=cls.siembra_a, estudio=cls.estudio_a, crecimiento="MODERADO"
        )
        cls.lectura_b = LecturaCultivo.objects.create(
            siembra=cls.siembra_b, estudio=cls.estudio_b, crecimiento="ESCASO"
        )
        cls.aislado_a = AisladoMicrobiologico.objects.create(
            estudio=cls.estudio_a,
            lectura_origen=cls.lectura_a,
            microorganismo=cls.micro,
            estado="IDENTIFICADO",
        )
        cls.aislado_b = AisladoMicrobiologico.objects.create(
            estudio=cls.estudio_b,
            lectura_origen=cls.lectura_b,
            microorganismo=cls.micro,
            estado="IDENTIFICADO",
        )
        cls.antibiograma_a = Antibiograma.objects.create(aislado=cls.aislado_a)
        cls.antibiograma_b = Antibiograma.objects.create(aislado=cls.aislado_b)
        cls.resultado_a = ResultadoAntibiotico.objects.create(
            antibiograma=cls.antibiograma_a,
            antibiotico=cls.antibiotico,
            interpretacion="S",
        )
        cls.resultado_b = ResultadoAntibiotico.objects.create(
            antibiograma=cls.antibiograma_b,
            antibiotico=cls.antibiotico,
            interpretacion="R",
        )
        cls.informe_a = InformeMicrobiologia.objects.create(
            estudio=cls.estudio_a, tipo="PRELIMINAR", texto="a"
        )
        cls.informe_b = InformeMicrobiologia.objects.create(
            estudio=cls.estudio_b, tipo="PRELIMINAR", texto="b"
        )
        cls.identificacion_a = IdentificacionMicroorganismo.objects.create(
            aislado=cls.aislado_a,
            microorganismo=cls.micro,
            metodo="manual",
        )

        cls.expected_by_path = {
            "estudios": cls.estudio_a.pk,
            "siembras": cls.siembra_a.pk,
            "lecturas": cls.lectura_a.pk,
            "aislados": cls.aislado_a.pk,
            "identificaciones": cls.identificacion_a.pk,
            "antibiogramas": cls.antibiograma_a.pk,
            "resultados-antibiotico": cls.resultado_a.pk,
            "informes": cls.informe_a.pk,
        }

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(self.lab)

    def test_sin_filtro_devuelve_todos_los_permitidos(self):
        for path in MICRO_LIST_ENDPOINTS:
            with self.subTest(path=path):
                r = self.client.get(f"/api/lab/microbiologia/{path}/")
                self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
                ids = _results_ids(r)
                self.assertIn(self.expected_by_path[path], ids)

    def test_filtro_valido_solo_registros_del_estudio(self):
        for path in MICRO_LIST_ENDPOINTS:
            with self.subTest(path=path):
                r = self.client.get(
                    f"/api/lab/microbiologia/{path}/?estudio_id={self.estudio_a.pk}"
                )
                self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
                self.assertEqual(_results_ids(r), {self.expected_by_path[path]})

    def test_filtro_estudio_inexistente_lista_vacia(self):
        for path in MICRO_LIST_ENDPOINTS:
            with self.subTest(path=path):
                r = self.client.get(
                    f"/api/lab/microbiologia/{path}/?estudio_id=999999999"
                )
                self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
                self.assertEqual(_results_ids(r), set())

    def test_filtro_estudio_id_invalido_retorna_400(self):
        for path in MICRO_LIST_ENDPOINTS:
            for raw, label in INVALID_ESTUDIO_ID_QUERIES:
                with self.subTest(path=path, invalid=label):
                    r = self.client.get(
                        f"/api/lab/microbiologia/{path}/?estudio_id={raw}"
                    )
                    self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.content)

    def test_filtro_estudio_id_decimal_retorna_400_sin_phi(self):
        r = self.client.get("/api/lab/microbiologia/siembras/?estudio_id=1.5")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.content)
        body = r.content.decode()
        self.assertIn("estudio_id", body)
        self.assertNotIn(self.paciente.dni, body)
        self.assertNotIn(self.paciente.nombre, body)
        self.assertNotIn(self.paciente.apellido, body)

    def test_superuser_filtra_por_estudio_valido(self):
        self.client.force_authenticate(self.superuser)
        for path in MICRO_LIST_ENDPOINTS:
            with self.subTest(path=path):
                r = self.client.get(
                    f"/api/lab/microbiologia/{path}/?estudio_id={self.estudio_a.pk}"
                )
                self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
                self.assertEqual(_results_ids(r), {self.expected_by_path[path]})

    def test_medico_estudio_ajeno_no_revela_datos(self):
        self.client.force_authenticate(self.med_user)
        for path in MICRO_LIST_ENDPOINTS:
            with self.subTest(path=path):
                r = self.client.get(
                    f"/api/lab/microbiologia/{path}/?estudio_id={self.estudio_ajeno.pk}"
                )
                self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
                self.assertEqual(_results_ids(r), set())

    def test_medico_estudio_propio_filtra(self):
        self.client.force_authenticate(self.med_user)
        for path in MICRO_LIST_ENDPOINTS:
            with self.subTest(path=path):
                r = self.client.get(
                    f"/api/lab/microbiologia/{path}/?estudio_id={self.estudio_a.pk}"
                )
                self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
                self.assertEqual(_results_ids(r), {self.expected_by_path[path]})

    def test_admin_filtra_por_estudio(self):
        self.client.force_authenticate(self.admin)
        for path in MICRO_LIST_ENDPOINTS:
            with self.subTest(path=path):
                r = self.client.get(
                    f"/api/lab/microbiologia/{path}/?estudio_id={self.estudio_a.pk}"
                )
                self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
                self.assertEqual(_results_ids(r), {self.expected_by_path[path]})

    def test_laboratorio_filtra_por_estudio(self):
        self.client.force_authenticate(self.lab)
        r = self.client.get(
            f"/api/lab/microbiologia/siembras/?estudio_id={self.estudio_a.pk}"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(_results_ids(r), {self.siembra_a.pk})

    def test_paciente_sin_permiso_403(self):
        self.client.force_authenticate(self.pac_u)
        r = self.client.get(
            f"/api/lab/microbiologia/siembras/?estudio_id={self.estudio_a.pk}"
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_alias_laboratorio_mismo_comportamiento(self):
        for path in MICRO_LIST_ENDPOINTS:
            with self.subTest(path=path):
                r_lab = self.client.get(
                    f"/api/lab/microbiologia/{path}/?estudio_id={self.estudio_a.pk}"
                )
                r_alias = self.client.get(
                    f"/api/laboratorio/microbiologia/{path}/?estudio_id={self.estudio_a.pk}"
                )
                self.assertEqual(r_lab.status_code, status.HTTP_200_OK, r_lab.content)
                self.assertEqual(r_alias.status_code, status.HTTP_200_OK, r_alias.content)
                self.assertEqual(_results_ids(r_lab), _results_ids(r_alias))
