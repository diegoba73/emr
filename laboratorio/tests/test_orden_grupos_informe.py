"""Tests de orden de grupos en informe PDF."""
from __future__ import annotations

import uuid

import pytest
from django.test import TestCase

from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.orden_grupos_informe import (
    PANEL_HEMOGRAMA,
    aplicar_orden_grupos,
    construir_grupos_informe,
    grupo_key_inferido,
    grupo_key_panel,
    ordenar_grupos_por_defecto,
)
from pacientes.models import Paciente


@pytest.mark.django_db
class TestOrdenGruposInforme(TestCase):
    def setUp(self):
        tag = uuid.uuid4().hex[:6]
        self.tm_sangre = TipoMuestra.objects.create(codigo=f"S{tag}", nombre="Sangre", activo=True)
        self.tm_orina = TipoMuestra.objects.create(codigo=f"O{tag}", nombre="Orina", activo=True)

        self.te_glu, _ = TipoExamen.objects.update_or_create(
            codigo="GLU",
            defaults={
                "nombre": "Glucemia",
                "tipo_muestra_requerida": self.tm_sangre,
                "precio": 1,
                "activo": True,
            },
        )
        self.te_cpk, _ = TipoExamen.objects.update_or_create(
            codigo="CPK",
            defaults={
                "nombre": "CPK",
                "tipo_muestra_requerida": self.tm_sangre,
                "precio": 1,
                "activo": True,
            },
        )
        self.te_wbc = TipoExamen.objects.create(
            codigo=f"WBC{tag}",
            nombre="Leucocitos",
            tipo_muestra_requerida=self.tm_sangre,
            precio=1,
            activo=True,
        )
        self.te_ph = TipoExamen.objects.create(
            codigo=f"PHU{tag}",
            nombre="pH orina",
            tipo_muestra_requerida=self.tm_orina,
            precio=1,
            activo=True,
        )
        self.te_got, _ = TipoExamen.objects.update_or_create(
            codigo="GOT",
            defaults={
                "nombre": "GOT (AST)",
                "tipo_muestra_requerida": self.tm_sangre,
                "precio": 1,
                "activo": True,
            },
        )
        self.te_gpt, _ = TipoExamen.objects.update_or_create(
            codigo="GPT",
            defaults={
                "nombre": "GPT (ALT)",
                "tipo_muestra_requerida": self.tm_sangre,
                "precio": 1,
                "activo": True,
            },
        )

        self.panel_hemo, _ = PanelExamen.objects.update_or_create(
            codigo=PANEL_HEMOGRAMA,
            defaults={"nombre": "Hemograma", "activo": True},
        )
        self.panel_hemo.tipos_examen.set([self.te_wbc])

        self.panel_iono, _ = PanelExamen.objects.update_or_create(
            codigo="PAN_IONO",
            defaults={"nombre": "Ionograma plasmático", "activo": True},
        )
        self.panel_iono.tipos_examen.set([self.te_glu])

        self.panel_orina, _ = PanelExamen.objects.update_or_create(
            codigo="PAN_ORI",
            defaults={"nombre": "Orina completa", "activo": True},
        )
        self.panel_orina.tipos_examen.set([self.te_ph])

        self.paciente = Paciente.objects.create(dni=f"D{tag}", nombre="Ana", apellido="Test")
        self.sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        self.sol.paneles.add(self.panel_iono, self.panel_hemo, self.panel_orina)

        self.r_hemo = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te_wbc, valor_obtenido="5"
        )
        self.r_iono = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te_glu, valor_obtenido="90"
        )
        self.r_orina = ResultadoExamen.objects.create(
            solicitud=self.sol, tipo_examen=self.te_ph, valor_obtenido="6"
        )

    def test_orden_defecto_sigue_presentacion_pedido(self):
        resultados = list(self.sol.resultados.select_related("tipo_examen").all())
        grupos = ordenar_grupos_por_defecto(construir_grupos_informe(self.sol, resultados))
        keys = [g.key for g in grupos]
        # Hemograma → Ionograma → orina completa al final
        self.assertEqual(keys[0], grupo_key_panel(self.panel_hemo.pk))
        self.assertEqual(keys[-1], grupo_key_panel(self.panel_orina.pk))
        self.assertLess(
            keys.index(grupo_key_panel(self.panel_hemo.pk)),
            keys.index(grupo_key_panel(self.panel_iono.pk)),
        )
        self.assertLess(
            keys.index(grupo_key_panel(self.panel_iono.pk)),
            keys.index(grupo_key_panel(self.panel_orina.pk)),
        )

    def test_bloque_orina_al_final_y_orina_completa_ultima(self):
        from laboratorio.orden_grupos_informe import PANEL_ORINA_COMPLETA

        tag = uuid.uuid4().hex[:6]
        te_na_u = TipoExamen.objects.create(
            codigo=f"NAU{tag}",
            nombre="Sodio urinario",
            tipo_muestra_requerida=self.tm_orina,
            precio=1,
            activo=True,
        )
        # Forzar código canónico para ranking de orina
        te_na_u.codigo = "NA_U"
        te_na_u.save(update_fields=["codigo"])

        panel_iono_u, _ = PanelExamen.objects.update_or_create(
            codigo="PAN_IONO_U",
            defaults={"nombre": "Ionograma urinario al azar", "activo": True},
        )
        panel_iono_u.tipos_examen.set([te_na_u])

        panel_clear, _ = PanelExamen.objects.update_or_create(
            codigo="PAN_CLEAR",
            defaults={"nombre": "Clearance de creatinina", "activo": True},
        )
        # Clearance usa creatininemia (sangre) + orina; el panel igual es bloque orina
        panel_clear.tipos_examen.set([self.te_glu])

        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.paneles.add(self.panel_hemo, panel_iono_u, panel_clear, self.panel_orina)
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_wbc, valor_obtenido="5")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=te_na_u, valor_obtenido="40")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_glu, valor_obtenido="1")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_ph, valor_obtenido="6")

        resultados = list(sol.resultados.select_related("tipo_examen", "tipo_examen__tipo_muestra_requerida").all())
        grupos = ordenar_grupos_por_defecto(construir_grupos_informe(sol, resultados))
        keys = [g.key for g in grupos]
        codes = [g.panel_codigo for g in grupos]

        self.assertEqual(keys[0], grupo_key_panel(self.panel_hemo.pk))
        # Todo el bloque orina al final; orina completa última
        self.assertEqual(codes[-1], PANEL_ORINA_COMPLETA)
        orina_codes = [c for c in codes if c in {"PAN_IONO_U", "PAN_CLEAR", "PAN_ORI"}]
        self.assertEqual(orina_codes[-1], "PAN_ORI")
        self.assertEqual(len(orina_codes), 3)
        # Hemograma no está mezclado después de orinas
        self.assertLess(keys.index(grupo_key_panel(self.panel_hemo.pk)), keys.index(grupo_key_panel(panel_iono_u.pk)))

    def test_orden_presentacion_glucemia_antes_que_cpk(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.te_cpk, self.te_glu)
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_cpk, valor_obtenido="10")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_glu, valor_obtenido="90")
        resultados = list(sol.resultados.select_related("tipo_examen").all())
        grupos = ordenar_grupos_por_defecto(construir_grupos_informe(sol, resultados))
        codigos = [
            (g.resultados[0].tipo_examen.codigo if g.resultados else None) for g in grupos
        ]
        self.assertEqual(codigos, ["GLU", "CPK"])

    def test_orden_presentacion_hemo_quimica_hep_cpk_orina(self):
        te_urea, _ = TipoExamen.objects.update_or_create(
            codigo="UREA",
            defaults={
                "nombre": "Uremia",
                "tipo_muestra_requerida": self.tm_sangre,
                "precio": 1,
                "activo": True,
            },
        )
        te_na, _ = TipoExamen.objects.update_or_create(
            codigo="NA",
            defaults={
                "nombre": "Sodio",
                "tipo_muestra_requerida": self.tm_sangre,
                "precio": 1,
                "activo": True,
            },
        )
        panel_hep, _ = PanelExamen.objects.update_or_create(
            codigo="PAN_HEP",
            defaults={"nombre": "Hepatograma", "activo": True},
        )
        panel_hep.tipos_examen.set([self.te_got, self.te_gpt])
        panel_iono, _ = PanelExamen.objects.update_or_create(
            codigo="PAN_IONO",
            defaults={"nombre": "Ionograma plasmático", "activo": True},
        )
        panel_iono.tipos_examen.set([te_na])

        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.paneles.add(self.panel_hemo, panel_hep, panel_iono, self.panel_orina)
        sol.tipos_examen.add(self.te_glu, te_urea, self.te_cpk)
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_wbc, valor_obtenido="5")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_glu, valor_obtenido="90")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=te_urea, valor_obtenido="30")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_got, valor_obtenido="20")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_gpt, valor_obtenido="25")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=te_na, valor_obtenido="140")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_cpk, valor_obtenido="10")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_ph, valor_obtenido="6")

        resultados = list(
            sol.resultados.select_related("tipo_examen", "tipo_examen__tipo_muestra_requerida")
        )
        grupos = ordenar_grupos_por_defecto(construir_grupos_informe(sol, resultados))
        codes = [
            g.panel_codigo or (g.resultados[0].tipo_examen.codigo if g.resultados else None)
            for g in grupos
        ]
        # Hemograma → química suelta → Hepatograma → Ionograma → CPK → orina última
        self.assertEqual(codes[0], "PAN_HEMO")
        self.assertEqual(codes[-1], "PAN_ORI")
        self.assertLess(codes.index("GLU"), codes.index("UREA"))
        self.assertLess(codes.index("UREA"), codes.index("PAN_HEP"))
        self.assertLess(codes.index("PAN_HEP"), codes.index("PAN_IONO"))
        self.assertLess(codes.index("PAN_IONO"), codes.index("CPK"))
        self.assertLess(codes.index("CPK"), codes.index("PAN_ORI"))
        self.assertNotIn("GOT", codes)
        self.assertNotIn("GPT", codes)

    def test_infiere_perfil_hepatograma_sin_panel_pedido(self):
        sol = SolicitudExamen.objects.create(
            paciente=self.paciente,
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(self.te_got, self.te_gpt, self.te_glu)
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_got, valor_obtenido="20")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_gpt, valor_obtenido="25")
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=self.te_glu, valor_obtenido="90")
        resultados = list(sol.resultados.select_related("tipo_examen").all())
        grupos = ordenar_grupos_por_defecto(construir_grupos_informe(sol, resultados))
        keys = [g.key for g in grupos]
        self.assertIn(grupo_key_inferido("PAN_HEP"), keys)
        hep = next(g for g in grupos if g.key == grupo_key_inferido("PAN_HEP"))
        self.assertTrue(hep.es_perfil)
        self.assertEqual(len(hep.resultados), 2)
        glu = next(g for g in grupos if not g.es_perfil)
        self.assertEqual(glu.resultados[0].tipo_examen.codigo, "GLU")
        self.assertFalse(glu.es_perfil)

    def test_orden_custom_persistido(self):
        resultados = list(self.sol.resultados.select_related("tipo_examen").all())
        specs = construir_grupos_informe(self.sol, resultados)
        custom = [
            grupo_key_panel(self.panel_orina.pk),
            grupo_key_panel(self.panel_iono.pk),
            grupo_key_panel(self.panel_hemo.pk),
        ]
        ordered = aplicar_orden_grupos(specs, custom)
        self.assertEqual([g.key for g in ordered], custom)
