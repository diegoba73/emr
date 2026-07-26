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
        assert unidades_para_calculo_tubos([_E("AU"), _E("TSH")]) == 2

    def test_unidades_orina_completa_cuenta_como_uno(self):
        class _E:
            def __init__(self, codigo):
                self.codigo = codigo

        orina = [_E(c) for c in PANEL_COMPONENTES_BY_CODIGO["PAN_ORI"]]
        assert len(orina) > 10
        assert unidades_para_calculo_tubos(orina) == 1
        assert unidades_para_calculo_tubos(orina + [_E("PROT_U_AZ")]) == 2
        assert unidades_para_calculo_tubos(orina + [_E("HEMATIES")]) == 2

    def test_unidades_quimica_rutina_cuenta_como_uno(self):
        class _E:
            def __init__(self, codigo):
                self.codigo = codigo

        from laboratorio.tubos_catalogo import _QUIMICA_RUTINA

        quimica = [_E(c) for c in sorted(_QUIMICA_RUTINA)]
        assert len(quimica) >= 10
        assert unidades_para_calculo_tubos(quimica) == 1
        assert unidades_para_calculo_tubos(quimica + [_E("AU")]) == 2
        assert unidades_para_calculo_tubos(quimica + [_E("EAB_ART")]) == 2


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

    def test_mismo_tubo_distinta_muestra_genera_grupos_separados(self):
        """EDTA + SANGRE_EDTA y EDTA + PLASMA no deben fallar: 2 muestras físicas."""
        tm_plasma = TipoMuestra.objects.create(
            codigo=f"PL{self.suf}", nombre="Plasma EDTA", activo=True
        )
        e1 = self._examen("HGB", self.edta)
        e2 = TipoExamen.objects.create(
            codigo=f"HB{self.suf}",
            nombre="Hb IACA",
            tipo_muestra_requerida=tm_plasma,
            tipo_contenedor=self.edta,
            precio=1,
            activo=True,
        )
        sol = self._solicitud(e1, e2)
        grupos = resolver_tubos_para_solicitud(sol)
        assert len(grupos) == 2
        assert all(g.tipo_contenedor_id == self.edta.pk for g in grupos)
        assert {g.tipo_muestra_id for g in grupos} == {self.tm.pk, tm_plasma.pk}
        assert sum(g.cantidad for g in grupos) == 2

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

    def test_hemograma_catorce_componentes_un_solo_tubo_edta(self):
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

    def test_orina_completa_catorce_componentes_un_solo_frasco(self):
        from laboratorio.models import PanelExamen

        tm_orina = TipoMuestra.objects.create(
            codigo=f"OR{self.suf}", nombre="Orina", activo=True
        )
        frasco = TipoContenedor.objects.create(
            codigo=f"FO{self.suf}", nombre="Frasco orina", activo=True
        )
        codigos = list(PANEL_COMPONENTES_BY_CODIGO["PAN_ORI"])
        assert len(codigos) > 10
        exams = []
        for codigo in codigos:
            te, _ = TipoExamen.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": codigo,
                    "tipo_muestra_requerida": tm_orina,
                    "tipo_contenedor": frasco,
                    "precio": 1,
                    "activo": True,
                },
            )
            if te.tipo_contenedor_id != frasco.pk or te.tipo_muestra_requerida_id != tm_orina.pk:
                te.tipo_contenedor = frasco
                te.tipo_muestra_requerida = tm_orina
                te.save(update_fields=["tipo_contenedor", "tipo_muestra_requerida"])
            exams.append(te)
        panel, _ = PanelExamen.objects.get_or_create(
            codigo="PAN_ORI", defaults={"nombre": "Orina completa", "activo": True}
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
                "tipo_muestra_id": tm_orina.pk,
                "tipo_contenedor_id": frasco.pk,
                "observaciones": "",
            }
        ]

    def test_orina_24h_varios_examenes_un_solo_bidon(self):
        from laboratorio.models import PanelExamen
        from laboratorio.tubos_catalogo import BIDON_ORINA_24H, MUESTRA_ORINA_24H

        tm_24, _ = TipoMuestra.objects.get_or_create(
            codigo=MUESTRA_ORINA_24H,
            defaults={"nombre": "Orina 24 hs", "activo": True},
        )
        bidon, _ = TipoContenedor.objects.get_or_create(
            codigo=BIDON_ORINA_24H,
            defaults={"nombre": "Bidón 24 hs", "activo": True},
        )
        if not bidon.activo:
            bidon.activo = True
            bidon.save(update_fields=["activo"])
        frasco = TipoContenedor.objects.create(
            codigo=f"FO{self.suf}", nombre="Frasco", activo=True
        )
        tm_ori = TipoMuestra.objects.create(codigo=f"OR{self.suf}", nombre="Orina", activo=True)

        # Clearance urine parts + proteinuria 24h → 1 bidón
        exams_24 = []
        for codigo in ("CLEAR_CREA", "DIUR", "CREA_U", "PROT_U_24"):
            te, _ = TipoExamen.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": codigo,
                    "tipo_muestra_requerida": tm_24 if codigo != "CREA_U" else tm_ori,
                    "tipo_contenedor": bidon if codigo != "CREA_U" else frasco,
                    "precio": 1,
                    "activo": True,
                },
            )
            te.tipo_muestra_requerida = tm_24 if codigo != "CREA_U" else tm_ori
            te.tipo_contenedor = bidon if codigo != "CREA_U" else frasco
            te.save(update_fields=["tipo_muestra_requerida", "tipo_contenedor"])
            exams_24.append(te)

        # Orina completa stays on frasco
        ori = TipoExamen.objects.create(
            codigo=f"ORI_PH{self.suf}",
            nombre="pH orina",
            tipo_muestra_requerida=tm_ori,
            tipo_contenedor=frasco,
            precio=1,
            activo=True,
        )

        panel, _ = PanelExamen.objects.get_or_create(
            codigo="PAN_CLEAR", defaults={"nombre": "Clearance", "activo": True}
        )
        panel.tipos_examen.set(exams_24)
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        sol.paneles.add(panel)
        sol.tipos_examen.add(ori)

        grupos = resolver_tubos_para_solicitud(sol)
        by_tc = {g.tipo_contenedor_codigo: g for g in grupos}
        assert BIDON_ORINA_24H in by_tc
        assert by_tc[BIDON_ORINA_24H].cantidad == 1
        # Dual CREA_U remapped into bidón because PAN_CLEAR
        assert len(by_tc[BIDON_ORINA_24H].examenes) == 4
        assert frasco.codigo in by_tc
        assert by_tc[frasco.codigo].cantidad == 1

    def test_eab_art_y_ven_dos_jeringas(self):
        tm_art = TipoMuestra.objects.create(
            codigo=f"ART{self.suf}", nombre="Sangre heparina arterial", activo=True
        )
        tm_ven = TipoMuestra.objects.create(
            codigo=f"VEN{self.suf}", nombre="Sangre heparina venosa", activo=True
        )
        eab_a, _ = TipoExamen.objects.update_or_create(
            codigo="EAB_ART",
            defaults={
                "nombre": "EAB arterial",
                "tipo_muestra_requerida": tm_art,
                "tipo_contenedor": self.hep,
                "precio": 1,
                "activo": True,
            },
        )
        eab_v, _ = TipoExamen.objects.update_or_create(
            codigo="EAB_VEN",
            defaults={
                "nombre": "EAB venoso",
                "tipo_muestra_requerida": tm_ven,
                "tipo_contenedor": self.hep,
                "precio": 1,
                "activo": True,
            },
        )
        eab_a.tipo_muestra_requerida = tm_art
        eab_a.tipo_contenedor = self.hep
        eab_a.save(update_fields=["tipo_muestra_requerida", "tipo_contenedor"])
        eab_v.tipo_muestra_requerida = tm_ven
        eab_v.tipo_contenedor = self.hep
        eab_v.save(update_fields=["tipo_muestra_requerida", "tipo_contenedor"])

        sol = self._solicitud(eab_a, eab_v)
        grupos = resolver_tubos_para_solicitud(sol)
        assert len(grupos) == 2
        assert all(g.cantidad == 1 for g in grupos)
        assert sum(g.cantidad for g in grupos) == 2
        items = expandir_items_crear_muestras(sol, grupos)
        assert len(items) == 2


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
        self.assertTrue(all(m.estado == "PENDIENTE_TOMA" for m in muestras))
        self.assertTrue(all(m.tipo_contenedor_id == self.sue.pk for m in muestras))
        self.assertEqual(len({m.codigo_barra for m in muestras}), 2)
