"""API móvil: consultas pasadas y estudios complementarios."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.test import APIClient

from estudios.models import (
    EstudioComplementario,
    InformeEstudioComplementario,
    TipoEstudioComplementario,
)
from medicos.models import Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Recurso

pytestmark = pytest.mark.django_db


@pytest.fixture
def movil_ctx():
    cache.clear()
    U = get_user_model()
    u = U.objects.create_user(username='ce_pac', password='test-password', rol='paciente')
    p = Paciente.objects.create(user=u, nombre='Pac', apellido='Consulta', dni='CE-PAC-1')
    d = U.objects.create_user(username='ce_doc', password='test-password', rol='medico')
    m = Medico.objects.create(user=d, nombre='Doc', apellido='Consulta', matricula='CE-DOC-1')
    c = APIClient()
    r = c.post(
        '/api/movil/login/',
        {'username': u.username, 'password': 'test-password'},
        format='json',
    )
    assert r.status_code == 200, r.data
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['token'])
    return {'c': c, 'u': u, 'p': p, 'd': d, 'm': m, 'token': r.data['token']}


def _login_medico(ctx):
    c = APIClient()
    r = c.post(
        '/api/movil/login/',
        {'username': ctx['d'].username, 'password': 'test-password'},
        format='json',
    )
    assert r.status_code == 200, r.data
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['token'])
    return c


def test_consultas_paciente_solo_finalizadas_sin_notas(movil_ctx):
    p, m = movil_ctx['p'], movil_ctx['m']
    abierta = Atencion.objects.create(
        paciente=p,
        medico_principal=m,
        tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
        tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
        estado_clinico=Atencion.EstadoClinico.ABIERTA,
        observaciones_generales='NOTA SECRETA NO DEBE SALIR',
    )
    # Cerrar vía update para no pelear con exclusividad al crear otra ABIERTA.
    Atencion.objects.filter(pk=abierta.pk).update(
        estado_clinico=Atencion.EstadoClinico.FINALIZADA,
        fecha_cierre=timezone.now() - timedelta(days=1),
    )
    abierta_otra = Atencion.objects.create(
        paciente=p,
        medico_principal=m,
        tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
        tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
        estado_clinico=Atencion.EstadoClinico.ABIERTA,
        observaciones_generales='NOTA ABIERTA',
    )
    r = movil_ctx['c'].get('/api/movil/consultas/')
    assert r.status_code == 200, r.data
    ids = [row['id'] for row in r.data['results']]
    assert abierta.pk in ids
    assert abierta_otra.pk not in ids
    assert all('observaciones' not in row for row in r.data['results'])
    assert all('NOTA SECRETA' not in str(row) for row in r.data['results'])
    row = next(x for x in r.data['results'] if x['id'] == abierta.pk)
    assert row['medico_nombre']
    assert row['tipo_intervencion'] == 'CONSULTA'


def test_consultas_medico_403(movil_ctx):
    c = _login_medico(movil_ctx)
    assert c.get('/api/movil/consultas/').status_code == 403


def test_estudios_paciente_solo_entregado(movil_ctx):
    p, m = movil_ctx['p'], movil_ctx['m']
    tipo = TipoEstudioComplementario.objects.create(
        nombre='RX Torax CE',
        practica=TipoEstudioComplementario.Modalidad.IMAGEN_RX,
    )
    EstudioComplementario.objects.create(
        paciente=p,
        tipo_estudio=tipo,
        practica=tipo.practica,
        estado=EstudioComplementario.Estado.VALIDADO,
        medico_solicitante=m,
        fecha_solicitud=timezone.now(),
    )
    entregado = EstudioComplementario.objects.create(
        paciente=p,
        tipo_estudio=tipo,
        practica=tipo.practica,
        estado=EstudioComplementario.Estado.ENTREGADO,
        medico_solicitante=m,
        fecha_solicitud=timezone.now(),
    )
    r = movil_ctx['c'].get('/api/movil/estudios/')
    assert r.status_code == 200, r.data
    ids = [row['id'] for row in r.data['results']]
    assert entregado.pk in ids
    assert len(ids) == 1


def test_estudios_medico_ve_validado_y_entregado(movil_ctx):
    p, m = movil_ctx['p'], movil_ctx['m']
    tipo = TipoEstudioComplementario.objects.create(
        nombre='Eco CE',
        practica=TipoEstudioComplementario.Modalidad.IMAGEN_RX,
    )
    EstudioComplementario.objects.create(
        paciente=p,
        tipo_estudio=tipo,
        practica=tipo.practica,
        estado=EstudioComplementario.Estado.VALIDADO,
        medico_solicitante=m,
        fecha_solicitud=timezone.now(),
    )
    EstudioComplementario.objects.create(
        paciente=p,
        tipo_estudio=tipo,
        practica=tipo.practica,
        estado=EstudioComplementario.Estado.SOLICITADO,
        medico_solicitante=m,
        fecha_solicitud=timezone.now(),
    )
    c = _login_medico(movil_ctx)
    r = c.get('/api/movil/estudios/')
    assert r.status_code == 200, r.data
    estados = {row['estado'] for row in r.data['results']}
    assert 'VALIDADO' in estados
    assert 'SOLICITADO' not in estados


def test_estudio_pdf_paciente_entregado(movil_ctx, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    p, m = movil_ctx['p'], movil_ctx['m']
    tipo = TipoEstudioComplementario.objects.create(
        nombre='PDF CE',
        practica=TipoEstudioComplementario.Modalidad.IMAGEN_RX,
    )
    estudio = EstudioComplementario.objects.create(
        paciente=p,
        tipo_estudio=tipo,
        practica=tipo.practica,
        estado=EstudioComplementario.Estado.ENTREGADO,
        medico_solicitante=m,
        fecha_solicitud=timezone.now(),
    )
    informe = InformeEstudioComplementario.objects.create(
        estudio=estudio,
        estado=InformeEstudioComplementario.EstadoInforme.VALIDADO,
        es_vigente=True,
        version=1,
    )
    informe.archivo_pdf.save('inf.pdf', ContentFile(b'%PDF-1.4 mobile-test'), save=True)
    r = movil_ctx['c'].get(f'/api/movil/estudios/{estudio.pk}/informes/{informe.pk}/pdf/')
    assert r.status_code == 200, getattr(r, 'data', r.content)
    assert r['Content-Type'].startswith('application/pdf')
