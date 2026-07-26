from laboratorio.tubos_catalogo import tubo_codigo_para_examen


def test_tubo_hemograma_edta():
    assert tubo_codigo_para_examen("HGB") == "EDTA"
    assert tubo_codigo_para_examen("PLAQ") == "EDTA"
    assert tubo_codigo_para_examen("HBA1C") == "EDTA"


def test_tubo_vsg_citrato_negro():
    assert tubo_codigo_para_examen("VSG") == "CITRATO_VSG"
    assert tubo_codigo_para_examen("VSG", "SANGRE_CITRATO_VSG") == "CITRATO_VSG"


def test_tubo_coag_citrato():
    assert tubo_codigo_para_examen("TP") == "CITRATO"
    assert tubo_codigo_para_examen("KPTT") == "CITRATO"
    assert tubo_codigo_para_examen("DDIM") == "CITRATO"


def test_tubo_heparina_eab():
    assert tubo_codigo_para_examen("EAB_ART") == "HEPARINA"
    assert tubo_codigo_para_examen("EAB_VEN") == "HEPARINA"
    assert tubo_codigo_para_examen("LACT") == "HEPARINA"


def test_tubo_orina_frasco():
    assert tubo_codigo_para_examen("ORI_PH", "ORINA") == "FRASCO_ORINA"
    assert tubo_codigo_para_examen("CREA_U") == "FRASCO_ORINA"
    assert tubo_codigo_para_examen("PROT_U_AZ") == "FRASCO_ORINA"


def test_tubo_orina_24h_bidon():
    assert tubo_codigo_para_examen("PROT_U_24") == "BIDON_ORINA_24H"
    assert tubo_codigo_para_examen("CLEAR_CREA") == "BIDON_ORINA_24H"
    assert tubo_codigo_para_examen("DIUR") == "BIDON_ORINA_24H"
    assert tubo_codigo_para_examen("CA24", "ORINA_24_H") == "BIDON_ORINA_24H"
    assert tubo_codigo_para_examen("AAO", "ORINA_REPRESENTATIVA_DE_24_H") == "BIDON_ORINA_24H"


def test_tubo_quimica_rutina_heparina():
    assert tubo_codigo_para_examen("GLU") == "HEPARINA"
    assert tubo_codigo_para_examen("GOT") == "HEPARINA"
    assert tubo_codigo_para_examen("NA") == "HEPARINA"
    assert tubo_codigo_para_examen("TG") == "HEPARINA"


def test_tubo_suero_fuera_de_rutina():
    assert tubo_codigo_para_examen("TSH") == "SUERO"
    assert tubo_codigo_para_examen("AU") == "SUERO"
    assert tubo_codigo_para_examen("PCR_US") == "SUERO"
