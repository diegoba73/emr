import pytest
from django.utils import timezone

from recepcion.models import LlegadaRecepcion, PuestoRecepcion, ReglaRuteoRecepcion
from recepcion.ruteo import ContextoRuteo, resolver_puesto


@pytest.fixture
def limpia_recepcion(db):
    ReglaRuteoRecepcion.objects.all().delete()
    LlegadaRecepcion.objects.all().delete()
    PuestoRecepcion.objects.all().delete()


@pytest.mark.django_db
def test_ruteo_consulta_a_puesto_1(limpia_recepcion):
    p1 = PuestoRecepcion.objects.create(
        codigo='t-p1', nombre='P1', modo='REGLAS', activo=True, es_fallback=True, orden=1
    )
    p2 = PuestoRecepcion.objects.create(
        codigo='t-p2', nombre='P2', modo='REGLAS', activo=True, orden=2
    )
    ReglaRuteoRecepcion.objects.create(
        puesto=p1, tipo_actividad='CONSULTA', prioridad=10, activo=True
    )
    ReglaRuteoRecepcion.objects.create(
        puesto=p2, tipo_actividad='ESTUDIO', prioridad=10, activo=True
    )
    r = resolver_puesto(ContextoRuteo(tipo_actividad='CONSULTA'))
    assert r.puesto.id == p1.id
    r2 = resolver_puesto(ContextoRuteo(tipo_actividad='ESTUDIO'))
    assert r2.puesto.id == p2.id


@pytest.mark.django_db
def test_balanceo_modo_todo(limpia_recepcion):
    p1 = PuestoRecepcion.objects.create(
        codigo='b1', nombre='B1', modo='TODO', activo=True, orden=1
    )
    p2 = PuestoRecepcion.objects.create(
        codigo='b2', nombre='B2', modo='TODO', activo=True, orden=2
    )
    from pacientes.models import Paciente

    pac = Paciente.objects.create(nombre='A', apellido='B', dni='99900011')
    hoy = timezone.localdate()
    LlegadaRecepcion.objects.create(
        paciente=pac,
        puesto=p1,
        tipo_actividad='CONSULTA',
        estado_flujo='EN_ESPERA_RECEPCION',
        fecha=hoy,
        checkin_en=timezone.now(),
    )
    r = resolver_puesto(ContextoRuteo(tipo_actividad='CONSULTA'))
    assert r.puesto.id == p2.id


@pytest.mark.django_db
def test_extraccion_prioriza_regla_sobre_modo_todo(limpia_recepcion):
    """Un puesto TODO (consultas) no debe absorber extracciones si hay regla L."""
    PuestoRecepcion.objects.create(
        codigo='consultas',
        nombre='Consultas',
        etiqueta_paciente='Puesto 1 — Consultas',
        modo='TODO',
        activo=True,
        es_fallback=True,
        orden=1,
    )
    sala = PuestoRecepcion.objects.create(
        codigo='sala-extraccion',
        nombre='Sala de extracción',
        etiqueta_paciente='Sala de extracción',
        modo='REGLAS',
        activo=True,
        orden=10,
    )
    ReglaRuteoRecepcion.objects.create(
        puesto=sala, tipo_actividad='EXTRACCION', prioridad=5, activo=True
    )
    r = resolver_puesto(ContextoRuteo(tipo_actividad='EXTRACCION'))
    assert r.puesto.id == sala.id
    assert 'extracción' in r.puesto.label_publico.lower()
