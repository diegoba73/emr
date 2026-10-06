"""Tests del catálogo «Solicitud de análisis» en papel."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from laboratorio.catalogo_referencias_clinicas import REFERENCIAS_POR_CODIGO
from laboratorio.catalogo_solicitud_papel import (
    EXAMENES,
    EXAMENES_SUELTOS_PDF,
    PANELES,
)
from laboratorio.models import PanelExamen, TipoExamen
from laboratorio.panel_componentes_orden import ordenar_queryset_panel


@pytest.mark.django_db
class TestSeedCatalogoSolicitudPapel:
    def test_seed_idempotente(self):
        call_command("seed_catalogo_solicitud_papel")
        n_exam = TipoExamen.objects.filter(activo=True).count()
        n_pan = PanelExamen.objects.filter(activo=True).count()
        call_command("seed_catalogo_solicitud_papel")
        assert TipoExamen.objects.filter(activo=True).count() == n_exam
        assert PanelExamen.objects.filter(activo=True).count() == n_pan

    def test_cantidad_examenes_y_paneles(self):
        call_command("seed_catalogo_solicitud_papel")
        assert TipoExamen.objects.filter(codigo__in=[e["codigo"] for e in EXAMENES]).count() == len(
            EXAMENES
        )
        assert PanelExamen.objects.filter(activo=True).count() == len(PANELES)

    def test_hemograma_tiene_quince_componentes(self):
        call_command("seed_catalogo_solicitud_papel")
        panel = PanelExamen.objects.get(codigo="PAN_HEMO")
        assert panel.tipos_examen.count() == 15
        codigos = [te.codigo for te in ordenar_queryset_panel(panel)]
        assert codigos == [
            "HEMATIES", "HTO", "HGB", "RDW", "VCM", "HCM", "CHCM", "PLAQ", "LEUCO",
            "NEUT_CAY", "NEUT_SEG", "EOS", "BAS", "LINF", "MONO",
        ]

    def test_perfil_lipidico_y_hepatograma_derivados(self):
        call_command("seed_catalogo_solicitud_papel")
        lip = PanelExamen.objects.get(codigo="PAN_LIP")
        hep = PanelExamen.objects.get(codigo="PAN_HEP")
        assert [te.codigo for te in ordenar_queryset_panel(lip)] == [
            "COL_TOT", "LDL", "VLDL", "HDL", "TG", "COL_NO_LDL", "COL_RESID", "RATIO_CT_HDL",
        ]
        assert [te.codigo for te in ordenar_queryset_panel(hep)] == [
            "GOT", "GPT", "FAL", "BIL_T", "BIL_D", "BIL_I",
        ]
        assert TipoExamen.objects.get(codigo="LDL").modo_entrada == "CALCULADO"
        assert TipoExamen.objects.get(codigo="BIL_I").modo_entrada == "CALCULADO"
        assert TipoExamen.objects.get(codigo="COL_NO_LDL").nombre == "Colesterol no-HDL"

    def test_sin_duplicar_componentes_entre_registros(self):
        call_command("seed_catalogo_solicitud_papel")
        codigos = [e["codigo"] for e in EXAMENES]
        assert len(codigos) == len(set(codigos))

    def test_creatininemia_compartida_clearance_y_suelto(self):
        call_command("seed_catalogo_solicitud_papel")
        crea = TipoExamen.objects.get(codigo="CREATI")
        clear = PanelExamen.objects.get(codigo="PAN_CLEAR")
        assert clear.tipos_examen.filter(pk=crea.pk).exists()
        assert "CREATI" in EXAMENES_SUELTOS_PDF
        clear_crea = TipoExamen.objects.get(codigo="CLEAR_CREA")
        assert clear_crea.modo_entrada == "CALCULADO"
        assert clear_crea.requiere_muestra is False
        assert clear_crea.tipo_contenedor_id is None
        assert [te.codigo for te in ordenar_queryset_panel(clear)] == [
            "CREATI", "CREA_U", "DIUR", "CLEAR_CREA",
        ]

    def test_orina_completa_incluye_glucosa_tira(self):
        call_command("seed_catalogo_solicitud_papel")
        pan = PanelExamen.objects.get(codigo="PAN_ORI")
        glu = TipoExamen.objects.get(codigo="ORI_GLU")
        assert glu.tipo_resultado == "CUALITATIVO"
        assert glu.nombre == "Glucosa (orina)"
        assert [te.codigo for te in ordenar_queryset_panel(pan)] == [
            "ORI_COLOR", "ORI_ASP", "ORI_DENS", "ORI_PH", "ORI_GLU", "ORI_BIL",
            "ORI_NIT", "ORI_CET", "ORI_CEL", "ORI_LEU", "ORI_HEM", "ORI_PIO",
            "ORI_MUC", "ORI_CRIS", "ORI_CONC",
        ]

    def test_ionograma_urinario_comparte_electrolitos(self):
        call_command("seed_catalogo_solicitud_papel")
        pan_az = PanelExamen.objects.get(codigo="PAN_IONO_U")
        pan_24 = PanelExamen.objects.get(codigo="PAN_IONO_U24")
        ids_az = set(pan_az.tipos_examen.values_list("codigo", flat=True))
        assert ids_az == {"NA_U", "K_U", "CL_U"}
        assert [te.codigo for te in ordenar_queryset_panel(pan_24)] == [
            "NA_U", "K_U", "CL_U", "DIUR", "NA_U24", "K_U24", "CL_U24",
        ]
        assert ids_az.issubset(
            set(pan_24.tipos_examen.values_list("codigo", flat=True))
        )
        for codigo in ("NA_U24", "K_U24", "CL_U24"):
            assert TipoExamen.objects.get(codigo=codigo).modo_entrada == "CALCULADO"

    def test_paneles_orina_24h_calculados(self):
        call_command("seed_catalogo_solicitud_papel")
        prot = PanelExamen.objects.get(codigo="PAN_PROT24")
        malb = PanelExamen.objects.get(codigo="PAN_MALB24")
        assert [te.codigo for te in ordenar_queryset_panel(prot)] == [
            "PROT_U_EQ", "DIUR", "PROT_U_24",
        ]
        assert [te.codigo for te in ordenar_queryset_panel(malb)] == [
            "MICROALB", "DIUR", "MICROALB_24",
        ]
        assert TipoExamen.objects.get(codigo="PROT_U_24").modo_entrada == "CALCULADO"
        assert TipoExamen.objects.get(codigo="MICROALB_24").modo_entrada == "CALCULADO"
        assert "PROT_U_24" not in EXAMENES_SUELTOS_PDF

    def test_panel_malb_azar_incluye_rac_calculado(self):
        call_command("seed_catalogo_solicitud_papel")
        malb_az = PanelExamen.objects.get(codigo="PAN_MALB_AZ")
        assert [te.codigo for te in ordenar_queryset_panel(malb_az)] == [
            "MICROALB", "CREA_U", "RAC",
        ]
        rac = TipoExamen.objects.get(codigo="RAC")
        assert rac.modo_entrada == "CALCULADO"
        assert rac.requiere_muestra is False

    def test_legacy_hemo_desactivado(self):
        from laboratorio.models import TipoMuestra

        muestra, _ = TipoMuestra.objects.get_or_create(
            codigo="SANGRE",
            defaults={"nombre": "Sangre", "activo": True},
        )
        TipoExamen.objects.create(
            codigo="HEMO",
            nombre="Hemograma (legacy)",
            tipo_muestra_requerida=muestra,
            activo=True,
        )
        call_command("seed_catalogo_solicitud_papel")
        assert not TipoExamen.objects.get(codigo="HEMO").activo

    def test_eab_paneles_y_legacy_desactivado(self):
        from laboratorio.models import TipoMuestra

        muestra, _ = TipoMuestra.objects.get_or_create(
            codigo="SANGRE_HEPARINA_ART",
            defaults={"nombre": "Sangre heparina arterial", "activo": True},
        )
        TipoExamen.objects.create(
            codigo="EAB_ART",
            nombre="EAB arterial (legacy)",
            tipo_muestra_requerida=muestra,
            activo=True,
        )
        TipoExamen.objects.create(
            codigo="EAB_VEN",
            nombre="EAB venoso (legacy)",
            tipo_muestra_requerida=muestra,
            activo=True,
        )
        call_command("seed_catalogo_solicitud_papel")
        assert not TipoExamen.objects.get(codigo="EAB_ART").activo
        assert not TipoExamen.objects.get(codigo="EAB_VEN").activo
        pan_art = PanelExamen.objects.get(codigo="PAN_EAB_ART")
        pan_ven = PanelExamen.objects.get(codigo="PAN_EAB_VEN")
        assert [te.codigo for te in ordenar_queryset_panel(pan_art)] == [
            "FIO2", "PH_ART", "PO2_ART", "PCO2_ART", "SAT_O2_ART", "HCO3_ART", "BE_ART",
        ]
        assert [te.codigo for te in ordenar_queryset_panel(pan_ven)] == [
            "FIO2", "PH_VEN", "PO2_VEN", "PCO2_VEN", "SAT_O2_VEN", "HCO3_VEN", "BE_VEN",
        ]
        assert pan_art.tipos_examen.filter(codigo="FIO2").exists()
        assert pan_ven.tipos_examen.filter(codigo="FIO2").exists()
        fio2 = TipoExamen.objects.get(codigo="FIO2")
        assert fio2.tipo_contenedor_id is None
        assert fio2.requiere_muestra is False
        assert "EAB_ART" not in EXAMENES_SUELTOS_PDF
        assert "EAB_VEN" not in EXAMENES_SUELTOS_PDF

    def test_perfil_ferrico_medidos_y_calculados(self):
        call_command("seed_catalogo_solicitud_papel")
        panel = PanelExamen.objects.get(codigo="PAN_FERR")
        assert [te.codigo for te in ordenar_queryset_panel(panel)] == [
            "FERR", "UIBC", "FERRIT", "CF", "SAT_FE", "TRANS",
        ]
        assert TipoExamen.objects.get(codigo="CF").modo_entrada == "CALCULADO"
        assert TipoExamen.objects.get(codigo="SAT_FE").modo_entrada == "CALCULADO"
        assert TipoExamen.objects.get(codigo="TRANS").modo_entrada == "CALCULADO"
        assert TipoExamen.objects.get(codigo="CF").requiere_muestra is False
        assert TipoExamen.objects.get(codigo="CF").tipo_contenedor_id is None
        assert TipoExamen.objects.get(codigo="CF").nombre == "Capacidad total de fijación"
        assert TipoExamen.objects.get(codigo="UIBC").modo_entrada != "CALCULADO"
        assert TipoExamen.objects.get(codigo="UIBC").requiere_muestra is True

    def test_referencias_cargadas_en_catalogo(self):
        call_command("seed_catalogo_solicitud_papel")
        glu = TipoExamen.objects.get(codigo="GLU")
        assert glu.metodo
        assert glu.unidad_default == "mg/dL"
        assert "70" in (glu.rango_referencia_texto or "")
        assert glu.rango_min is not None
        assert glu.rango_max is not None

    def test_todos_los_examenes_tienen_referencia(self):
        codigos = {e["codigo"] for e in EXAMENES}
        assert codigos == set(REFERENCIAS_POR_CODIGO.keys())
        for codigo, ref in REFERENCIAS_POR_CODIGO.items():
            assert ref.get("metodo"), f"{codigo} sin método"
            assert ref.get("rango_referencia_texto"), f"{codigo} sin rango texto"
