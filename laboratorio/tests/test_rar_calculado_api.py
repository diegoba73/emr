"""RAR: carga ALDOS + ARPLA → relación aldosterona/actividad de renina calculada."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from laboratorio.calculos_derivados import RESULTADO_NO_CALCULABLE
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from pacientes.models import Paciente
from usuarios.models import User


def _ensure_rar_catalog():
    suero, _ = TipoMuestra.objects.get_or_create(
        codigo="SUERO", defaults={"nombre": "Suero", "activo": True}
    )
    plasma, _ = TipoMuestra.objects.get_or_create(
        codigo="PLASMA_EDTA", defaults={"nombre": "Plasma EDTA", "activo": True}
    )
    combo, _ = TipoMuestra.objects.get_or_create(
        codigo="SUERO_Y_PLASMA_EDTA",
        defaults={"nombre": "Suero y plasma EDTA", "activo": True},
    )
    TipoExamen.objects.update_or_create(
        codigo="ALDOS",
        defaults={
            "nombre": "Aldosterona",
            "tipo_muestra_requerida": suero,
            "tipo_resultado": "NUMERICO",
            "modo_entrada": "ESTANDAR",
            "activo": True,
            "requiere_muestra": False,
        },
    )
    TipoExamen.objects.update_or_create(
        codigo="ARPLA",
        defaults={
            "nombre": "Actividad de Renina",
            "tipo_muestra_requerida": plasma,
            "tipo_resultado": "NUMERICO",
            "modo_entrada": "ESTANDAR",
            "activo": True,
            "requiere_muestra": False,
        },
    )
    TipoExamen.objects.update_or_create(
        codigo="RAR",
        defaults={
            "nombre": "Relacion Aldosterona-Actividad de Renina",
            "tipo_muestra_requerida": combo,
            "tipo_resultado": "NUMERICO",
            "modo_entrada": "CALCULADO",
            "ticket_decimales": 1,
            "activo": True,
            "requiere_muestra": False,
        },
    )


@pytest.fixture
def rar_orden(db):
    _ensure_rar_catalog()
    paciente = Paciente.objects.create(
        dni="PRUEBA-RAR", nombre="Prueba", apellido="RAR"
    )
    actor = User.objects.create_user(username="prueba-rar", rol="bioquimico")
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    rows = {
        codigo: ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo=codigo)
        )
        for codigo in ("ALDOS", "ARPLA", "RAR")
    }
    sol.tipos_examen.add(*[r.tipo_examen for r in rows.values()])
    return sol, actor, client, rows


def cargar(rar_orden, valores):
    sol, _actor, client, rows = rar_orden
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
def test_rar_es_calculado_en_catalogo(rar_orden):
    rar = TipoExamen.objects.get(codigo="RAR")
    assert rar.modo_entrada == "CALCULADO"
    assert rar.requiere_muestra is False


@pytest.mark.django_db
def test_cargar_medidos_calcula_rar(rar_orden):
    _sol, _actor, _client, rows = rar_orden
    cargar(rar_orden, {"ALDOS": "20", "ARPLA": "1"})
    rows["RAR"].refresh_from_db()
    assert rows["RAR"].valor_numerico == Decimal("20.0")
    assert rows["RAR"].valor_obtenido == "20"


@pytest.mark.django_db
def test_cargar_incompleto_marca_no_calculable(rar_orden):
    _sol, _actor, _client, rows = rar_orden
    cargar(rar_orden, {"ALDOS": "20"})
    rows["RAR"].refresh_from_db()
    assert rows["RAR"].valor_numerico is None
    assert rows["RAR"].valor_obtenido == RESULTADO_NO_CALCULABLE


@pytest.mark.django_db
def test_arpla_cero_no_calculable(rar_orden):
    _sol, _actor, _client, rows = rar_orden
    cargar(rar_orden, {"ALDOS": "20", "ARPLA": "0"})
    rows["RAR"].refresh_from_db()
    assert rows["RAR"].valor_numerico is None
    assert rows["RAR"].valor_obtenido == RESULTADO_NO_CALCULABLE


@pytest.mark.django_db
def test_agregar_rar_suelto_trae_insumos(db):
    from laboratorio.solicitud_orden_abierta import agregar_examenes_a_solicitud

    _ensure_rar_catalog()
    paciente = Paciente.objects.create(
        dni="PRUEBA-RAR2", nombre="Prueba", apellido="RAR2"
    )
    actor = User.objects.create_user(username="prueba-rar2", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    rar = TipoExamen.objects.get(codigo="RAR")
    agregar_examenes_a_solicitud(sol, examenes_ids=[rar.pk], user=actor)
    sol.refresh_from_db()
    codigos = set(sol.resultados.values_list("tipo_examen__codigo", flat=True))
    assert {"RAR", "ALDOS", "ARPLA"} <= codigos
