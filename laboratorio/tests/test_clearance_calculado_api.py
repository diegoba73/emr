"""Clearance de creatinina: carga medidos → CLEAR_CREA calculado."""
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
def clearance(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-CLEAR", nombre="Prueba", apellido="Clearance"
    )
    actor = User.objects.create_user(username="prueba-clear", rol="bioquimico")
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    sol.paneles.add(PanelExamen.objects.get(codigo="PAN_CLEAR"))
    rows = {
        codigo: ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo=codigo)
        )
        for codigo in ("CREATI", "CREA_U", "DIUR", "CLEAR_CREA")
    }
    return sol, actor, client, rows


def cargar(clearance, valores):
    sol, _actor, client, rows = clearance
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
def test_clear_crea_es_calculado_en_catalogo(clearance):
    clear = TipoExamen.objects.get(codigo="CLEAR_CREA")
    assert clear.modo_entrada == "CALCULADO"


@pytest.mark.django_db
def test_cargar_medidos_calcula_clearance(clearance):
    sol, _actor, _client, rows = clearance
    cargar(clearance, {"CREATI": "1.0", "CREA_U": "100", "DIUR": "1500"})
    rows["CLEAR_CREA"].refresh_from_db()
    assert rows["CLEAR_CREA"].valor_numerico == Decimal("104.2")
    assert rows["CLEAR_CREA"].valor_obtenido == "104.2"


@pytest.mark.django_db
def test_cargar_incompleto_marca_no_calculable(clearance):
    sol, _actor, _client, rows = clearance
    cargar(clearance, {"CREATI": "1.0", "CREA_U": "100"})
    rows["CLEAR_CREA"].refresh_from_db()
    assert rows["CLEAR_CREA"].valor_numerico is None
    assert rows["CLEAR_CREA"].valor_obtenido == RESULTADO_NO_CALCULABLE


@pytest.mark.django_db
def test_creatininemia_cero_no_calculable(clearance):
    sol, _actor, _client, rows = clearance
    cargar(clearance, {"CREATI": "0", "CREA_U": "100", "DIUR": "1500"})
    rows["CLEAR_CREA"].refresh_from_db()
    assert rows["CLEAR_CREA"].valor_numerico is None
    assert rows["CLEAR_CREA"].valor_obtenido == RESULTADO_NO_CALCULABLE
