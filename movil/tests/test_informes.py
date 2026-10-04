"""Tests de listado/PDF de informes en API móvil."""

from datetime import timedelta
import base64
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra, ResultadoExamen
from pacientes.models import Paciente

pytestmark = pytest.mark.django_db
User = get_user_model()


def _login(rol, username='u'):
    cache.clear()
    user = User.objects.create_user(username=username, password='test-password', rol=rol)
    c = APIClient()
    r = c.post('/api/movil/login/', {'username': username, 'password': 'test-password'}, format='json')
    assert r.status_code == 200, r.data
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['token'])
    return c, user


def _orden(paciente, estado='FINALIZADO'):
    suf = uuid.uuid4().hex[:8]
    tm = TipoMuestra.objects.create(codigo=f'SUERO-{suf}', nombre='Suero', activo=True)
    te = TipoExamen.objects.create(codigo=f'GLU-{suf}', nombre='Glucemia', tipo_muestra_requerida=tm, activo=True)
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado='EN_PROCESO',
        fecha_solicitud=timezone.now() - timedelta(hours=2),
    )
    sol.tipos_examen.add(te)
    ResultadoExamen.objects.create(
        solicitud=sol,
        tipo_examen=te,
        valor_obtenido='90',
        valor_numerico=90,
        unidad='mg/dL',
    )
    if estado != 'EN_PROCESO':
        sol.estado = estado
        sol.save(update_fields=['estado'])
    return sol


def test_paciente_ve_solo_sus_informes_finalizados_o_parciales():
    c, user = _login('paciente', 'pac-inf')
    p = Paciente.objects.create(user=user, nombre='Ana', apellido='Propia', dni='INF-1')
    otro = Paciente.objects.create(nombre='Otro', apellido='Ajeno', dni='INF-2')
    propia = _orden(p, 'FINALIZADO')
    parcial = _orden(p, 'INFORMADO_PARCIAL')
    _orden(otro, 'FINALIZADO')
    r = c.get('/api/movil/informes/')
    assert r.status_code == 200, r.data
    ids = {row['id'] for row in r.data['results']}
    assert ids == {propia.id, parcial.id}
    assert all(row['paciente_nombre'].upper().startswith('PROPIA') for row in r.data['results'])


def test_secretaria_lista_parcial_pero_no_descarga_pdf():
    c, _ = _login('secretaria', 'sec-inf')
    p = Paciente.objects.create(nombre='Pac', apellido='Sec', dni='INF-3')
    sol = _orden(p, 'INFORMADO_PARCIAL')
    listed = c.get('/api/movil/informes/')
    assert listed.status_code == 200
    assert sol.id in {row['id'] for row in listed.data['results']}
    row = next(r for r in listed.data['results'] if r['id'] == sol.id)
    assert row.get('es_parcial') is True
    assert row.get('puede_descargar_pdf') is False
    pdf = c.get(f'/api/movil/informes/{sol.id}/pdf/?as_base64=1')
    assert pdf.status_code == 403


def test_paciente_descarga_pdf_propio_y_no_ajeno():
    c, user = _login('paciente', 'pac-pdf')
    p = Paciente.objects.create(user=user, nombre='Ana', apellido='Propia', dni='INF-PDF-1')
    otro = Paciente.objects.create(nombre='Otro', apellido='Ajeno', dni='INF-PDF-2')
    propia = _orden(p, 'FINALIZADO')
    ajena = _orden(otro, 'FINALIZADO')

    det = c.get(f'/api/movil/informes/{propia.id}/')
    assert det.status_code == 200, det.data
    assert det.data['informe']['puede_descargar_pdf'] is True

    pdf = c.get(f'/api/movil/informes/{propia.id}/pdf/?as_base64=1')
    assert pdf.status_code == 200, pdf.data
    assert pdf.data['es_parcial'] is False
    assert isinstance(pdf.data.get('filename'), str) and pdf.data['filename'].endswith('.pdf')
    raw = base64.b64decode(pdf.data['base64'])
    assert raw.startswith(b'%PDF')

    deny = c.get(f'/api/movil/informes/{ajena.id}/pdf/?as_base64=1')
    assert deny.status_code == 403


def test_bioquimico_puede_ver_listo_para_validar():
    c, _ = _login('bioquimico', 'bio-inf')
    p = Paciente.objects.create(nombre='Bio', apellido='Quim', dni='INF-4')
    sol = _orden(p, 'LISTO_PARA_VALIDAR')
    r = c.get('/api/movil/informes/')
    assert r.status_code == 200
    assert sol.id in {row['id'] for row in r.data['results']}
    det = c.get(f'/api/movil/informes/{sol.id}/')
    assert det.status_code == 200
    assert det.data['informe']['puede_validar'] is True
    assert 'orden' in det.data


def test_bioquimico_desvalidar_informe_finalizado():
    c, _ = _login('bioquimico', 'bio-des')
    p = Paciente.objects.create(nombre='Bio', apellido='Des', dni='INF-DES')
    sol = _orden(p, 'FINALIZADO')
    det = c.get(f'/api/movil/informes/{sol.id}/')
    assert det.status_code == 200
    assert det.data['informe']['puede_desvalidar'] is True
    bad = c.post(f'/api/movil/informes/{sol.id}/desvalidar/', {'motivo': 'x'}, format='json')
    assert bad.status_code == 400
    ok = c.post(
        f'/api/movil/informes/{sol.id}/desvalidar/',
        {'motivo': 'Corrección de valor'},
        format='json',
    )
    assert ok.status_code == 200, ok.data
    assert ok.data['estado'] == 'LISTO_PARA_VALIDAR'
    assert ok.data['puede_validar'] is True
    assert ok.data['puede_desvalidar'] is False
