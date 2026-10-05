"""Auditoría de expansión fantasma de paneles (solo lectura)."""
from io import StringIO

import pytest
from django.core.management import call_command

from laboratorio.audit_paneles_fantasma import auditar_por_numeros, auditar_solicitud
from laboratorio.models import PanelExamen, ResultadoExamen, SolicitudExamen, TipoExamen
from pacientes.models import Paciente


def _sol_con(*codigos: str, paneles: tuple[str, ...] = (), numero: str = "LAB-TEST-FAN") -> SolicitudExamen:
    call_command("seed_catalogo_solicitud_papel", stdout=StringIO())
    paciente = Paciente.objects.create(
        dni=f"AUD-{numero[-8:]}",
        nombre="Audit",
        apellido="Fantasma",
    )
    sol = SolicitudExamen.objects.create(
        paciente=paciente,
        estado="EN_PROCESO",
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


@pytest.mark.django_db
def test_iono_azar_con_firmas_24hs_detecta_candidatos():
    sol = _sol_con(
        "NA_U",
        "K_U",
        "CL_U",
        "DIUR",
        "NA_U24",
        "K_U24",
        "CL_U24",
        paneles=("PAN_IONO_U",),
        numero="LAB-2026-00901",
    )
    inf = auditar_solicitud(sol)
    assert inf.hallazgo
    assert any(s.panel == "PAN_IONO_U24" for s in inf.sospechas)
    por = {f.codigo: f.clasificacion for f in inf.filas}
    assert por["NA_U"] == "justificado"
    assert por["NA_U24"] == "candidato_borrar"
    assert por["DIUR"] == "compartido_revisar"


@pytest.mark.django_db
def test_clearance_explicito_no_es_fantasma():
    sol = _sol_con(
        "CREATI",
        "CREA_U",
        "DIUR",
        "CLEAR_CREA",
        paneles=("PAN_CLEAR",),
        numero="LAB-2026-00902",
    )
    inf = auditar_solicitud(sol)
    assert not inf.hallazgo
    assert all(f.clasificacion == "justificado" for f in inf.filas)


@pytest.mark.django_db
def test_creatinina_con_clear_crea_fantasma():
    sol = _sol_con(
        "CREATI",
        "CREA_U",
        "DIUR",
        "CLEAR_CREA",
        paneles=(),
        numero="LAB-2026-00903",
    )
    # Sin panel M2M: CREATI suelta + firma CLEAR_CREA
    inf = auditar_solicitud(sol)
    assert inf.hallazgo
    por = {f.codigo: f.clasificacion for f in inf.filas}
    assert por["CLEAR_CREA"] == "candidato_borrar"
    # CREATI no es firma; queda como pedido suelto (justificado heurístico)
    assert por["CREATI"] == "justificado"
    assert por["DIUR"] == "compartido_revisar"


@pytest.mark.django_db
def test_firma_con_valor_va_a_revisar_manual():
    sol = _sol_con("NA_U", "NA_U24", paneles=("PAN_IONO_U",), numero="LAB-2026-00904")
    r = ResultadoExamen.objects.get(solicitud=sol, tipo_examen__codigo="NA_U24")
    r.valor_obtenido = "12.5"
    r.save(update_fields=["valor_obtenido"])
    inf = auditar_solicitud(sol)
    por = {f.codigo: f.clasificacion for f in inf.filas}
    assert por["NA_U24"] == "revisar_manual"


@pytest.mark.django_db
def test_no_calculable_cuenta_como_candidato_borrar():
    from laboratorio.calculos_derivados import RESULTADO_NO_CALCULABLE

    sol = _sol_con("NA_U", "NA_U24", paneles=("PAN_IONO_U",), numero="LAB-2026-00905")
    r = ResultadoExamen.objects.get(solicitud=sol, tipo_examen__codigo="NA_U24")
    r.valor_obtenido = RESULTADO_NO_CALCULABLE
    r.save(update_fields=["valor_obtenido"])
    inf = auditar_solicitud(sol)
    por = {f.codigo: f.clasificacion for f in inf.filas}
    assert por["NA_U24"] == "candidato_borrar"


@pytest.mark.django_db
def test_comando_numeros_default_y_faltante():
    _sol_con("NA_U", "NA_U24", paneles=("PAN_IONO_U",), numero="LAB-2026-00107")
    out = StringIO()
    call_command(
        "audit_paneles_fantasma_expansion",
        "--numeros",
        "LAB-2026-00107",
        "LAB-2026-00199",
        stdout=out,
    )
    text = out.getvalue()
    assert "LAB-2026-00107" in text
    assert "HALLAZGO" in text
    assert "NO ENCONTRADA" in text
    assert "candidato_borrar" in text


@pytest.mark.django_db
def test_auditar_por_numeros_preserva_orden():
    _sol_con("MICROALB", "MICROALB_24", paneles=("PAN_MALB_AZ",), numero="LAB-B")
    _sol_con("MICROALB", paneles=("PAN_MALB_AZ",), numero="LAB-A")
    infos = auditar_por_numeros(["LAB-B", "LAB-A", "LAB-Z"])
    assert [i.numero for i in infos] == ["LAB-B", "LAB-A", "LAB-Z"]
    assert infos[0].hallazgo
    assert not infos[1].hallazgo
    assert infos[2].estado == "NO_ENCONTRADA"
