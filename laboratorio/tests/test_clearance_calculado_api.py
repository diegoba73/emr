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


@pytest.mark.django_db
def test_clear_crea_calculado_no_exige_muestra_aunque_flag_activo(clearance):
    """Regresión UI: CLEAR_CREA CALCULADO no debe bloquear carga por requiere_muestra."""
    sol, _actor, client, rows = clearance
    clear = TipoExamen.objects.get(codigo="CLEAR_CREA")
    clear.requiere_muestra = True
    clear.save(update_fields=["requiere_muestra"])
    response = client.post(
        f"/api/lab/solicitudes/{sol.pk}/cargar-resultados/",
        {
            "resultados": [
                {
                    "id": rows["CREATI"].pk,
                    "valor": "1.0",
                    "valor_numerico": "1.0",
                },
                {
                    "id": rows["CLEAR_CREA"].pk,
                    "valor": RESULTADO_NO_CALCULABLE,
                    "valor_numerico": None,
                },
            ]
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    rows["CLEAR_CREA"].refresh_from_db()
    assert rows["CLEAR_CREA"].valor_obtenido == RESULTADO_NO_CALCULABLE


@pytest.mark.django_db
def test_agregar_panel_clear_a_orden_con_suero_crea_bidon_pendiente(db):
    """
    Orden con solo suero/EDTA: agregar PAN_CLEAR no falla por CLEAR_CREA sin tubo;
    crea bidón PENDIENTE_TOMA (lab puede seguir).
    """
    from django.utils import timezone
    from rest_framework import status

    from laboratorio.models_catalog import Muestra
    from laboratorio.tubos_catalogo import BIDON_ORINA_24H

    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-CLEAR-ADD", nombre="Add", apellido="Clear"
    )
    actor = User.objects.create_user(
        username="lab-clear-add", password="pass12345", rol="laboratorio", is_staff=True
    )
    client = APIClient()
    client.force_authenticate(actor)

    creati = TipoExamen.objects.get(codigo="CREATI")
    r = client.post(
        "/api/lab/solicitudes/",
        {
            "paciente_id": paciente.id,
            "examenes_ids": [creati.id],
            "origen_solicitud": "AMBULATORIO_CEHTA",
            "fecha_programada_toma": timezone.localdate().isoformat(),
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert r.status_code == status.HTTP_201_CREATED, r.data
    sol_id = r.data["id"]
    r_tom = client.post(
        f"/api/lab/solicitudes/{sol_id}/tomar-muestra/",
        {},
        format="json",
        HTTP_HOST="localhost",
    )
    assert r_tom.status_code == status.HTTP_200_OK, r_tom.data
    n_antes = Muestra.objects.filter(solicitud_id=sol_id).count()

    panel = PanelExamen.objects.get(codigo="PAN_CLEAR")
    r_add = client.post(
        f"/api/lab/solicitudes/{sol_id}/agregar-examenes/",
        {"paneles_ids": [panel.id]},
        format="json",
        HTTP_HOST="localhost",
    )
    assert r_add.status_code == status.HTTP_200_OK, r_add.data
    codigos = set(
        ResultadoExamen.objects.filter(solicitud_id=sol_id).values_list(
            "tipo_examen__codigo", flat=True
        )
    )
    assert {"CREATI", "CREA_U", "DIUR", "CLEAR_CREA"} <= codigos
    assert Muestra.objects.filter(solicitud_id=sol_id).count() >= n_antes + 1
    assert Muestra.objects.filter(
        solicitud_id=sol_id,
        estado="PENDIENTE_TOMA",
        tipo_contenedor__codigo=BIDON_ORINA_24H,
    ).exists()


@pytest.mark.django_db
def test_agregar_clear_crea_suelto_trae_insumos(db):
    """Pedir solo CLEAR_CREA debe traer CREATI + CREA_U + DIUR."""
    from laboratorio.solicitud_orden_abierta import agregar_examenes_a_solicitud

    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-CLR2", nombre="Prueba", apellido="Clear2"
    )
    actor = User.objects.create_user(username="prueba-clr2", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    clear = TipoExamen.objects.get(codigo="CLEAR_CREA")
    agregar_examenes_a_solicitud(sol, examenes_ids=[clear.pk], user=actor)
    sol.refresh_from_db()
    codigos = set(sol.resultados.values_list("tipo_examen__codigo", flat=True))
    assert {"CLEAR_CREA", "CREATI", "CREA_U", "DIUR"} <= codigos

