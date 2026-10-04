"""Default NO CONTIENE en tira/sedimento al crear orden con PAN_ORI."""
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from laboratorio.examen_orina_micro import (
    CODIGOS_DEFAULT_NO_CONTIENE,
    VALOR_NO_CONTIENE,
    examen_orina_vacio,
)
from laboratorio.models import PanelExamen, SolicitudExamen
from pacientes.models import Paciente
from usuarios.models import User


@pytest.mark.django_db
def test_examen_orina_vacio_prellena_no_contiene():
    vacio = examen_orina_vacio()
    for codigo in CODIGOS_DEFAULT_NO_CONTIENE:
        assert vacio[codigo] == VALOR_NO_CONTIENE
    assert vacio["ORI_COLOR"] == ""
    assert vacio["ORI_PH"] == ""
    assert vacio["ORI_CONC"] == ""


@pytest.mark.django_db
def test_crear_orden_pan_ori_prellena_no_contiene():
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-NOCONT", nombre="Prueba", apellido="NoContiene"
    )
    actor = User.objects.create_user(username="prueba-nocont", rol="laboratorio")
    client = APIClient()
    client.force_authenticate(actor)
    pan = PanelExamen.objects.get(codigo="PAN_ORI")
    response = client.post(
        "/api/lab/solicitudes/",
        {
            "paciente_id": paciente.pk,
            "origen_solicitud": "AMBULATORIO_CEHTA",
            "paneles_ids": [pan.pk],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    sol = SolicitudExamen.objects.get(pk=response.data["id"])
    by_codigo = {
        r.tipo_examen.codigo: r.valor_obtenido for r in sol.resultados.select_related("tipo_examen")
    }
    for codigo in CODIGOS_DEFAULT_NO_CONTIENE:
        assert by_codigo[codigo] == VALOR_NO_CONTIENE, codigo
    assert by_codigo["ORI_COLOR"] == ""
    assert by_codigo["ORI_ASP"] == ""
    assert by_codigo["ORI_DENS"] == ""
    assert by_codigo["ORI_PH"] == ""
    assert by_codigo["ORI_CONC"] == ""
