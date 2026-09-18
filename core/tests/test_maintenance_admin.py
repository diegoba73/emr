"""Consola avanzada: rol admin, edición y retiro reversible con historial."""
import pytest
from django.test import RequestFactory

from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from core.maintenance_admin import maintenance_site
from internacion.models import Cama, Sector
from laboratorio.models import TipoExamen, TipoMuestra
from usuarios.models import User


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(username='mantenimiento', password='clave-test',
                                    rol='admin', is_staff=False, is_superuser=False)


@pytest.mark.django_db
def test_admin_sin_staff_ni_superuser_accede_y_edita(client, admin_user):
    client.force_login(admin_user)
    index = client.get('/api/administracion/')
    assert index.status_code == 200
    assert 'Administración avanzada'.encode() in index.content
    tm = TipoMuestra.objects.create(codigo='EDITAR', nombre='Anterior')
    with capture_on_commit_callbacks(execute=True):
        response = client.post(f'/api/administracion/laboratorio/tipomuestra/{tm.pk}/change/',
                               {'codigo': 'EDITAR', 'nombre': 'Corregido', 'activo': 'on', '_save': 'Guardar'})
    assert response.status_code == 302
    tm.refresh_from_db()
    assert tm.nombre == 'Corregido'
    event = AuditEvent.objects.get(module='administracion', entity_type='laboratorio.TipoMuestra', entity_id=str(tm.pk))
    assert event.actor_id == admin_user.pk
    assert event.before_state['nombre'] == 'Anterior'
    assert event.after_state['nombre'] == 'Corregido'


@pytest.mark.django_db
def test_login_admin_no_exige_staff(client, admin_user):
    response = client.post('/api/administracion/login/', {
        'username': admin_user.username, 'password': 'clave-test', 'next': '/api/administracion/',
    })
    assert response.status_code == 302
    assert client.get('/api/administracion/').status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize('rol', ['medico', 'secretaria', 'enfermeria', 'laboratorio', 'bioquimico'])
def test_otros_roles_no_entran_aunque_sean_staff(client, rol):
    user = User.objects.create_user(username=rol, password='x', rol=rol, is_staff=True)
    client.force_login(user)
    for url in ('/api/administracion/', '/api/administracion/internacion/cama/'):
        assert client.get(url).status_code == 302


@pytest.mark.django_db
def test_catalogo_con_referencias_se_retira_y_recupera(client, admin_user):
    client.force_login(admin_user)
    tm = TipoMuestra.objects.create(codigo='REFERIDO', nombre='Suero')
    te = TipoExamen.objects.create(codigo='TEST', nombre='Ensayo', tipo_muestra_requerida=tm)
    url = '/api/administracion/laboratorio/tipomuestra/'
    for action, activo in [('retirar', False), ('recuperar', True)]:
        with capture_on_commit_callbacks(execute=True):
            response = client.post(url, {'action': action, '_selected_action': [tm.pk], 'index': 0})
        assert response.status_code == 302
        tm.refresh_from_db()
        assert tm.activo is activo
        te.refresh_from_db()
        assert te.tipo_muestra_requerida_id == tm.pk
        assert AuditEvent.objects.filter(module='administracion', entity_id=str(tm.pk),
                                         actor=admin_user, after_state__activo=activo).exists()
    response = client.post(f'{url}{tm.pk}/delete/', {'post': 'yes'})
    assert response.status_code == 403
    assert TipoExamen.objects.filter(pk=te.pk).exists()


@pytest.mark.django_db
def test_borrado_configuracion_sin_referencias(client, admin_user):
    client.force_login(admin_user)
    sector = Sector.objects.create(nombre='Sin uso')
    response = client.post(f'/api/administracion/internacion/sector/{sector.pk}/delete/', {'post': 'yes'})
    assert response.status_code == 302
    assert not Sector.objects.filter(pk=sector.pk).exists()


@pytest.mark.django_db
def test_auditoria_permanece_solo_lectura(admin_user):
    request = RequestFactory().get('/api/administracion/')
    request.user = admin_user
    model_admin = maintenance_site._registry[AuditEvent]
    assert model_admin.has_view_permission(request)
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)


@pytest.mark.django_db
def test_formularios_de_todos_los_modulos_accesibles(client, admin_user):
    client.force_login(admin_user)
    for model in maintenance_site._registry:
        meta = model._meta
        if meta.app_label == 'auditoria':
            continue
        response = client.get(f'/api/administracion/{meta.app_label}/{meta.model_name}/add/')
        assert response.status_code == 200, meta.label


@pytest.mark.django_db
def test_editar_sector_retira_camas_y_audita(client, admin_user):
    client.force_login(admin_user)
    sector = Sector.objects.create(nombre='Sector retirado por formulario')
    cama = Cama.objects.create(nombre='Cama dependiente', sector=sector)
    with capture_on_commit_callbacks(execute=True):
        response = client.post(f'/api/administracion/internacion/sector/{sector.pk}/change/',
                               {'nombre': sector.nombre, '_save': 'Guardar'})
    assert response.status_code == 302
    cama.refresh_from_db()
    sector.refresh_from_db()
    assert not cama.activo and not sector.activo
    assert AuditEvent.objects.filter(module='administracion', entity_type='internacion.Cama',
                                     entity_id=str(cama.pk), actor=admin_user,
                                     before_state__activo=True, after_state__activo=False).exists()
