"""Origen del QR: URL pública del EMR tiene prioridad sobre LAN."""
import pytest

from recepcion.kiosco_origen import resolver_origen_espera_kiosco

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


def test_institucion_movil_expone_url_publica(settings, monkeypatch):
    from rest_framework.test import APIClient

    settings.MOBILE_INSTITUTION_CODE = 'ICPL'
    settings.MOBILE_INSTITUTION_NAME = 'ICPL'
    monkeypatch.setenv('PUBLIC_API_BASE_URL', 'https://emr.icpueblodeluis.com.ar:8080')
    monkeypatch.delenv('EMR_KIOSCO_LAN_ORIGIN', raising=False)
    r = APIClient().get('/api/movil/institucion/')
    assert r.status_code == 200
    assert r.data['kiosco_anuncio_url'] == (
        'https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion'
    )
