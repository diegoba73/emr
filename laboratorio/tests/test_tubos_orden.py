"""Tests de cálculo de tubos por orden (ceil n/10)."""
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra, TipoContenedor
from laboratorio.tubos_orden import (
    TubosOrdenError,
    cantidad_tubos_por_examenes,
    expandir_items_crear_muestras,
    resolver_tubos_para_solicitud,
    unidades_para_calculo_tubos,
)
from laboratorio.panel_componentes_orden import PANEL_COMPONENTES_BY_CODIGO
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.mark.django_db
class TestCantidadTubos(TestCase):
    def test_ceil_div_10(self):
        assert cantidad_tubos_por_examenes(0) == 0
        assert cantidad_tubos_por_examenes(1) == 1
        assert cantidad_tubos_por_examenes(10) == 1
        assert cantidad_tubos_por_examenes(11) == 2
        assert cantidad_tubos_por_examenes(20) == 2
        assert cantidad_tubos_por_examenes(21) == 3

    def test_unidades_hemograma_cuenta_como_uno(self):
        class _E:
            def __init__(self, codigo):
                self.codigo = codigo

        hemo = [_E(c) for c in PANEL_COMPONENTES_BY_CODIGO["PAN_HEMO"]]
        assert len(hemo) >= 11
        assert unidades_para_calculo_tubos(hemo) == 1
        assert unidades_para_calculo_tubos(hemo + [_E("HBA1C")]) == 2
        assert unidades_para_calculo_tubos([_E("GLU"), _E("UREA")]) == 2


@pytest.mark.django_db
class TestResolverTubosOrden(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:6]
        self.tm = TipoMuestra.objects.create(codigo=f"SG{self.suf}", nombre="Sangre", activo=True)
        self.edta = TipoContenedor.objects.create(codigo=f"EDTA{self.suf}", nombre="EDTA", activo=True)
        self.cit = TipoContenedor.objects.create(codigo=f"CIT{self.suf}", nombre="Citrato", activo=True)
        self.hep = TipoContenedor.objects.create(codigo=f"HEP{self.suf}", nombre="Heparina", activo=True)
        self.sue = TipoContenedor.objects.create(codigo=f"SUE{self.suf}", nombre="Suero", activo=True)
        self.pac_u = User.objects.create_user(
            username=f"p{self.suf}", email=f"p{self.suf}@t.com", password="x", rol="paciente"
        )
        self.paciente = Paciente.objects.create(
            dni=f"9{self.suf}", nombre="P", apellido="T", user=self.pac_u
        )
        esp = Especialidad.objects.create(nombre=f"E{self.suf}")
        med_u = User.objects.create_user(
            username=f"m{self.suf}", email=f"m{self.suf}@t.com", password="x", rol="medico"
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="Test",
            matricula=f"MT{self.suf}",
            especialidad=esp,
            user=med_u,
        )

    def _examen(self, codigo, contenedor):
        return TipoExamen.objects.create(
            codigo=f"{codigo}{self.suf}",
            nombre=codigo,
            tipo_muestra_requerida=self.tm,
            tipo_contenedor=contenedor,
            precio=1,
            activo=True,
        )

    def _solicitud(self, *examenes):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.tipos_examen.add(*examenes)
        return sol

    def test_cuatro_tubos_distintos(self):
        sol = self._solicitud(
            self._examen("HEMO", self.edta),
            self._examen("COAG", self.cit),
            self._examen("GLU", self.hep),
            self._examen("HIV", self.sue),
        )
        grupos = resolver_tubos_para_solicitud(sol)
        assert len(grupos) == 4
        assert sum(g.cantidad for g in grupos) == 4

    def test_doce_mismo_tubo_dos_fisicos(self):
        exams = [self._examen(f"P{i}", self.sue) for i in range(12)]
        sol = self._solicitud(*exams)
        grupos = resolver_tubos_para_solicitud(sol)
        assert len(grupos) == 1
        assert grupos[0].cantidad == 2
        assert grupos[0].tipo_contenedor_id == self.sue.pk
        items = expandir_items_crear_muestras(sol, grupos)
        assert len(items) == 2
        assert all(i["tipo_contenedor_id"] == self.sue.pk for i in items)

    def test_diez_mismo_tubo_uno(self):
        exams = [self._examen(f"Q{i}", self.sue) for i in range(10)]
        sol = self._solicitud(*exams)
        assert resolver_tubos_para_solicitud(sol)[0].cantidad == 1

    def test_once_mismo_tubo_dos(self):
        exams = [self._examen(f"R{i}", self.sue) for i in range(11)]
        sol = self._solicitud(*exams)
        assert resolver_tubos_para_solicitud(sol)[0].cantidad == 2

    def test_sin_tubos_en_catalogo_lista_vacia(self):
        te = TipoExamen.objects.create(
            codigo=f"NOT{self.suf}",
            nombre="Sin tubo",
            tipo_muestra_requerida=self.tm,
            tipo_contenedor=None,
            precio=1,
            activo=True,
        )
        sol = self._solicitud(te)
        assert resolver_tubos_para_solicitud(sol) == []

    def test_mezcla_parcial_error(self):
        con = self._examen("OK", self.edta)
        sin = TipoExamen.objects.create(
            codigo=f"NO{self.suf}",
            nombre="Sin",
            tipo_muestra_requerida=self.tm,
            tipo_contenedor=None,
            precio=1,
            activo=True,
        )
        sol = self._solicitud(con, sin)
        with self.assertRaises(TubosOrdenError):
            resolver_tubos_para_solicitud(sol)

    def test_panel_solo_resuelve_tubos_desde_componentes(self):
        from laboratorio.models import PanelExamen

        exams = [self._examen(f"H{i}", self.edta) for i in range(3)]
        panel = PanelExamen.objects.create(
            codigo=f"PAN{self.suf}", nombre="Hemograma", activo=True
        )
        panel.tipos_examen.add(*exams)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.paneles.add(panel)
        # Sin tipos_examen M2M (bug histórico de órdenes solo-panel)
        assert sol.tipos_examen.count() == 0
        grupos = resolver_tubos_para_solicitud(sol)
        assert len(grupos) == 1
        assert grupos[0].tipo_contenedor_id == self.edta.pk
        assert grupos[0].cantidad == 1
        assert len(grupos[0].examenes) == 3

    def test_hemograma_doce_componentes_un_solo_tubo_edta(self):
        from laboratorio.models import PanelExamen

        codigos = list(PANEL_COMPONENTES_BY_CODIGO["PAN_HEMO"])
        assert len(codigos) >= 11
        exams = []
        for codigo in codigos:
            te, _ = TipoExamen.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": codigo,
                    "tipo_muestra_requerida": self.tm,
                    "tipo_contenedor": self.edta,
                    "precio": 1,
                    "activo": True,
                },
            )
            if te.tipo_contenedor_id != self.edta.pk or te.tipo_muestra_requerida_id != self.tm.pk:
                te.tipo_contenedor = self.edta
                te.tipo_muestra_requerida = self.tm
                te.save(update_fields=["tipo_contenedor", "tipo_muestra_requerida"])
            exams.append(te)
        panel, _ = PanelExamen.objects.get_or_create(
            codigo="PAN_HEMO", defaults={"nombre": "Hemograma", "activo": True}
        )
        panel.tipos_examen.set(exams)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.paneles.add(panel)
        grupos = resolver_tubos_para_solicitud(sol)
        assert len(grupos) == 1
        assert grupos[0].cantidad == 1
        assert len(grupos[0].examenes) == len(codigos)
        assert expandir_items_crear_muestras(sol, grupos) == [
            {
                "tipo_muestra_id": self.tm.pk,
                "tipo_contenedor_id": self.edta.pk,
                "observaciones": "",
            }
        ]


@pytest.mark.django_db
class TestTomarMuestraAutoTubosAPI(TestCase):
    def setUp(self):
        self.suf = uuid.uuid4().hex[:6]
        self.lab = User.objects.create_user(
            username=f"lab{self.suf}",
            email=f"l{self.suf}@t.com",
            password="x",
            rol="laboratorio",
            is_staff=True,
        )
        self.tm = TipoMuestra.objects.create(codigo=f"S{self.suf}", nombre="Sangre", activo=True)
        self.sue = TipoContenedor.objects.create(codigo=f"SU{self.suf}", nombre="Suero", activo=True)
        self.pac_u = User.objects.create_user(
            username=f"px{self.suf}", email=f"px{self.suf}@t.com", password="x", rol="paciente"
        )
        self.paciente = Paciente.objects.create(
            dni=f"8{self.suf}", nombre="P", apellido="T", user=self.pac_u
        )
        esp = Especialidad.objects.create(nombre=f"Ex{self.suf}")
        med_u = User.objects.create_user(
            username=f"mx{self.suf}", email=f"mx{self.suf}@t.com", password="x", rol="medico"
        )
        self.medico = Medico.objects.create(
            nombre="Dr",
            apellido="Lab",
            matricula=f"MX{self.suf}",
            especialidad=esp,
            user=med_u,
        )
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_authenticate(self.lab)

    def test_tomar_auto_crea_dos_tubos_suero(self):
        exams = []
        for i in range(12):
            exams.append(
                TipoExamen.objects.create(
                    codigo=f"A{i}{self.suf}",
                    nombre=f"Ex {i}",
                    tipo_muestra_requerida=self.tm,
                    tipo_contenedor=self.sue,
                    precio=1,
                    activo=True,
                )
            )
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.tipos_examen.add(*exams)

        r_prev = self.client.get(f"/api/lab/solicitudes/{sol.pk}/tubos-preview/")
        self.assertEqual(r_prev.status_code, status.HTTP_200_OK)
        self.assertEqual(r_prev.json()["tubos"][0]["cantidad"], 2)

        r = self.client.post(f"/api/lab/solicitudes/{sol.pk}/tomar-muestra/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        muestras = Muestra.objects.filter(solicitud=sol)
        self.assertEqual(muestras.count(), 2)
        self.assertTrue(all(m.estado == "TOMADA" for m in muestras))
        self.assertTrue(all(m.tipo_contenedor_id == self.sue.pk for m in muestras))
        self.assertEqual(len({m.codigo_barra for m in muestras}), 2)
