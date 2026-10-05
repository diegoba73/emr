"""Reparación de orina fantasma: solo sin resultado; no toca sangre ni 00119."""
from io import StringIO

import pytest
from django.core.management import call_command

from laboratorio.calculos_derivados import RESULTADO_NO_CALCULABLE
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.reparar_orina_fantasma import (
    aplicar_plan,
    planificar_orden,
    planificar_por_numeros,
)
from pacientes.models import Paciente


def _sol(*codigos: str, paneles: tuple[str, ...] = (), numero: str = "LAB-REP-1") -> SolicitudExamen:
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni=f"REP-{numero[-6:]}",
        nombre="Rep",
        apellido="Orina",
    )
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="INFORMADO_PARCIAL",
        origen_solicitud="AMBULATORIO_CEHTA",
        numero=numero,
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
def test_borra_orina_vacia_y_no_calculable_conserva_sangre_y_creati():
    sol = _sol(
        "NA",
        "K",
        "CL",
        "CREATI",
        "NA_U",
        "NA_U24",
        "CLEAR_CREA",
        "DIUR",
        "CREA_U",
        paneles=("PAN_IONO",),
        numero="LAB-2026-00107",
    )
    ResultadoExamen.objects.filter(
        solicitud=sol, tipo_examen__codigo="NA_U24"
    ).update(valor_obtenido=RESULTADO_NO_CALCULABLE)
    ResultadoExamen.objects.filter(
        solicitud=sol, tipo_examen__codigo="CLEAR_CREA"
    ).update(valor_obtenido=RESULTADO_NO_CALCULABLE)
    ResultadoExamen.objects.filter(
        solicitud=sol, tipo_examen__codigo="NA"
    ).update(valor_obtenido="140")
    ResultadoExamen.objects.filter(
        solicitud=sol, tipo_examen__codigo="CREATI"
    ).update(valor_obtenido="0.9")

    plan = planificar_orden(sol)
    borrar = {a.codigo for a in plan.a_borrar}
    assert borrar == {"NA_U", "NA_U24", "CLEAR_CREA", "DIUR", "CREA_U"}

    stats = aplicar_plan([plan])
    assert stats["resultados_borrados"] == 5
    sol.refresh_from_db()
    assert _codigos(sol) == {"NA", "K", "CL", "CREATI"}
    assert sol.resultados.get(tipo_examen__codigo="NA").valor_obtenido == "140"
    assert sol.resultados.get(tipo_examen__codigo="CREATI").valor_obtenido == "0.9"


@pytest.mark.django_db
def test_conserva_orina_con_valor_real():
    sol = _sol("NA_U", "NA_U24", paneles=("PAN_IONO",), numero="LAB-2026-00109")
    ResultadoExamen.objects.filter(
        solicitud=sol, tipo_examen__codigo="NA_U"
    ).update(valor_obtenido="88")
    plan = planificar_orden(sol)
    por = {a.codigo: a.accion for a in plan.acciones if a.codigo in {"NA_U", "NA_U24"}}
    assert por["NA_U"] == "conservar_resultado"
    assert por["NA_U24"] == "borrar"
    aplicar_plan([plan])
    assert _codigos(sol) == {"NA_U"}


@pytest.mark.django_db
def test_comando_rechaza_00119_y_dry_run_no_borra():
    sol = _sol("NA_U24", "DIUR", paneles=("PAN_IONO",), numero="LAB-2026-00113")
    ResultadoExamen.objects.filter(
        solicitud=sol, tipo_examen__codigo="NA_U24"
    ).update(valor_obtenido=RESULTADO_NO_CALCULABLE)

    out = StringIO()
    call_command(
        "reparar_orina_fantasma_expansion",
        "--numeros",
        "LAB-2026-00119",
        stdout=out,
    )
    assert "excluida" in out.getvalue().lower()

    out2 = StringIO()
    call_command(
        "reparar_orina_fantasma_expansion",
        "--numeros",
        "LAB-2026-00113",
        stdout=out2,
    )
    text = out2.getvalue()
    assert "dry-run" in text.lower()
    assert "NA_U24" in text
    assert sol.resultados.filter(tipo_examen__codigo="NA_U24").exists()


@pytest.mark.django_db
def test_comando_apply():
    sol = _sol("MICROALB_24", "DIUR", paneles=("PAN_HEMO",), numero="LAB-2026-00116")
    ResultadoExamen.objects.filter(
        solicitud=sol, tipo_examen__codigo="MICROALB_24"
    ).update(valor_obtenido=RESULTADO_NO_CALCULABLE)
    call_command(
        "reparar_orina_fantasma_expansion",
        "--numeros",
        "LAB-2026-00116",
        "--apply",
        stdout=StringIO(),
    )
    assert not sol.resultados.filter(tipo_examen__codigo="MICROALB_24").exists()
    assert not sol.resultados.filter(tipo_examen__codigo="DIUR").exists()
    assert not sol.tipos_examen.filter(codigo="DIUR").exists()


@pytest.mark.django_db
def test_default_no_incluye_00119():
    planes = planificar_por_numeros(["LAB-2026-00119"])
    # El planificador acepta el número; el comando lo bloquea.
    assert planes[0].numero == "LAB-2026-00119"
    from laboratorio.reparar_orina_fantasma import numeros_default_reparacion

    assert "LAB-2026-00119" not in numeros_default_reparacion()
