"""CREA_U: dilución 1:20 (CM260) solo en órdenes nuevas."""
from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from laboratorio.creatinuria_dilucion import (
    CREATINURIA_DILUCION_DESDE,
    FACTOR_DILUCION_CREATINURIA,
    aplica_dilucion_creatinuria,
)
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from pacientes.models import Paciente
from usuarios.models import User


@pytest.fixture
def seed_catalogo(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())


def _orden(*, fecha_solicitud, paneles_codigos, examenes, sufijo: str = "x"):
    paciente = Paciente.objects.create(
        dni=f"CU{sufijo}"[:20],
        nombre="Prueba",
        apellido="Creatinuria",
    )
    actor = User.objects.create_user(username=f"cu-{sufijo}"[:30], rol="bioquimico")
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    SolicitudExamen.objects.filter(pk=sol.pk).update(fecha_solicitud=fecha_solicitud)
    sol.refresh_from_db()
    for codigo in paneles_codigos:
        sol.paneles.add(PanelExamen.objects.get(codigo=codigo))
    medidos = [c for c in examenes if c not in ("RAC", "CLEAR_CREA")]
    if medidos:
        TipoExamen.objects.filter(codigo__in=medidos).update(requiere_muestra=False)
    rows = {
        codigo: ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo=codigo)
        )
        for codigo in examenes
    }
    return sol, actor, client, rows


def _cargar(client, sol, rows, valores):
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
def test_aplica_dilucion_por_fecha(seed_catalogo):
    assert aplica_dilucion_creatinuria(
        type("S", (), {"fecha_solicitud": CREATINURIA_DILUCION_DESDE})()
    )
    assert not aplica_dilucion_creatinuria(
        type(
            "S",
            (),
            {"fecha_solicitud": CREATINURIA_DILUCION_DESDE - timedelta(seconds=1)},
        )()
    )


@pytest.mark.django_db
def test_crea_u_nueva_multiplica_por_20(seed_catalogo):
    sol, _actor, client, rows = _orden(
        fecha_solicitud=CREATINURIA_DILUCION_DESDE + timedelta(minutes=1),
        paneles_codigos=("PAN_MALB_AZ",),
        examenes=("MICROALB", "CREA_U", "RAC"),
        sufijo="n1",
    )
    assert aplica_dilucion_creatinuria(sol)
    # CM260 = 5 → clínico 100; RAC = (30/100)×100 = 30
    _cargar(client, sol, rows, {"MICROALB": "30", "CREA_U": "5"})
    rows["CREA_U"].refresh_from_db()
    rows["RAC"].refresh_from_db()
    assert rows["CREA_U"].valor_numerico == Decimal("100.0000")
    assert rows["CREA_U"].valor_obtenido == "100"
    assert rows["RAC"].valor_numerico == Decimal("30.0")
    assert rows["RAC"].valor_obtenido == "30"


@pytest.mark.django_db
def test_crea_u_vieja_no_multiplica(seed_catalogo):
    sol, _actor, client, rows = _orden(
        fecha_solicitud=CREATINURIA_DILUCION_DESDE - timedelta(days=1),
        paneles_codigos=("PAN_MALB_AZ",),
        examenes=("MICROALB", "CREA_U", "RAC"),
        sufijo="v1",
    )
    _cargar(client, sol, rows, {"MICROALB": "30", "CREA_U": "100"})
    rows["CREA_U"].refresh_from_db()
    rows["RAC"].refresh_from_db()
    assert rows["CREA_U"].valor_numerico == Decimal("100.0000")
    assert rows["CREA_U"].valor_obtenido == "100"
    assert rows["RAC"].valor_numerico == Decimal("30.0")


@pytest.mark.django_db
def test_clearance_nueva_usa_crea_u_x20(seed_catalogo):
    sol, _actor, client, rows = _orden(
        fecha_solicitud=timezone.now(),
        paneles_codigos=("PAN_CLEAR",),
        examenes=("CREATI", "CREA_U", "DIUR", "CLEAR_CREA"),
        sufijo="cl1",
    )
    # CM260 5 → 100 clínico → clearance 104.2
    _cargar(client, sol, rows, {"CREATI": "1.0", "CREA_U": "5", "DIUR": "1500"})
    rows["CREA_U"].refresh_from_db()
    rows["CLEAR_CREA"].refresh_from_db()
    assert rows["CREA_U"].valor_numerico == Decimal("100.0000")
    assert rows["CLEAR_CREA"].valor_numerico == Decimal("104.2")
    assert FACTOR_DILUCION_CREATINURIA == Decimal("20")


@pytest.mark.django_db
def test_serializer_flag_dilucion(seed_catalogo):
    from laboratorio.serializers import SolicitudExamenSerializer

    sol_nueva, *_ = _orden(
        fecha_solicitud=CREATINURIA_DILUCION_DESDE + timedelta(hours=1),
        paneles_codigos=("PAN_MALB_AZ",),
        examenes=("CREA_U",),
        sufijo="sn",
    )
    sol_vieja, *_ = _orden(
        fecha_solicitud=CREATINURIA_DILUCION_DESDE - timedelta(days=2),
        paneles_codigos=("PAN_MALB_AZ",),
        examenes=("CREA_U",),
        sufijo="sv",
    )
    assert SolicitudExamenSerializer(sol_nueva).data["crea_u_dilucion_activa"] is True
    assert SolicitudExamenSerializer(sol_vieja).data["crea_u_dilucion_activa"] is False
