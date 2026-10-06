"""RAC: carga MICROALB + CREA_U → relación albúmina/creatinina calculada."""
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
def rac_orden(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-RAC", nombre="Prueba", apellido="RAC"
    )
    actor = User.objects.create_user(username="prueba-rac", rol="bioquimico")
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    sol.paneles.add(PanelExamen.objects.get(codigo="PAN_MALB_AZ"))
    rows = {
        codigo: ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo=codigo)
        )
        for codigo in ("MICROALB", "CREA_U", "RAC")
    }
    return sol, actor, client, rows


def cargar(rac_orden, valores):
    sol, _actor, client, rows = rac_orden
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
def test_rac_es_calculado_en_catalogo(rac_orden):
    rac = TipoExamen.objects.get(codigo="RAC")
    assert rac.modo_entrada == "CALCULADO"
    assert rac.requiere_muestra is False


@pytest.mark.django_db
def test_cargar_medidos_calcula_rac(rac_orden):
    _sol, _actor, _client, rows = rac_orden
    # (30 mg/L ÷ 100 mg/dL) × 100 = 30 mg/g
    cargar(rac_orden, {"MICROALB": "30", "CREA_U": "100"})
    rows["RAC"].refresh_from_db()
    assert rows["RAC"].valor_numerico == Decimal("30.0")
    assert rows["RAC"].valor_obtenido == "30"


@pytest.mark.django_db
def test_cargar_incompleto_marca_no_calculable(rac_orden):
    _sol, _actor, _client, rows = rac_orden
    cargar(rac_orden, {"MICROALB": "30"})
    rows["RAC"].refresh_from_db()
    assert rows["RAC"].valor_numerico is None
    assert rows["RAC"].valor_obtenido == RESULTADO_NO_CALCULABLE


@pytest.mark.django_db
def test_crea_u_cero_no_calculable(rac_orden):
    _sol, _actor, _client, rows = rac_orden
    cargar(rac_orden, {"MICROALB": "30", "CREA_U": "0"})
    rows["RAC"].refresh_from_db()
    assert rows["RAC"].valor_numerico is None
    assert rows["RAC"].valor_obtenido == RESULTADO_NO_CALCULABLE


@pytest.mark.django_db
def test_panel_malb_az_incluye_rac(rac_orden):
    panel = PanelExamen.objects.get(codigo="PAN_MALB_AZ")
    codigos = set(panel.tipos_examen.values_list("codigo", flat=True))
    assert {"MICROALB", "CREA_U", "RAC"} <= codigos


@pytest.mark.django_db
def test_agregar_rac_suelto_trae_insumos(db):
    """Pedir solo RAC debe traer MICROALB + CREA_U para cargar del equipo."""
    from laboratorio.solicitud_orden_abierta import agregar_examenes_a_solicitud

    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-RAC2", nombre="Prueba", apellido="RAC2"
    )
    actor = User.objects.create_user(username="prueba-rac2", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    rac = TipoExamen.objects.get(codigo="RAC")
    agregar_examenes_a_solicitud(sol, examenes_ids=[rac.pk], user=actor)
    sol.refresh_from_db()
    codigos = set(sol.resultados.values_list("tipo_examen__codigo", flat=True))
    assert {"RAC", "MICROALB", "CREA_U"} <= codigos


@pytest.mark.django_db
def test_asegurar_rac_suelto_completa_insumos(db):
    from laboratorio.hemograma_resultados import asegurar_resultados_paneles_derivados

    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni="PRUEBA-RAC3", nombre="Prueba", apellido="RAC3"
    )
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    rac = TipoExamen.objects.get(codigo="RAC")
    ResultadoExamen.objects.create(solicitud=sol, tipo_examen=rac)
    sol.tipos_examen.add(rac)
    assert asegurar_resultados_paneles_derivados(sol) == 2
    codigos = set(sol.resultados.values_list("tipo_examen__codigo", flat=True))
    assert {"RAC", "MICROALB", "CREA_U"} <= codigos
