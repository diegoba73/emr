"""Corrección de TG: invalidar derivados previos y conservar un informe explícito."""
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from auditoria.models import AuditEvent
from auditoria.tests.compat import capture_on_commit_callbacks
from laboratorio.calculos_derivados import RESULTADO_NO_CALCULABLE
from laboratorio.informe_pdf_layout import _valor_y_unidad, generar_pdf_icpl_bytes
from laboratorio.models import PanelExamen, TipoExamen, ResultadoExamen, SolicitudExamen
from pacientes.models import Paciente
from usuarios.models import User


@pytest.fixture
def perfil(db):
    call_command('seed_catalogo_solicitud_papel', stdout=StringIO())
    paciente = Paciente.objects.create(dni='PRUEBA-LDL', nombre='Prueba', apellido='Perfil')
    actor = User.objects.create_user(username='prueba-ldl', rol='bioquimico')
    client = APIClient()
    client.force_authenticate(actor)
    sol = SolicitudExamen.objects.create(paciente=paciente, estado='EN_PROCESO', origen_solicitud='AMBULATORIO_CEHTA')
    sol.paneles.add(PanelExamen.objects.get(codigo='PAN_LIP'))
    rows = {codigo: ResultadoExamen.objects.create(solicitud=sol, tipo_examen=TipoExamen.objects.get(codigo=codigo))
            for codigo in ('COL_TOT', 'HDL', 'TG')}
    return sol, actor, client, rows


def cargar(perfil, valores, extras=None):
    sol, actor, client, rows = perfil
    payload = [{'id': rows[codigo].pk, 'valor': str(valor), 'valor_numerico': str(valor)}
               for codigo, valor in valores.items()]
    response = client.post(f'/api/lab/solicitudes/{sol.pk}/cargar-resultados/',
                           {'resultados': payload + (extras or [])}, format='json')
    assert response.status_code == 200, response.data
    return response


@pytest.mark.django_db
@pytest.mark.parametrize('tg', ['400', '401', '600'])
def test_correccion_retiro_guardado_lectura_pdf_y_recuperacion(perfil, tg):
    sol, actor, client, rows = perfil
    cargar(perfil, {'COL_TOT': '101', 'HDL': '33', 'TG': '99'})
    ldl = sol.resultados.get(tipo_examen__codigo='LDL')
    assert ldl.valor_numerico == Decimal('48')
    # Simula valores previos marcados y un cliente con LDL viejo en su payload.
    sol.resultados.filter(tipo_examen__codigo__in=['LDL', 'COL_RESID']).update(es_patologico=True, es_critico=True)
    with capture_on_commit_callbacks(execute=True):
        cargar(perfil, {'TG': tg}, [{'id': ldl.pk, 'valor': '48', 'valor_numerico': '48'}])
    for codigo in ('LDL', 'COL_RESID'):
        res = sol.resultados.select_related('tipo_examen').get(tipo_examen__codigo=codigo)
        assert res.valor_numerico is None
        assert res.valor_obtenido == RESULTADO_NO_CALCULABLE
        assert not res.es_patologico and not res.es_critico
        assert _valor_y_unidad(res) == (RESULTADO_NO_CALCULABLE, '')
        assert AuditEvent.objects.filter(actor=actor, entity_type='laboratorio.ResultadoExamen',
                                         entity_id=str(res.pk), metadata__accion='recalcular_resultado',
                                         metadata__calculable=False).exists()
    detail = client.get(f'/api/lab/solicitudes/{sol.pk}/')
    assert detail.status_code == 200
    leido = next(r for r in detail.data['resultados'] if r['id'] == ldl.pk)
    assert leido['valor_numerico'] is None
    assert leido['valor_obtenido'] == RESULTADO_NO_CALCULABLE
    pdf = generar_pdf_icpl_bytes(sol, list(sol.resultados.select_related('tipo_examen__tipo_muestra_requerida')))
    assert pdf.startswith(b'%PDF')
    cargar(perfil, {'TG': tg})
    ldl.refresh_from_db()
    assert ldl.valor_numerico is None
    cargar(perfil, {'TG': '150'})
    ldl.refresh_from_db()
    assert ldl.valor_numerico == Decimal('38')
    assert ldl.valor_obtenido == '38'
    residual = sol.resultados.get(tipo_examen__codigo='COL_RESID')
    assert residual.valor_numerico == Decimal('30')


@pytest.mark.django_db
def test_correccion_solo_texto_no_reutiliza_numero_anterior(perfil):
    sol, actor, client, rows = perfil
    cargar(perfil, {'COL_TOT': '101', 'HDL': '33', 'TG': '99'})
    response = client.post(f'/api/lab/solicitudes/{sol.pk}/cargar-resultados/',
                           {'resultados': [{'id': rows['TG'].pk, 'valor': '400'}]},
                           format='json')
    assert response.status_code == 200, response.data
    rows['TG'].refresh_from_db()
    assert rows['TG'].valor_obtenido == '400'
    assert rows['TG'].valor_numerico is None
    ldl = sol.resultados.get(tipo_examen__codigo='LDL')
    assert ldl.valor_numerico is None
    assert ldl.valor_obtenido == RESULTADO_NO_CALCULABLE


@pytest.mark.django_db
def test_orden_finalizada_conserva_historial(perfil):
    sol, actor, client, rows = perfil
    cargar(perfil, {'COL_TOT': '101', 'HDL': '33', 'TG': '99'})
    sol.refresh_from_db()
    sol.estado = 'FINALIZADO'
    sol.save(update_fields=['estado'])
    response = client.post(f'/api/lab/solicitudes/{sol.pk}/cargar-resultados/',
                           {'resultados': [{'id': rows['TG'].pk, 'valor': '400', 'valor_numerico': '400'}]},
                           format='json')
    assert response.status_code == 400
    assert sol.resultados.get(tipo_examen__codigo='LDL').valor_numerico == Decimal('48')
