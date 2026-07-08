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

    def test_hemograma_tiene_doce_componentes(self):
        call_command("seed_catalogo_solicitud_papel")
        panel = PanelExamen.objects.get(codigo="PAN_HEMO")
        assert panel.tipos_examen.count() == 12
        codigos = [te.codigo for te in ordenar_queryset_panel(panel)]
        assert codigos == [
            "HEMATIES", "HTO", "HGB", "RDW", "LEU", "NEUT_CAY", "NEUT_SEG",
            "EOS", "BAS", "LINF", "MONO", "PLAQ",
        ]

    def test_sin_duplicar_componentes_entre_registros(self):
        call_command("seed_catalogo_solicitud_papel")
        codigos = [e["codigo"] for e in EXAMENES]
        assert len(codigos) == len(set(codigos))

    def test_creatininemia_compartida_clearance_y_suelto(self):
        call_command("seed_catalogo_solicitud_papel")
        crea = TipoExamen.objects.get(codigo="CREA")
        clear = PanelExamen.objects.get(codigo="PAN_CLEAR")
        assert clear.tipos_examen.filter(pk=crea.pk).exists()
        assert "CREA" in EXAMENES_SUELTOS_PDF

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
