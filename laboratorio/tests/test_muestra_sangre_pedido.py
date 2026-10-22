from laboratorio.muestra_sangre_pedido import es_tipo_muestra_sangre_pedido


def test_acepta_variantes_sangre_suero_plasma():
    assert es_tipo_muestra_sangre_pedido("SUERO")
    assert es_tipo_muestra_sangre_pedido("SANGRE_EDTA")
    assert es_tipo_muestra_sangre_pedido("PLASMA_EDTA")
    assert es_tipo_muestra_sangre_pedido("PLASMA_CITRATO")
    assert es_tipo_muestra_sangre_pedido("SANGRE_HEPARINA_ART")
    assert es_tipo_muestra_sangre_pedido("SANGRE_SECA_EN_PAPEL_FILTRO")
    assert es_tipo_muestra_sangre_pedido("SANGRE_2")
    assert es_tipo_muestra_sangre_pedido("SUERO_Y_ORINA_24_H")


def test_rechaza_no_sangre():
    assert not es_tipo_muestra_sangre_pedido("ORINA")
    assert not es_tipo_muestra_sangre_pedido("LCR")
    assert not es_tipo_muestra_sangre_pedido("ESPUTO")
    assert not es_tipo_muestra_sangre_pedido("PLASMA_SEMINAL")
    assert not es_tipo_muestra_sangre_pedido("MEDULA_OSEA_EDTA")
    assert not es_tipo_muestra_sangre_pedido("LIQ_PLEURAL")
    assert not es_tipo_muestra_sangre_pedido("")
    assert not es_tipo_muestra_sangre_pedido(None)
