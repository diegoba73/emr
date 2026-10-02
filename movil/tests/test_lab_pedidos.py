"""Tests de pedidos de laboratorio desde API móvil (médico)."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from laboratorio.models import PanelExamen, SolicitudExamen, TipoExamen, TipoMuestra
from medicos.models import Medico
from movil.models import FavoritoLabMedico, PaqueteLabContexto
from pacientes.models import Paciente

pytestmark = pytest.mark.django_db
User = get_user_model()


def _login(rol, username='u', with_medico=False):
    cache.clear()
    user = User.objects.create_user(username=username, password='test-password', rol=rol)
    medico = None
    if with_medico:
        medico = Medico.objects.create(
            user=user, nombre='Ana', apellido='Médica', matricula=f'M-{username}'
        )
    c = APIClient()
    r = c.post('/api/movil/login/', {'username': username, 'password': 'test-password'}, format='json')
    assert r.status_code == 200, r.data
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['token'])
    return c, user, medico


def _catalogo_minimo():
    tm = TipoMuestra.objects.create(codigo='SUE-LAB', nombre='Suero', activo=True)
    glu = TipoExamen.objects.create(codigo='GLU-LAB', nombre='Glucemia', tipo_muestra_requerida=tm, activo=True)
    crea = TipoExamen.objects.create(codigo='CRE-LAB', nombre='Creatinina', tipo_muestra_requerida=tm, activo=True)
    panel = PanelExamen.objects.create(codigo='PAN-BAS', nombre='Básico', activo=True)
    panel.tipos_examen.add(glu, crea)
    return glu, crea, panel


def test_perfil_medico_puede_pedir_lab():
    c, _, _ = _login('medico', 'doc1', with_medico=True)
    me = c.get('/api/movil/me/')
    assert me.status_code == 200
    assert me.data['puede_pedir_lab'] is True


def test_paciente_no_puede_pedir_lab():
    c, _, _ = _login('paciente', 'pac1')
    r = c.get('/api/movil/lab/pacientes/?q=12')
    assert r.status_code == 403


def test_buscar_paciente_y_crear_orden_con_examen_extra():
    c, _, medico = _login('medico', 'doc2', with_medico=True)
    glu, crea, panel = _catalogo_minimo()
    pac = Paciente.objects.create(nombre='Celia', apellido='Macias', dni='30111222')
    PaqueteLabContexto.objects.create(
        codigo='GUARDIA-BAS',
        nombre='Guardia básico',
        contexto='GUARDIA',
        activo=True,
        orden=1,
    ).paneles.add(panel)

    bus = c.get('/api/movil/lab/pacientes/?q=Macias')
    assert bus.status_code == 200, bus.data
    assert bus.data['results'][0]['id'] == pac.id
    assert bus.data['results'][0]['contexto_sugerido'] in ('GUARDIA', 'AMBULATORIO', 'INTERNACION')

    cat = c.get('/api/movil/lab/catalogo/?contexto=GUARDIA')
    assert cat.status_code == 200
    assert any(p['codigo'] == 'GUARDIA-BAS' for p in cat.data['paquetes'])
    assert any(e['codigo'] == 'GLU-LAB' for e in cat.data['examenes'])

    # Favorito panel
    fav = c.put(
        '/api/movil/lab/favoritos/',
        {'items': [{'kind': 'panel', 'id': panel.id}]},
        format='json',
    )
    assert fav.status_code == 200
    assert FavoritoLabMedico.objects.filter(medico=medico, panel=panel).exists()

    # Pedido: paquete (panel) + examen complementario (mismo panel ya lo tiene; agregamos solo panel + nada extra)
    # Complemento: pedir panel + examen suelto creatinina (ya en panel) y glucemia vía panel
    crear = c.post(
        '/api/movil/lab/ordenes/',
        {
            'paciente_id': pac.id,
            'contexto': 'GUARDIA',
            'paneles_ids': [panel.id],
            'examenes_ids': [crea.id],  # complemento / redundante OK
            'observaciones': 'Desde app móvil',
            'fecha_programada_toma': date.today().isoformat(),
        },
        format='json',
    )
    assert crear.status_code in (200, 201), crear.data
    assert crear.data['orden']['numero']
    assert SolicitudExamen.objects.filter(paciente=pac, medico_interno=medico).count() == 1

    mias = c.get('/api/movil/lab/ordenes/')
    assert mias.status_code == 200
    assert len(mias.data['results']) == 1


def test_orden_requiere_al_menos_un_item():
    c, _, _ = _login('medico', 'doc3', with_medico=True)
    pac = Paciente.objects.create(nombre='X', apellido='Y', dni='30999888')
    r = c.post(
        '/api/movil/lab/ordenes/',
        {'paciente_id': pac.id, 'contexto': 'AMBULATORIO', 'examenes_ids': [], 'paneles_ids': []},
        format='json',
    )
    assert r.status_code == 400


def test_medico_solo_ambulatorio_no_pide_guardia():
    c, _, medico = _login('medico', 'doc-amb', with_medico=True)
    medico.ambito_atencion = Medico.AMBITO_AMBULATORIO
    medico.save(update_fields=['ambito_atencion'])
    glu, _, _ = _catalogo_minimo()
    pac = Paciente.objects.create(nombre='Luis', apellido='SoloAmb', dni='30122334')

    me = c.get('/api/movil/me/')
    assert me.status_code == 200
    assert me.data['ambito_atencion'] == 'AMBULATORIO'
    assert me.data['contextos_lab_permitidos'] == ['AMBULATORIO']
    assert me.data['puede_guardia'] is False
    assert me.data['puede_internacion'] is False

    cat = c.get('/api/movil/lab/catalogo/?contexto=AMBULATORIO')
    assert cat.status_code == 200
    assert [x['id'] for x in cat.data['contextos']] == ['AMBULATORIO']

    denied = c.post(
        '/api/movil/lab/ordenes/',
        {
            'paciente_id': pac.id,
            'contexto': 'GUARDIA',
            'examenes_ids': [glu.id],
            'paneles_ids': [],
            'fecha_programada_toma': date.today().isoformat(),
        },
        format='json',
    )
    assert denied.status_code == 403

    ok = c.post(
        '/api/movil/lab/ordenes/',
        {
            'paciente_id': pac.id,
            'contexto': 'AMBULATORIO',
            'examenes_ids': [glu.id],
            'paneles_ids': [],
            'fecha_programada_toma': date.today().isoformat(),
        },
        format='json',
    )
    assert ok.status_code in (200, 201), ok.data
