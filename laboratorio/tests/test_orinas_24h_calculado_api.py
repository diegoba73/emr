"""Orinas 24 hs: carga concentración + DIUR → excreción calculada."""
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from laboratorio.calculos_derivados import RESULTADO_NO_CALCULABLE
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from pacientes.models import Paciente
from usuarios.models import User


@pytest.fixture
def orina24(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-ORI24", nombre="Prueba", apellido="Orina24"
    )
    actor = User.objects.create_user(username="prueba-ori24", rol="bioquimico")
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    for codigo in ("PAN_PROT24", "PAN_IONO_U24", "PAN_MALB24"):
        sol.paneles.add(PanelExamen.objects.get(codigo=codigo))
    codigos = (
        "PROT_U_EQ",
        "NA_U",
        "K_U",
        "CL_U",
        "MICROALB",
        "DIUR",
        "PROT_U_24",
        "NA_U24",
        "K_U24",
        "CL_U24",
        "MICROALB_24",
    )
    rows = {
        codigo: ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo=codigo)
        )
        for codigo in codigos
    }
    return sol, actor, client, rows


def cargar(orina24, valores):
    sol, _actor, client, rows = orina24
    payload = [
        {"id": rows[codigo].pk, "valor": str(valor), "valor_numerico": str(valor)}
        for codigo, valor in valores.items()
    ]
    response = client.post(
        f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
        {"resultados": payload},
        format="json",
    )
    assert response.status_code == 200, response.data
    return response


@pytest.mark.django_db
def test_codigos_24h_son_calculados_en_catalogo(orina24):
    for codigo in ("PROT_U_24", "NA_U24", "K_U24", "CL_U24", "MICROALB_24"):
        assert TipoExamen.objects.get(codigo=codigo).modo_entrada == "CALCULADO"


@pytest.mark.django_db
def test_cargar_medidos_calcula_excreciones_24h(orina24):
    _sol, _actor, _client, rows = orina24
    cargar(
        orina24,
        {
            "PROT_U_EQ": "80",
            "NA_U": "100",
            "K_U": "40",
            "CL_U": "90",
            "MICROALB": "20",
            "DIUR": "1500",
        },
    )
    rows["PROT_U_24"].refresh_from_db()
    rows["NA_U24"].refresh_from_db()
    rows["K_U24"].refresh_from_db()
    rows["CL_U24"].refresh_from_db()
    rows["MICROALB_24"].refresh_from_db()
    assert rows["PROT_U_24"].valor_numerico == Decimal("1200")
    assert rows["NA_U24"].valor_numerico == Decimal("150")
    assert rows["K_U24"].valor_numerico == Decimal("60")
    assert rows["CL_U24"].valor_numerico == Decimal("135")
    assert rows["MICROALB_24"].valor_numerico == Decimal("30.0")


@pytest.mark.django_db
def test_cargar_sin_diuresis_marca_no_calculable(orina24):
    _sol, _actor, _client, rows = orina24
    cargar(orina24, {"PROT_U_EQ": "80", "NA_U": "100", "MICROALB": "25"})
    rows["PROT_U_24"].refresh_from_db()
    rows["NA_U24"].refresh_from_db()
    rows["MICROALB_24"].refresh_from_db()
    assert rows["PROT_U_24"].valor_obtenido == RESULTADO_NO_CALCULABLE
    assert rows["NA_U24"].valor_obtenido == RESULTADO_NO_CALCULABLE
    assert rows["MICROALB_24"].valor_obtenido == RESULTADO_NO_CALCULABLE
