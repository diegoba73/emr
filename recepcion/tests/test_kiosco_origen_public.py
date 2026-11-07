"""Origen del QR: URL pública del EMR tiene prioridad sobre LAN."""
import pytest
from rest_framework.test import APIClient

from recepcion.kiosco_origen import (
    es_url_permitida_qr_kiosco,
    resolver_origen_espera_kiosco,
    url_anuncio_kiosco,
)

pytestmark = pytest.mark.django_db


def test_public_api_base_url_gana_sobre_lan(monkeypatch):
    monkeypatch.setenv('PUBLIC_API_BASE_URL', 'https://emr.icpueblodeluis.com.ar:8080')
    monkeypatch.setenv('EMR_KIOSCO_LAN_ORIGIN', 'http://192.168.1.94:3000')
    monkeypatch.setenv('EMR_LAN_IPS', '192.168.1.94')
    info = resolver_origen_espera_kiosco()
    assert info['espera_origin'] == 'https://emr.icpueblodeluis.com.ar:8080'
    assert info['fuente'] == 'public'
    assert info['es_lan'] is False


def test_sin_publico_usa_lan(monkeypatch):
    monkeypatch.delenv('PUBLIC_API_BASE_URL', raising=False)
    monkeypatch.delenv('EMR_KIOSCO_PUBLIC_ORIGIN', raising=False)
    monkeypatch.setenv('EMR_KIOSCO_LAN_ORIGIN', 'http://192.168.1.94:3000')
    info = resolver_origen_espera_kiosco()
    assert info['espera_origin'] == 'http://192.168.1.94:3000'
    assert info['es_lan'] is True


def test_url_anuncio_siempre_kiosco_recepcion():
    assert (
        url_anuncio_kiosco('https://emr.icpueblodeluis.com.ar:8080')
        == 'https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion'
    )
    # Si alguien pega el APK, se descarta el path y queda el kiosco.
    assert (
        url_anuncio_kiosco('https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk')
        == 'https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion'
    )


def test_qr_png_rechaza_apk_acepta_kiosco():
    assert es_url_permitida_qr_kiosco(
        'https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion'
    )
    assert es_url_permitida_qr_kiosco('/kiosco-recepcion')
    assert es_url_permitida_qr_kiosco('/espera/abc')
    assert not es_url_permitida_qr_kiosco(
        'https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk'
    )
    client = APIClient()
    bad = client.get(
        '/api/recepcion/kiosco-qr.png',
        {'data': 'https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk'},
    )
    assert bad.status_code == 400
    good = client.get(
        '/api/recepcion/kiosco-qr.png',
        {'data': 'https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion'},
    )
    assert good.status_code == 200
    assert good['Content-Type'] == 'image/png'


def test_kiosco_config_expone_anuncio_url(monkeypatch):
    monkeypatch.setenv('PUBLIC_API_BASE_URL', 'https://emr.icpueblodeluis.com.ar:8080')
    r = APIClient().get('/api/recepcion/kiosco-config/')
    assert r.status_code == 200
    assert r.data['anuncio_url'] == (
        'https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion'
    )


def test_institucion_movil_expone_url_publica(settings, monkeypatch):
    settings.MOBILE_INSTITUTION_CODE = 'ICPL'
    settings.MOBILE_INSTITUTION_NAME = 'ICPL'
    monkeypatch.setenv('PUBLIC_API_BASE_URL', 'https://emr.icpueblodeluis.com.ar:8080')
    monkeypatch.delenv('EMR_KIOSCO_LAN_ORIGIN', raising=False)
    r = APIClient().get('/api/movil/institucion/')
    assert r.status_code == 200
    assert r.data['kiosco_anuncio_url'] == (
        'https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion'
    )
