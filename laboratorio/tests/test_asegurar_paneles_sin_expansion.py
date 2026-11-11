"""Regresión: no expandir paneles por componentes compartidos sin panel explícito."""
from io import StringIO

import pytest
from django.core.management import call_command

from laboratorio.hemograma_resultados import asegurar_resultados_paneles_derivados
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from pacientes.models import Paciente


def _ensure_caie() -> None:
    """CAIE puede no estar en el seed papel; asegurar fila activa para el test."""
    from laboratorio.models import TipoMuestra

    tm = TipoMuestra.objects.filter(codigo="SUERO").first() or TipoMuestra.objects.first()
    assert tm is not None
    TipoExamen.objects.update_or_create(
        codigo="CAIE",
        defaults={
            "nombre": "Calcio ionico estimado",
            "activo": True,
            "tipo_resultado": "NUMERICO",
            "tipo_muestra_requerida": tm,
            "precio": 1,
        },
    )


def _sol_con_codigos(*codigos: str, paneles: tuple[str, ...] = ()) -> SolicitudExamen:
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    if "CAIE" in codigos:
        _ensure_caie()
    # DNI max 20 chars en Paciente.
    dni_body = "-".join(codigos)[:12]
    paciente = Paciente.objects.create(
        dni=f"NX{dni_body}"[:20],
        nombre="No",
        apellido="Expand",
    )
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
        origen_solicitud="AMBULATORIO_CEHTA",
    )
    for codigo in paneles:
        sol.paneles.add(PanelExamen.objects.get(codigo=codigo))
    for codigo in codigos:
        te = TipoExamen.objects.get(codigo=codigo)
        ResultadoExamen.objects.create(solicitud=sol, tipo_examen=te)
        sol.tipos_examen.add(te)
    return sol


def _codigos(sol: SolicitudExamen) -> set[str]:
    return set(sol.resultados.values_list("tipo_examen__codigo", flat=True))


@pytest.mark.django_db
def test_ca_ion_suelto_no_trae_insumos_zeisler():
    """CA_ION medido (K-ión) no completa CA/PROT_T."""
    sol = _sol_con_codigos("CA_ION")
    assert asegurar_resultados_paneles_derivados(sol) == 0
    assert _codigos(sol) == {"CA_ION"}


@pytest.mark.django_db
def test_caie_suelto_trae_ca_y_prot_t():
    """CAIE suelto completa CA + PROT_T para Zeisler; no arrastra EAB."""
    sol = _sol_con_codigos("CAIE")
    assert asegurar_resultados_paneles_derivados(sol) == 2
    assert _codigos(sol) == {"CAIE", "CA", "PROT_T"}


@pytest.mark.django_db
def test_caie_con_eab_no_trae_insumos_zeisler():
    """Con EAB no forzar CA/PROT_T aunque haya CAIE."""
    sol = _sol_con_codigos("CAIE", paneles=("PAN_EAB_ART",))
    asegurar_resultados_paneles_derivados(sol)
    codigos = _codigos(sol)
    assert "CAIE" in codigos
    assert "CA" not in codigos
    assert "PROT_T" not in codigos


@pytest.mark.django_db
def test_diur_sola_no_expande_ningun_panel_24hs():
    sol = _sol_con_codigos("DIUR")
    assert asegurar_resultados_paneles_derivados(sol) == 0
    assert _codigos(sol) == {"DIUR"}


@pytest.mark.django_db
def test_hgb_sola_sin_panel_no_expande_hemograma():
    sol = _sol_con_codigos("HGB")
    assert asegurar_resultados_paneles_derivados(sol) == 0
    assert _codigos(sol) == {"HGB"}


@pytest.mark.django_db
def test_panel_clear_explicito_si_completa():
    sol = _sol_con_codigos("CREATI", paneles=("PAN_CLEAR",))
    n = asegurar_resultados_paneles_derivados(sol)
    assert n >= 3
    assert {"CREATI", "CREA_U", "DIUR", "CLEAR_CREA"} <= _codigos(sol)


@pytest.mark.django_db
def test_panel_iono_u24_explicito_si_completa():
    sol = _sol_con_codigos("NA_U", paneles=("PAN_IONO_U24",))
    n = asegurar_resultados_paneles_derivados(sol)
    assert n >= 1
    assert {"NA_U", "K_U", "CL_U", "DIUR", "NA_U24", "K_U24", "CL_U24"} <= _codigos(sol)


@pytest.mark.django_db
def test_panel_malb24_explicito_si_completa():
    sol = _sol_con_codigos("MICROALB", paneles=("PAN_MALB24",))
    n = asegurar_resultados_paneles_derivados(sol)
    assert n >= 2
    assert {"MICROALB", "DIUR", "MICROALB_24"} <= _codigos(sol)
