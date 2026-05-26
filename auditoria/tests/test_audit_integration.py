import json
from datetime import timedelta

import pytest
from auditoria.tests.compat import capture_on_commit_callbacks
from django.utils import timezone
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from auditoria.snapshot import safe_model_snapshot
from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.muestra_estado import aplicar_recibir, aplicar_tomar, crear_muestra
from medicos.models import Medico
from pacientes.models import Paciente
from solicitudes.models import Solicitud as SolicitudEMR
from turnos.models import Recurso, Turno
from usuarios.models import User


@pytest.mark.django_db
def test_turno_create_and_update_generates_audit_events():
    client = APIClient()
    admin = User.objects.create_user(username="admin1", password="x", rol="admin", is_staff=True)
    client.force_authenticate(user=admin)

    pac = Paciente.objects.create(dni="100", nombre="Juan", apellido="Perez")
    med = Medico.objects.create(matricula="M-1", nombre="Ana", apellido="Doc")
    rec = Recurso.objects.create(nombre="Consultorio 1", ubicacion="CEHTA", tipo_recurso="CONSULTORIO", activo=True)

    payload = {
        "paciente_id": pac.id,
        "medico_id": med.id,
        "recurso_id": rec.id,
        "fecha_hora_inicio": timezone.now().isoformat(),
        "fecha_hora_fin": (timezone.now() + timedelta(minutes=30)).isoformat(),
        "estado": "RESERVADO",
        "motivo_reserva": "Control",
    }

    with capture_on_commit_callbacks(execute=True):
        r = client.post("/api/turnos/", payload, format="json")
    assert r.status_code in (200, 201)
    turno_id = r.data["id"]

    # audit CREATE
    ev = AuditEvent.objects.filter(entity_type="turnos.Turno", entity_id=str(turno_id), action="CREATE").first()
    assert ev is not None
    assert ev.actor_id == admin.id
    assert ev.request_id

    # confirmar vía acción (C5.9.2: PATCH estado bloqueado)
    with capture_on_commit_callbacks(execute=True):
        r2 = client.post(f"/api/turnos/{turno_id}/confirmar/", {}, format="json")
    assert r2.status_code == 200
    ev2 = AuditEvent.objects.filter(entity_type="turnos.Turno", entity_id=str(turno_id), action="UPDATE").order_by("-id").first()
    assert ev2 is not None
    assert ev2.before_state is not None
    assert ev2.after_state is not None
    assert ev2.metadata.get("accion") == "confirmar_turno"


@pytest.mark.django_db
def test_atencion_create_and_close_generates_audit_events():
    client = APIClient()
    admin = User.objects.create_user(username="admin2", password="x", rol="admin", is_staff=True)
    client.force_authenticate(user=admin)

    pac = Paciente.objects.create(dni="101", nombre="Maria", apellido="Lopez")
    med = Medico.objects.create(matricula="M-2", nombre="Luis", apellido="Doc")
    rec = Recurso.objects.create(nombre="Consultorio 2", ubicacion="CEHTA", tipo_recurso="CONSULTORIO", activo=True)
    turno = Turno.objects.create(
        paciente=pac,
        medico=med,
        recurso=rec,
        fecha_hora_inicio=timezone.now(),
        fecha_hora_fin=timezone.now() + timedelta(minutes=30),
        estado="CONFIRMADO",
    )

    with capture_on_commit_callbacks(execute=True):
        r = client.post("/api/atenciones/", {"turno": turno.id, "observaciones_generales": "ok"}, format="json")
    assert r.status_code in (200, 201)
    at_id = r.data["id"]

    ev = AuditEvent.objects.filter(entity_type="turnos.Atencion", entity_id=str(at_id), action="CREATE").first()
    assert ev is not None

    with capture_on_commit_callbacks(execute=True):
        r2 = client.post(f"/api/atenciones/{at_id}/cerrar/")
    assert r2.status_code == 200
    ev2 = AuditEvent.objects.filter(entity_type="turnos.Atencion", entity_id=str(at_id), action="UPDATE").order_by("-id").first()
    assert ev2 is not None


@pytest.mark.django_db
def test_solicitud_create_and_state_change_generates_audit_events():
    client = APIClient()
    admin = User.objects.create_user(username="admin3", password="x", rol="admin", is_staff=True)
    client.force_authenticate(user=admin)

    pac = Paciente.objects.create(dni="102", nombre="P", apellido="A")
    sol_payload = {
        "paciente": pac.id,
        "tipo_solicitud": "EXAMEN_LABORATORIO",
        "descripcion": "Hemograma",
        "observaciones": "",
        "estado": "PENDIENTE",
        "prioridad": "NORMAL",
    }

    with capture_on_commit_callbacks(execute=True):
        r = client.post("/api/solicitudes/", sol_payload, format="json")
    assert r.status_code in (200, 201)
    # SolicitudCreateSerializer no incluye ``id`` en la respuesta de creación.
    sol_id = r.data.get("id")
    if sol_id is None:
        sol = SolicitudEMR.objects.filter(paciente_id=pac.id).order_by("-id").first()
        assert sol is not None, r.data
        sol_id = sol.id

    ev = AuditEvent.objects.filter(entity_type="solicitudes.Solicitud", entity_id=str(sol_id), action="CREATE").first()
    assert ev is not None

    with capture_on_commit_callbacks(execute=True):
        r2 = client.patch(f"/api/solicitudes/{sol_id}/cambiar_estado/", {"estado": "EN_PROCESO"}, format="json")
    assert r2.status_code == 200
    ev2 = AuditEvent.objects.filter(entity_type="solicitudes.Solicitud", entity_id=str(sol_id), action="UPDATE").order_by("-id").first()
    assert ev2 is not None


@pytest.mark.django_db
def test_resultado_examen_snapshot_redacta_valor_clinico():
    pac = Paciente.objects.create(dni="B2A001", nombre="T", apellido="P")
    tm = TipoMuestra.objects.create(codigo="TM_B2A", nombre="Sangre", activo=True)
    te = TipoExamen.objects.create(
        codigo="GLU_B2A",
        nombre="Glucosa",
        tipo_muestra_requerida=tm,
        precio=1,
        activo=True,
    )
    med = Medico.objects.create(matricula="MB2A", nombre="Dr", apellido="X")
    sol = SolicitudExamen.objects.create(
        paciente=pac,
        medico_interno=med,
        origen_solicitud="EMR",
        estado="EN_PROCESO",
    )
    sol.tipos_examen.add(te)
    m = crear_muestra(
        solicitud=sol,
        tipo_muestra_id=tm.pk,
        tipo_contenedor_id=None,
        observaciones="",
        actor=None,
        view="test",
        codigo_barra="MUE-SENSIBLE-B2A-001",
    )
    aplicar_tomar(m.pk, actor=None, view="t")
    aplicar_recibir(m.pk, actor=None, view="t")

    res = ResultadoExamen.objects.create(
        solicitud=sol,
        tipo_examen=te,
        valor_obtenido="VALOR-SENSIBLE-123",
        valor_numerico="13.5",
        unidad="mg/dL",
        rango_referencia_snapshot="70-100",
        observaciones="Comentario clínico libre",
        muestra=m,
        es_patologico=True,
    )

    snap = safe_model_snapshot(res)
    raw = json.dumps(snap, ensure_ascii=False, default=str)

    assert "VALOR-SENSIBLE-123" not in raw
    assert "Comentario clínico libre" not in raw
    assert "MUE-SENSIBLE-B2A-001" not in raw
    assert snap.get("valor_obtenido") == "<valor clínico redactado>"
    assert snap.get("valor_numerico") == "<valor clínico redactado>"
    assert snap.get("observaciones") == "<valor clínico redactado>"
    assert snap.get("solicitud_id") == sol.pk
    assert snap.get("muestra_id") == m.pk
    assert snap.get("tipo_examen_id") == te.pk
    assert snap.get("es_patologico") is True


@pytest.mark.django_db
def test_audit_events_endpoint_is_readonly_and_protected():
    client = APIClient()

    # unauthenticated -> 403/401
    r = client.get("/api/auditoria/events/")
    assert r.status_code in (401, 403)

    admin = User.objects.create_user(username="admin4", password="x", rol="admin", is_staff=True)
    client.force_authenticate(user=admin)

    r2 = client.get("/api/auditoria/events/")
    assert r2.status_code == 200

    # Write methods not allowed
    r3 = client.post("/api/auditoria/events/", {"action": "X"}, format="json")
    assert r3.status_code in (405, 403)

