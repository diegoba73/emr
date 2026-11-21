"""Acompañamiento clínico: coag→PLAQ y EAB→HTO si no hay hemograma."""
from io import StringIO

import pytest
from django.core.management import call_command

from laboratorio.acompanamiento_pedido import codigos_acompanamiento_pedido
from laboratorio.hemograma_resultados import asegurar_resultados_paneles_derivados
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.solicitud_orden_abierta import agregar_examenes_a_solicitud
from pacientes.models import Paciente
from usuarios.models import User


def test_coag_sin_hemo_pide_plaq():
    assert codigos_acompanamiento_pedido(
        codigos_examen=set(),
        codigos_panel={"PAN_COAG"},
    ) == ["PLAQ"]


def test_coag_con_hemo_no_pide_plaq():
    assert (
        codigos_acompanamiento_pedido(
            codigos_examen=set(),
            codigos_panel={"PAN_COAG", "PAN_HEMO"},
        )
        == []
    )


def test_coag_con_plaq_ya_presente():
    assert (
        codigos_acompanamiento_pedido(
            codigos_examen={"PLAQ"},
            codigos_panel={"PAN_COAG"},
        )
        == []
    )


def test_eab_sin_hemo_pide_hto():
    assert codigos_acompanamiento_pedido(
        codigos_examen=set(),
        codigos_panel={"PAN_EAB_ART"},
    ) == ["HTO"]
    assert codigos_acompanamiento_pedido(
        codigos_examen=set(),
        codigos_panel={"PAN_EAB_VEN"},
    ) == ["HTO"]


def test_eab_con_hemo_no_pide_hto():
    assert (
        codigos_acompanamiento_pedido(
            codigos_examen=set(),
            codigos_panel={"PAN_EAB_ART", "PAN_HEMO"},
        )
        == []
    )


def test_eab_con_hto_ya_presente():
    assert (
        codigos_acompanamiento_pedido(
            codigos_examen={"HTO"},
            codigos_panel={"PAN_EAB_VEN"},
        )
        == []
    )


def test_eab_y_coag_sin_hemo_pide_plaq_y_hto():
    assert codigos_acompanamiento_pedido(
        codigos_examen=set(),
        codigos_panel={"PAN_COAG", "PAN_EAB_ART"},
    ) == ["PLAQ", "HTO"]


@pytest.mark.django_db
def test_agregar_coag_suelto_trae_plaq(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-COAG1", nombre="Prueba", apellido="Coag"
    )
    actor = User.objects.create_user(username="prueba-coag1", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    coag = PanelExamen.objects.get(codigo="PAN_COAG")
    agregar_examenes_a_solicitud(sol, paneles_ids=[coag.pk], user=actor)
    sol.refresh_from_db()
    codigos = set(sol.resultados.values_list("tipo_examen__codigo", flat=True))
    assert "PLAQ" in codigos
    assert sol.paneles.filter(codigo="PAN_COAG").exists()
    assert not sol.paneles.filter(codigo="PAN_HEMO").exists()


@pytest.mark.django_db
def test_agregar_coag_con_hemo_no_duplica_plaq_suelto(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-COAG2", nombre="Prueba", apellido="Coag2"
    )
    actor = User.objects.create_user(username="prueba-coag2", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    coag = PanelExamen.objects.get(codigo="PAN_COAG")
    hemo = PanelExamen.objects.get(codigo="PAN_HEMO")
    agregar_examenes_a_solicitud(
        sol, paneles_ids=[coag.pk, hemo.pk], user=actor
    )
    sol.refresh_from_db()
    assert sol.paneles.filter(codigo="PAN_HEMO").exists()
    # PLAQ viene del hemograma; no hace falta acompañamiento aparte.
    assert sol.resultados.filter(tipo_examen__codigo="PLAQ").exists()


@pytest.mark.django_db
def test_asegurar_agrega_plaq_a_orden_coag_abierta(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-COAG3", nombre="Prueba", apellido="Coag3"
    )
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    coag = PanelExamen.objects.get(codigo="PAN_COAG")
    sol.paneles.add(coag)
    for te in coag.tipos_examen.all():
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=te)
        sol.tipos_examen.add(te)
    assert not sol.resultados.filter(tipo_examen__codigo="PLAQ").exists()
    assert asegurar_resultados_paneles_derivados(sol) >= 1
    assert sol.resultados.filter(tipo_examen__codigo="PLAQ").exists()


@pytest.mark.django_db
def test_agregar_eab_suelto_trae_hto(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-EAB1", nombre="Prueba", apellido="Eab"
    )
    actor = User.objects.create_user(username="prueba-eab1", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    eab = PanelExamen.objects.get(codigo="PAN_EAB_ART")
    agregar_examenes_a_solicitud(sol, paneles_ids=[eab.pk], user=actor)
    sol.refresh_from_db()
    codigos = set(sol.resultados.values_list("tipo_examen__codigo", flat=True))
    assert "HTO" in codigos
    assert sol.paneles.filter(codigo="PAN_EAB_ART").exists()
    assert not sol.paneles.filter(codigo="PAN_HEMO").exists()


@pytest.mark.django_db
def test_agregar_eab_con_hemo_no_pide_hto_suelto_extra(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-EAB2", nombre="Prueba", apellido="Eab2"
    )
    actor = User.objects.create_user(username="prueba-eab2", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    eab = PanelExamen.objects.get(codigo="PAN_EAB_VEN")
    hemo = PanelExamen.objects.get(codigo="PAN_HEMO")
    agregar_examenes_a_solicitud(
        sol, paneles_ids=[eab.pk, hemo.pk], user=actor
    )
    sol.refresh_from_db()
    assert sol.paneles.filter(codigo="PAN_HEMO").exists()
    # HTO viene del hemograma; no hace falta acompañamiento aparte.
    assert sol.resultados.filter(tipo_examen__codigo="HTO").exists()


@pytest.mark.django_db
def test_asegurar_agrega_hto_a_orden_eab_abierta(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-EAB3", nombre="Prueba", apellido="Eab3"
    )
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    eab = PanelExamen.objects.get(codigo="PAN_EAB_ART")
    sol.paneles.add(eab)
    for te in eab.tipos_examen.all():
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=te)
        sol.tipos_examen.add(te)
    assert not sol.resultados.filter(tipo_examen__codigo="HTO").exists()
    assert asegurar_resultados_paneles_derivados(sol) >= 1
    assert sol.resultados.filter(tipo_examen__codigo="HTO").exists()
