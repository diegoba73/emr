"""TFG CKD-EPI 2021: carga CREATI + demografía paciente → TFG calculado."""
from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from laboratorio.calculos_derivados import RESULTADO_NO_CALCULABLE
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen
from pacientes.models import Paciente
from usuarios.models import User


@pytest.fixture
def tfg_orden(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-TFG",
        nombre="Prueba",
        apellido="TFG",
        sexo="F",
        fecha_nacimiento=date(1976, 1, 1),  # ~50 años en 2026
    )
    actor = User.objects.create_user(username="prueba-tfg", rol="bioquimico")
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    TipoExamen.objects.filter(codigo="CREATI").update(requiere_muestra=False)
    rows = {
        codigo: ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo=codigo)
        )
        for codigo in ("CREATI", "TFG")
    }
    return sol, actor, client, rows


def cargar(tfg_orden, valores):
    sol, _actor, client, rows = tfg_orden
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
def test_tfg_es_calculado_en_catalogo(tfg_orden):
    tfg = TipoExamen.objects.get(codigo="TFG")
    assert tfg.modo_entrada == "CALCULADO"
    assert tfg.requiere_muestra is False


@pytest.mark.django_db
def test_cargar_creati_calcula_tfg(tfg_orden):
    _sol, _actor, _client, rows = tfg_orden
    cargar(tfg_orden, {"CREATI": "1.0"})
    rows["TFG"].refresh_from_db()
    assert rows["TFG"].valor_numerico == Decimal("69")
    assert rows["TFG"].valor_obtenido == "69"


@pytest.mark.django_db
def test_tfg_sin_sexo_no_calculable(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-TFG2",
        nombre="Sin",
        apellido="Sexo",
        fecha_nacimiento=date(1980, 1, 1),
        sexo="",
    )
    actor = User.objects.create_user(username="prueba-tfg2", rol="bioquimico")
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    TipoExamen.objects.filter(codigo="CREATI").update(requiere_muestra=False)
    creati = ResultadoExamen.objects.create(
        solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo="CREATI")
    )
    tfg = ResultadoExamen.objects.create(
        solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo="TFG")
    )
    response = client.post(
        f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
        {
            "resultados": [
                {"id": creati.pk, "valor": "1.0", "valor_numerico": "1.0"},
            ]
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    tfg.refresh_from_db()
    assert tfg.valor_numerico is None
    assert tfg.valor_obtenido == RESULTADO_NO_CALCULABLE


@pytest.mark.django_db
def test_agregar_tfg_suelto_trae_creati(db):
    from laboratorio.solicitud_orden_abierta import agregar_examenes_a_solicitud

    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-TFG3", nombre="Prueba", apellido="TFG3", sexo="M",
        fecha_nacimiento=date(1985, 5, 5),
    )
    actor = User.objects.create_user(username="prueba-tfg3", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    tfg = TipoExamen.objects.get(codigo="TFG")
    agregar_examenes_a_solicitud(sol, examenes_ids=[tfg.pk], user=actor)
    codigos = set(sol.resultados.values_list("tipo_examen__codigo", flat=True))
    assert {"TFG", "CREATI"} <= codigos
