"""ENA: panel con un resultado por antígeno (reemplaza ENA único)."""
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.solicitud_orden_abierta import agregar_examenes_a_solicitud
from pacientes.models import Paciente
from usuarios.models import User


@pytest.fixture
def ena_seed(db):
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())


@pytest.mark.django_db
def test_agregar_ena_legacy_expande_panel(ena_seed):
    """Pedir el código legacy ENA trae los 5 antígenos del panel."""
    # Reactivar ENA solo para simular pedido por id legacy (sigue en BD).
    ena = TipoExamen.objects.get(codigo="ENA")
    ena.activo = True
    ena.save(update_fields=["activo"])

    paciente = Paciente.objects.create(dni="PRUEBA-ENA", nombre="Prueba", apellido="ENA")
    actor = User.objects.create_user(username="prueba-ena", rol="bioquimico")
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    agregar_examenes_a_solicitud(sol, examenes_ids=[ena.pk], user=actor)
    sol.refresh_from_db()
    codigos = set(sol.resultados.values_list("tipo_examen__codigo", flat=True))
    assert {"ENA_RO52", "ENA_RO60", "ENA_SSB", "ENA_RNP", "ENA_SM"} <= codigos
    assert "ENA" not in codigos
    assert sol.paneles.filter(codigo="PAN_ENA").exists()


@pytest.mark.django_db
def test_agregar_panel_ena_directo(ena_seed):
    paciente = Paciente.objects.create(dni="PRUEBA-ENA2", nombre="Prueba", apellido="ENA2")
    actor = User.objects.create_user(username="prueba-ena2", rol="bioquimico")
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="PENDIENTE",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    panel = PanelExamen.objects.get(codigo="PAN_ENA")
    r = client.post(
        f"/api/lab/solicitudes/{sol.pk}/agregar-examenes/",
        {"paneles_ids": [panel.id]},
        format="json",
    )
    assert r.status_code == 200, r.data
    codigos = set(
        ResultadoExamen.objects.filter(solicitud=sol).values_list("tipo_examen__codigo", flat=True)
    )
    assert codigos == {"ENA_RO52", "ENA_RO60", "ENA_SSB", "ENA_RNP", "ENA_SM"}
