import pytest
from django.core.files.base import ContentFile
from django.core import mail
from estudios.models import InformeEstudioComplementario

@pytest.fixture
def informe_envio(estudio_solicitado, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    estudio_solicitado.estado = 'VALIDADO'
    estudio_solicitado.save()
    paciente = estudio_solicitado.paciente
    paciente.email = 'paciente@example.com'
    paciente.save()
    informe = InformeEstudioComplementario.objects.create(estudio=estudio_solicitado, version=1, estado='VALIDADO', es_vigente=True)
    informe.archivo_pdf.save('prueba.pdf', ContentFile(b'%PDF-1.4 informe de prueba'))
    return informe

def endpoint(informe):
    return f'/api/estudios-complementarios/{informe.estudio_id}/informes/{informe.id}/enviar/'

@pytest.mark.django_db
def test_secretaria_envia_pdf_validado_sin_cambiar_estado(client, secretaria, informe_envio):
    client.force_authenticate(user=secretaria)
    r = client.post(endpoint(informe_envio), {}, format='json')
    assert r.status_code == 200, r.data
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['paciente@example.com']
    assert mail.outbox[0].attachments[0][2] == 'application/pdf'
    informe_envio.estudio.refresh_from_db()
    assert informe_envio.estudio.estado == 'VALIDADO'

@pytest.mark.django_db
@pytest.mark.parametrize('estado,vigente', [('BORRADOR',False), ('EMITIDO',False), ('VALIDADO',False)])
def test_secretaria_no_envia_borradores_ni_versiones_reemplazadas(client, secretaria, informe_envio, estado, vigente):
    informe_envio.estado = estado
    informe_envio.es_vigente = vigente
    informe_envio.save()
    client.force_authenticate(user=secretaria)
    r = client.post(endpoint(informe_envio), {}, format='json')
    assert r.status_code == 403
    assert not getattr(mail, 'outbox', [])

@pytest.mark.django_db
def test_envio_exige_correo_en_ficha(client, secretaria, informe_envio):
    paciente = informe_envio.estudio.paciente
    paciente.email = ''
    paciente.save()
    client.force_authenticate(user=secretaria)
    r = client.post(endpoint(informe_envio), {}, format='json')
    assert r.status_code == 400
    assert not getattr(mail, 'outbox', [])

@pytest.mark.django_db
def test_enfermeria_no_puede_enviar(client, enfermeria, informe_envio):
    client.force_authenticate(user=enfermeria)
    assert client.post(endpoint(informe_envio), {}, format='json').status_code == 403
    assert not getattr(mail, 'outbox', [])

@pytest.mark.django_db
def test_fallo_smtp_no_se_informa_como_exito(client, secretaria, informe_envio, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('SMTP unavailable')
    monkeypatch.setattr('django.core.mail.EmailMessage.send', fail)
    client.force_authenticate(user=secretaria)
    assert client.post(endpoint(informe_envio), {}, format='json').status_code == 400

@pytest.mark.django_db
@pytest.mark.parametrize('estado', ['INFORMADO', 'ANULADO'])
def test_no_envia_si_el_estudio_no_esta_validado_o_entregado(client, secretaria, informe_envio, estado):
    estudio = informe_envio.estudio
    estudio.estado = estado
    estudio.save()
    client.force_authenticate(user=secretaria)
    assert client.post(endpoint(informe_envio), {}, format='json').status_code == 403
    assert not getattr(mail, 'outbox', [])

@pytest.mark.django_db
def test_no_finge_envio_con_backend_de_correo_de_consola(client, secretaria, informe_envio, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    client.force_authenticate(user=secretaria)
    assert client.post(endpoint(informe_envio), {}, format='json').status_code == 400
