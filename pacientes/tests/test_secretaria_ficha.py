import pytest
from rest_framework.test import APIClient
from usuarios.models import User
from pacientes.models import Paciente

@pytest.mark.django_db
@pytest.mark.parametrize('rol', ['secretaria', 'SECRETARIA'])
def test_secretaria_crea_y_corrige_todos_los_campos_de_ficha(rol):
    user = User.objects.create_user(username='sec_ficha', rol=rol, password='test')
    client = APIClient()
    client.force_authenticate(user=user)
    datos = dict(nombre='Ana', apellido='Test', dni='SEC-1', fecha_nacimiento='1990-01-01', sexo='O', estado_civil='Casada', telefono='123', email='ana@example.com', direccion='calle 1', obra_social='OS', numero_afiliado='123', familiar_nombre='Contacto', familiar_telefono='456', observaciones='Nota', antecedentes_personales='AP', antecedentes_familiares='AF')
    r = client.post('/api/pacientes/', datos, format='json')
    assert r.status_code == 201, r.data
    pid = r.data['id']
    datos.update(dni='SEC-2', nombre='Otra', estado_civil='Soltera', familiar_nombre='Nuevo contacto', observaciones='Nota corregida')
    r = client.patch(f'/api/pacientes/{pid}/', datos, format='json')
    assert r.status_code == 200, r.data
    p = Paciente.objects.get(pk=pid)
    assert p.dni == 'SEC-2'
    assert p.observaciones == 'Nota corregida'
    assert p.antecedentes_personales == 'AP'
    assert p.modificado_por_id == user.id
    assert p.creado_por_id == user.id
