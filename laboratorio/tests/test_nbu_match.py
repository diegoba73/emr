"""Matching NBU vs nombres de TipoExamen: no asignar códigos a destiempo."""
from laboratorio.nbu_match import (
    ExamRow,
    NbuPractica,
    match_exam,
    specimen_group,
)


MINI = [
    NbuPractica("662119", "ÁCIDO CÍTRICO - plasmático", "PE"),
    NbuPractica("662120", "ÁCIDO CÍTRICO - urinario", "PE"),
    NbuPractica("662296", "ÁCIDO OXALICO - sérico", "PE"),
    NbuPractica("662299", "ÁCIDO OXALICO - urinario (2/ 12 / 24 hs. - c/u)", "PE"),
    NbuPractica("662417", "ADENOSIN DEAMINASA - LCR", "PE"),
    NbuPractica("662418", "ADENOSIN DEAMINASA - líquido pleural", "PE"),
    NbuPractica("660412", "GLUCEMIA (C/U)", "PMO"),
    NbuPractica("660417", "GLUCOSA en orina (C/U)", "PMO"),
    NbuPractica("660413", "GLUCEMIA, PRUEBA de SOBRECARGA (x 2 - dos determinaciones)", "PMO"),
    NbuPractica("660865", "TIROTROFINA - TSH", "PMO"),
    NbuPractica("660867", "TIROXINA EFECTIVA - LIBRE (FT4 / T4L)", "PMO"),
    NbuPractica("660873", "TRANSAMINASA, GLUTAMICO OXALACETICA (GOT / AST)", "PMO"),
    NbuPractica("660874", "TRANSAMINASA, GLUTAMICO PIRUVICA (GPT / AGT)", "PMO"),
    NbuPractica("660475", "HEMOGRAMA.", "PMO"),
    NbuPractica("661000", "ANTIGENO PROSTATICO ESPECÍFICO TOTAL - PSA-t", "PMO"),
    NbuPractica("662734", "ANTÍGENO PROSTÁTICO ESPECÍFICO, Libre+Total (PSA-L+T)", "PE"),
    NbuPractica("662025", "ACETILCOLINA, Ac. Anti- RECEPTORES (ACRA)", "PE"),
    NbuPractica("668580", "PROGESTERONA 17-HIDROXI (17-OH-Pg)", "PE"),
    NbuPractica("667751", "NEONATAL, 17-HIDROXIPROGESTERONA (17-HO-Pg-Neo)", "PE"),
    NbuPractica("669909", "VITAMINA D2 + D3  (ERGOCALCIFEROL + 25-HIDROXICALCIFEROL O COLECALCIFEROL)", "PE"),
    NbuPractica("669905", "VITAMINA D  (1,25-DIHIDROXICOLECALCIFEROL O CALCITRIOL - 1,25-VITAMINA D", "PE"),
    NbuPractica("660702", "NUCLEOTIDASA - 5' N", "PMO"),
    NbuPractica("660006", "ACTH - HORMONA ADRENOCORTICOTROFINA.", "PMO"),
    NbuPractica("662009", "ACANTHAMOEBA - PCR", "PE"),
    NbuPractica("660761", "PROTEINA C REACTIVA - PCR", "PMO"),
]


def _m(nombre, muestra="", codigo="X"):
    return match_exam(ExamRow(1, codigo, nombre, muestra), MINI)


def test_citrico_no_cruza_suero_con_orina():
    r = _m("Acido Citrico", "Suero")
    assert r.auto
    assert r.practica.codigo_nbu == "662119"

    r = _m("Acido Citrico", "Orina")
    assert r.auto
    assert r.practica.codigo_nbu == "662120"


def test_oxalico_orina_no_toma_serico():
    r = _m("Acido Oxalico", "Orina 24 hs")
    assert r.auto
    assert r.practica.codigo_nbu == "662299"


def test_ada_pleural_no_toma_lcr():
    r = _m("Adenosin Deaminasa", "líquido pleural")
    assert r.auto
    assert r.practica.codigo_nbu == "662418"

    r = _m("Adenosin Deaminasa", "LCR")
    assert r.auto
    assert r.practica.codigo_nbu == "662417"


def test_glucemia_sangre_vs_glucosa_orina():
    r = _m("Glucemia", "Plasma heparina", codigo="GLU")
    assert r.auto
    assert r.practica.codigo_nbu == "660412"

    r = _m("Glucosa", "Orina")
    assert r.auto
    assert r.practica.codigo_nbu == "660417"


def test_tsh_y_t4_libre():
    r = _m("TSH", "Suero")
    assert r.auto
    assert r.practica.codigo_nbu == "660865"

    r = _m("T4 libre", "Suero")
    assert r.auto
    assert r.practica.codigo_nbu == "660867"


def test_got_gpt():
    r = _m("GOT (AST)", "Plasma heparina")
    assert r.auto
    assert r.practica.codigo_nbu == "660873"

    r = _m("GPT (ALT)", "Plasma heparina")
    assert r.auto
    assert r.practica.codigo_nbu == "660874"


def test_hemograma_y_psa_total():
    r = _m("Hemograma", "Sangre EDTA")
    assert r.auto
    assert r.practica.codigo_nbu == "660475"

    r = _m("PSA Total - Ag. Prostatico Especifico Total", "Suero")
    assert r.auto
    assert r.practica.codigo_nbu == "661000"


def test_psa_libre_y_total_no_se_asigna_al_total():
    r = _m("PSA Libre y PSA Total", "Suero")
    assert r.practica is not None
    assert r.practica.codigo_nbu == "662734"


def test_acra_por_alias_parentesis():
    r = _m("ACRA - Receptores Acetil Colina Ac.", "Suero")
    assert r.auto
    assert r.practica.codigo_nbu == "662025"


def test_17ohp_invertido_y_neonatal():
    r = _m("17-Hidroxi Progesterona", "Suero")
    assert r.auto
    assert r.practica.codigo_nbu == "668580"

    r = _m("17-Hidroxi Progesterona neonatal", "sangre seca en papel filtro")
    assert r.auto
    assert r.practica.codigo_nbu == "667751"


def test_vitamina_d_25_no_es_calcitriol():
    r = _m("25-Hidroxivitamina D (D2 + D3)", "Suero")
    assert r.practica is not None
    assert r.practica.codigo_nbu == "669909"


def test_nucleotidasa_y_acth():
    r = _m("5'Nucleotidasa", "Suero")
    assert r.auto
    assert r.practica.codigo_nbu == "660702"

    r = _m("ACTH - Adrenocorticotrofina", "plasma")
    assert r.auto
    assert r.practica.codigo_nbu == "660006"


def test_pcr_molecular_no_es_proteina_c_reactiva():
    r = _m("Acanthamoeba PCR", "hisopado conjuntival")
    assert r.auto
    assert r.practica.codigo_nbu == "662009"


def test_specimen_group_helpers():
    assert specimen_group("ÁCIDO CÍTRICO - urinario") == "orina"
    assert specimen_group("Glucemia", "Plasma heparina") == "sangre"
    assert specimen_group("SODIO - sérico o urinario.") is None


def test_sufijo_emia_es_sangre_y_uria_es_orina():
    assert specimen_group("Glucemia") == "sangre"
    assert specimen_group("Uremia") == "sangre"
    assert specimen_group("Calcemia") == "sangre"
    assert specimen_group("Bilirrubinemia") == "sangre"
    assert specimen_group("Glucosuria") == "orina"
    assert specimen_group("Acetonuria") == "orina"


def test_glucosuria_no_toma_glucemia():
    r = _m("Glucosuria")
    assert r.auto
    assert r.practica.codigo_nbu == "660417"


def test_calcemia_por_sufijo():
    catalog = MINI + [NbuPractica("660133", "CALCEMIA TOTAL (Ca)", "PMO", "1.5")]
    r = match_exam(ExamRow(1, "CA", "Calcemia"), catalog)
    assert r.auto
    assert r.practica.codigo_nbu == "660133"


def test_distrofia_miotonica_tipo_no_cruza():
    catalog = MINI + [
        NbuPractica("664448", "DISTROFIA MIOTONICA Tipo 1 ( enfermedad de steinert )", "PE"),
    ]
    r = match_exam(ExamRow(1, "DMT2", "Distrofia Miotónica tipo 2", "sangre"), catalog)
    assert r.practica is None or r.practica.codigo_nbu != "664448"
    assert not r.auto
