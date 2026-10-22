"""Tests del catálogo / seed / API de materiales de pedido."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from laboratorio.materiales_pedido_catalogo import (
    MATERIALES_PEDIDO,
    as_api_list,
    grilla_codigos_material,
    material_por_codigo,
    panel_diferencial_de_material,
    rank_presentacion_codigo_material,
    todos_examenes_materiales,
)
from laboratorio.models import PanelExamen, TipoExamen, TipoMuestra
from laboratorio.models_microbiologia import TipoCultivoMicrobiologia
from laboratorio.tubos_catalogo import FRASCO_ESTERIL, tubo_codigo_para_examen


def test_codigos_examen_max_20():
    for ex in todos_examenes_materiales():
        assert len(ex.codigo) <= 20, ex.codigo


def test_lcr_bloque_celular_y_bioquimica():
    mat = material_por_codigo("LCR")
    assert mat is not None
    codes = set(grilla_codigos_material(mat))
    assert "RBC_LCR" in codes
    assert "NC_LCR" in codes
    assert "PAN_DIF_LCR" in codes
    assert "CITOL_LCR" in codes
    assert "GLU_LCR" in codes
    # Independiente del hemograma
    assert "HEMATIES" not in codes
    assert "LEUCO" not in codes
    pan = panel_diferencial_de_material(mat)
    assert pan is not None
    assert set(pan.componentes) == {
        "NEUT_LCR",
        "LINF_LCR",
        "MOMA_LCR",
        "EOS_LCR",
        "OTRA_LCR",
    }


def test_grilla_orden_fisicos_celulares_quimicos():
    """En líquidos: aspecto/color → recuentos/dif → química."""
    lcr = material_por_codigo("LCR")
    assert lcr is not None
    assert grilla_codigos_material(lcr) == [
        "ASP_LCR",
        "COL_LCR",
        "RBC_LCR",
        "NC_LCR",
        "PAN_DIF_LCR",
        "CITOL_LCR",
        "GLU_LCR",
        "PROT_LCR",
        "LACT_LCR",
    ]
    ple = material_por_codigo("LIQ_PLEURAL")
    assert ple is not None
    g = grilla_codigos_material(ple)
    assert g.index("ASP_PLE") < g.index("PH_PLE") < g.index("RBC_PLE")
    assert g.index("RBC_PLE") < g.index("PAN_DIF_PLE") < g.index("PROT_PLE")
    assert g.index("HTO_PLE") < g.index("GLU_PLE")
    asc = material_por_codigo("LIQ_ASCITICO")
    assert asc is not None
    ga = grilla_codigos_material(asc)
    assert ga.index("ASP_ASC") < ga.index("RAN_ASC") < ga.index("ALB_ASC")
    assert ga.index("PAN_DIF_ASC") < ga.index("GLU_ASC")


def test_rank_presentacion_material_no_toca_sangre():
    assert rank_presentacion_codigo_material("GLU") is None
    assert rank_presentacion_codigo_material("PAN_HEMO") is None
    assert rank_presentacion_codigo_material("ASP_LCR") is not None
    assert rank_presentacion_codigo_material("ASP_LCR") < rank_presentacion_codigo_material(
        "RBC_LCR"
    )
    assert rank_presentacion_codigo_material("RBC_LCR") < rank_presentacion_codigo_material(
        "GLU_LCR"
    )


def test_ascitico_y_peritoneal_cultivos_distintos():
    asc = material_por_codigo("LIQ_ASCITICO")
    per = material_por_codigo("LIQ_PERITON")
    assert asc and per
    assert asc.cultivo_micro == "LIQUIDO_ASCITICO"
    assert per.cultivo_micro == "LIQUIDO_PERITONEAL"
    assert asc.cultivo_micro != per.cultivo_micro


def test_sudor_solo_clinico():
    sud = material_por_codigo("SUDOR")
    assert sud is not None
    assert sud.cultivo_micro is None
    assert "CL_SUD" in grilla_codigos_material(sud)


def test_api_list_shape():
    rows = as_api_list()
    assert len(rows) == len(MATERIALES_PEDIDO)
    lcr = next(r for r in rows if r["codigo"] == "LCR")
    assert "PAN_DIF_LCR" in lcr["grilla_codigos"]
    assert lcr["cultivo_micro_codigo"] == "LCR"
    sangre = next(r for r in rows if r["codigo"] == "SANGRE")
    assert "SUERO" in sangre["tipo_muestra_codigos"]
    assert "PLASMA_EDTA" in sangre["tipo_muestra_codigos"]


@pytest.mark.django_db
def test_api_sangre_incluye_variantes_de_bd():
    TipoMuestra.objects.get_or_create(
        codigo="SANGRE_SECA_EN_PAPEL_FILTRO",
        defaults={"nombre": "Sangre seca papel filtro", "activo": True},
    )
    rows = as_api_list()
    sangre = next(r for r in rows if r["codigo"] == "SANGRE")
    assert "SANGRE_SECA_EN_PAPEL_FILTRO" in sangre["tipo_muestra_codigos"]
    assert "ORINA" not in sangre["tipo_muestra_codigos"]
    assert "PLASMA_SEMINAL" not in sangre["tipo_muestra_codigos"]


def test_tubo_esteril_para_muestra_lcr():
    assert tubo_codigo_para_examen("GLU_LCR", "LCR") == FRASCO_ESTERIL
    assert tubo_codigo_para_examen("LACT_LCR", "LCR") == FRASCO_ESTERIL
    # Homónimo de sangre: con muestra LCR gana frasco estéril.
    assert tubo_codigo_para_examen("LACT", "LCR") == FRASCO_ESTERIL
    assert tubo_codigo_para_examen("ASP_LCR", None) == FRASCO_ESTERIL


def test_tubo_esteril_para_muestra_esputo():
    assert tubo_codigo_para_examen("CITOL_ESP", "ESPUTO") == FRASCO_ESTERIL
    assert tubo_codigo_para_examen("CITOL_ESP", None) == FRASCO_ESTERIL
    assert tubo_codigo_para_examen("X", "ESPUTO") == FRASCO_ESTERIL


@pytest.mark.django_db
def test_seed_materiales_pedido_idempotente():
    call_command("seed_materiales_pedido")
    n1 = TipoExamen.objects.filter(codigo="GLU_LCR").count()
    assert n1 == 1
    glu = TipoExamen.objects.get(codigo="GLU_LCR")
    assert glu.tipo_muestra_requerida.codigo == "LCR"
    assert glu.unidad_default == "mg/dL"
    assert TipoMuestra.objects.filter(codigo="LCR", activo=True).exists()
    pan = PanelExamen.objects.get(codigo="PAN_DIF_LCR")
    assert pan.tipos_examen.count() == 5
    assert TipoCultivoMicrobiologia.objects.filter(
        codigo="LIQUIDO_ASCITICO", activo=True
    ).exists()
    rbc = TipoExamen.objects.get(codigo="RBC_LCR")
    assert rbc.unidad_default == "células/µL"
    assert rbc.codigo != "HEMATIES"

    call_command("seed_materiales_pedido")
    assert TipoExamen.objects.filter(codigo="GLU_LCR").count() == 1


@pytest.mark.django_db
def test_api_materiales_pedido_requires_auth(django_user_model):
    client = APIClient()
    url = reverse("laboratorio-materiales-pedido")
    assert client.get(url).status_code in (401, 403)
    user = django_user_model.objects.create_user(
        username="mat_pedido_u", password="x", rol="admin"
    )
    client.force_authenticate(user=user)
    r = client.get(url)
    assert r.status_code == 200
    assert any(row["codigo"] == "LCR" for row in r.data)

