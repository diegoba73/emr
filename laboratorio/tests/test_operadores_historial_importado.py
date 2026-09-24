"""Historial importado disponible para carga y validación, sin vínculo médico."""
import csv
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from usuarios.models import User


@pytest.mark.django_db
@pytest.mark.parametrize('rol', ['laboratorio', 'bioquimico'])
def test_operador_consulta_importado_y_compara_orden_nueva(tmp_path, rol):
    muestra = TipoMuestra.objects.create(codigo='SUERO_HIST', nombre='Suero')
    tipo = TipoExamen.objects.create(codigo='GLU', nombre='Glucemia',
        tipo_muestra_requerida=muestra, tipo_resultado='NUMERICO', unidad_default='mg/dL')
    archivo = tmp_path / 'historial.csv'
    with archivo.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['Número', 'Fecha', 'Nº doc.', 'Apellido y nombre', 'Sexo', 'F. nacim.', 'GLU'])
        writer.writerow(['1(1)', '30/06/2022', '90111222', 'PRUEBA HISTORIAL', 'M', '01/01/1980', '75'])
    call_command('import_labwin_csv', str(archivo), allow_new_patients=True, verbosity=0)
    anterior = SolicitudExamen.objects.get(numero='LW-2022-00001')
    assert anterior.estado == 'FINALIZADO'
    assert anterior.medico_interno_id is None
    assert not anterior.muestras.exists()

    user = User.objects.create_user(username=f'hist_{rol}', password='x', rol=rol, is_staff=False)
    client = APIClient()
    client.force_authenticate(user)
    listado = client.get('/api/lab/solicitudes/', {'paciente': anterior.paciente_id})
    assert listado.status_code == 200
    assert anterior.pk in {row['id'] for row in listado.data['results']}
    detalle = client.get(f'/api/lab/solicitudes/{anterior.pk}/')
    assert detalle.status_code == 200
    assert detalle.data['resultados_visibles'] is True
    assert any(r['valor_obtenido'] == '75' for r in detalle.data['resultados'])

    nueva = SolicitudExamen.objects.create(numero='LAB-HIST-NUEVA', paciente=anterior.paciente,
        estado='EN_PROCESO', origen_solicitud='AMBULATORIO_ICPL')
    actual = ResultadoExamen.objects.create(solicitud=nueva, tipo_examen=tipo, valor_obtenido='')
    historial = client.get(f'/api/lab/solicitudes/{nueva.pk}/historial-analitos/')
    assert historial.status_code == 200
    previos = historial.data['analitos'][0]['previos']
    assert previos[0]['solicitud_id'] == anterior.pk
    assert previos[0]['valor'] == '75'
    assert previos[0]['unidad'] == 'mg/dL'
    assert previos[0]['fecha'].startswith('2022-06-30')

    # La comparación debe seguir disponible tras guardar y al quedar lista para validar.
    ResultadoExamen.objects.filter(pk=actual.pk).update(
        valor_obtenido='90', valor_numerico=Decimal('90'), unidad='mg/dL')
    SolicitudExamen.objects.filter(pk=nueva.pk).update(estado='LISTO_PARA_VALIDAR')
    comparacion = client.get(f'/api/lab/solicitudes/{nueva.pk}/analisis-longitudinal/')
    assert comparacion.status_code == 200
    assert comparacion.data['total_con_historial'] == 1
    assert comparacion.data['resultados'][0]['historial']['valor_anterior'] == '75'
