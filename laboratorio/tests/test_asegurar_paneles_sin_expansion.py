"""Regresión: no expandir paneles por componentes compartidos sin panel explícito."""
from io import StringIO

import pytest
from django.core.management import call_command

from laboratorio.hemograma_resultados import asegurar_resultados_paneles_derivados
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from pacientes.models import Paciente


def _sol_con_codigos(*codigos: str, paneles: tuple[str, ...] = ()) -> SolicitudExamen:
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni=f"NOEXP-{'-'.join(codigos)[:20]}",
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
def test_creatininemia_sola_no_trae_clearance():
    sol = _sol_con_codigos("CREATI")
    assert asegurar_resultados_paneles_derivados(sol) == 0
    assert _codigos(sol) == {"CREATI"}


@pytest.mark.django_db
def test_ionograma_orina_azar_no_trae_24hs():
    """PAN_IONO_U (NA_U/K_U/CL_U) no debe expandir PAN_IONO_U24."""
    sol = _sol_con_codigos("NA_U", "K_U", "CL_U", paneles=("PAN_IONO_U",))
    assert asegurar_resultados_paneles_derivados(sol) == 0
    assert _codigos(sol) == {"NA_U", "K_U", "CL_U"}
    assert "NA_U24" not in _codigos(sol)
    assert "DIUR" not in _codigos(sol)


@pytest.mark.django_db
def test_na_u_suelto_no_trae_ionograma_24hs():
    sol = _sol_con_codigos("NA_U")
    assert asegurar_resultados_paneles_derivados(sol) == 0
    assert _codigos(sol) == {"NA_U"}


@pytest.mark.django_db
def test_microalbuminuria_azar_no_trae_24hs():
    sol = _sol_con_codigos("MICROALB", "CREA_U", paneles=("PAN_MALB_AZ",))
    assert asegurar_resultados_paneles_derivados(sol) == 0
    assert _codigos(sol) == {"MICROALB", "CREA_U"}
    assert "MICROALB_24" not in _codigos(sol)
    assert "DIUR" not in _codigos(sol)
    # CREA_U tampoco debe arrastrar clearance
    assert "CLEAR_CREA" not in _codigos(sol)


@pytest.mark.django_db
def test_microalb_suelta_no_trae_malb24():
    sol = _sol_con_codigos("MICROALB")
    assert asegurar_resultados_paneles_derivados(sol) == 0
    assert _codigos(sol) == {"MICROALB"}


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
