from laboratorio.tubos_catalogo import tubo_codigo_para_examen


def test_tubo_hemograma_edta():
    assert tubo_codigo_para_examen("HGB") == "EDTA"
    assert tubo_codigo_para_examen("PLAQ") == "EDTA"
    assert tubo_codigo_para_examen("HBA1C") == "EDTA"


def test_tubo_vsg_eritro():
    assert tubo_codigo_para_examen("VSG") == "ERITRO"
    assert tubo_codigo_para_examen("VSG", "SANGRE_ERITRO") == "ERITRO"
    assert tubo_codigo_para_examen("VSG", "SANGRE_CITRATO_VSG") == "ERITRO"


def test_tubo_coag_citrato():
    assert tubo_codigo_para_examen("TP") == "CITRATO"
    assert tubo_codigo_para_examen("KPTT") == "CITRATO"
    assert tubo_codigo_para_examen("DDIM") == "CITRATO"


def test_tubo_heparina_eab():
    assert tubo_codigo_para_examen("PH_ART") == "HEPARINA"
    assert tubo_codigo_para_examen("PH_VEN") == "HEPARINA"
    assert tubo_codigo_para_examen("HCO3_ART") == "HEPARINA"
    assert tubo_codigo_para_examen("BE_VEN") == "HEPARINA"
    assert tubo_codigo_para_examen("LACT") == "HEPARINA"
    assert tubo_codigo_para_examen("FIO2") is None


def test_tubo_orina_frasco():
    assert tubo_codigo_para_examen("ORI_PH", "ORINA") == "FRASCO_ORINA"
    assert tubo_codigo_para_examen("CREA_U") == "FRASCO_ORINA"
    assert tubo_codigo_para_examen("PROT_U_AZ") == "FRASCO_ORINA"


def test_tubo_orina_24h_bidon():
    # Medidos / contexto 24h → bidón; CALCULADO no genera tubo propio.
    assert tubo_codigo_para_examen("PROT_U_24") is None
    assert tubo_codigo_para_examen("CLEAR_CREA") is None
    assert tubo_codigo_para_examen("DIUR") == "BIDON_ORINA_24H"
    assert tubo_codigo_para_examen("CA24", "ORINA_24_H") == "BIDON_ORINA_24H"
    assert tubo_codigo_para_examen("AAO", "ORINA_REPRESENTATIVA_DE_24_H") == "BIDON_ORINA_24H"


def test_calculados_y_fio2_sin_tubo():
    assert tubo_codigo_para_examen("FIO2") is None
    assert tubo_codigo_para_examen("LDL") is None
    assert tubo_codigo_para_examen("BIL_I") is None
    assert tubo_codigo_para_examen("MICROALB_24") is None


def test_tubo_quimica_rutina_suero():
    assert tubo_codigo_para_examen("GLU") == "SUERO"
    assert tubo_codigo_para_examen("GOT") == "SUERO"
    assert tubo_codigo_para_examen("NA") == "SUERO"
    assert tubo_codigo_para_examen("TG") == "SUERO"


def test_tubo_suero_fuera_de_rutina():
    assert tubo_codigo_para_examen("TSH") == "SUERO"
    assert tubo_codigo_para_examen("AU") == "SUERO"
    assert tubo_codigo_para_examen("PCR_US") == "SUERO"
