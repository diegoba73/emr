from laboratorio.tubos_catalogo import tubo_codigo_para_examen


def test_tubo_hemograma_edta():
    assert tubo_codigo_para_examen("HGB") == "EDTA"
    assert tubo_codigo_para_examen("PLAQ") == "EDTA"
    assert tubo_codigo_para_examen("HBA1C") == "EDTA"


def test_tubo_coag_citrato():
    assert tubo_codigo_para_examen("TP") == "CITRATO"
    assert tubo_codigo_para_examen("KPTT") == "CITRATO"
    assert tubo_codigo_para_examen("DDIM") == "CITRATO"


def test_tubo_heparina_eab():
    assert tubo_codigo_para_examen("EAB_ART") == "HEPARINA"
    assert tubo_codigo_para_examen("LACT") == "HEPARINA"


def test_tubo_orina_frasco():
    assert tubo_codigo_para_examen("ORI_PH", "ORINA") == "FRASCO_ORINA"
    assert tubo_codigo_para_examen("CREA_U") == "FRASCO_ORINA"


def test_tubo_quimica_suero():
    assert tubo_codigo_para_examen("GLU", "SANGRE") == "SUERO"
    assert tubo_codigo_para_examen("TSH") == "SUERO"
    assert tubo_codigo_para_examen("GOT") == "SUERO"
