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

    def test_hemograma_tiene_catorce_componentes(self):
        call_command("seed_catalogo_solicitud_papel")
        panel = PanelExamen.objects.get(codigo="PAN_HEMO")
        assert panel.tipos_examen.count() == 14
        codigos = [te.codigo for te in ordenar_queryset_panel(panel)]
        assert codigos == [
            "HEMATIES", "HTO", "HGB", "VCM", "CHCM", "RDW", "LEUCO", "NEUT_CAY",
            "NEUT_SEG", "EOS", "BAS", "LINF", "MONO", "PLAQ",
        ]

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

    def test_ionograma_urinario_comparte_electrolitos(self):
        call_command("seed_catalogo_solicitud_papel")
        pan_az = PanelExamen.objects.get(codigo="PAN_IONO_U")
        pan_24 = PanelExamen.objects.get(codigo="PAN_IONO_U24")
        ids_az = set(pan_az.tipos_examen.values_list("codigo", flat=True))
        ids_24 = set(pan_24.tipos_examen.values_list("codigo", flat=True))
        assert ids_az == ids_24 == {"NA_U", "K_U", "CL_U"}

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
            "PH_ART", "PO2_ART", "PCO2_ART", "SAT_O2_ART", "HCO3_ART", "BE_ART",
        ]
        assert [te.codigo for te in ordenar_queryset_panel(pan_ven)] == [
            "PH_VEN", "PO2_VEN", "PCO2_VEN", "SAT_O2_VEN", "HCO3_VEN", "BE_VEN",
        ]
        assert "EAB_ART" not in EXAMENES_SUELTOS_PDF
        assert "EAB_VEN" not in EXAMENES_SUELTOS_PDF

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
