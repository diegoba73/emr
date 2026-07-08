"""
Tests de modelos — LIMS Fase B3.1 (Microbiología base).
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from laboratorio.microbiologia_estado import (
    MicrobiologiaAccionError,
    actualizar_informe_borrador,
    aplicar_completar_antibiograma,
    aplicar_emitir_informe,
    aplicar_marcar_estudio_informado,
    aplicar_validar_informe_final,
    crear_antibiograma,
    crear_informe_borrador,
    crear_identificacion,
    crear_resultado_antibiotico,
)
from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
from laboratorio.models_microbiologia import (
    AisladoMicrobiologico,
    Antibiograma,
    Antibiotico,
    EstudioMicrobiologia,
    IdentificacionMicroorganismo,
    InformeMicrobiologia,
    LecturaCultivo,
    MedioCultivo,
    Microorganismo,
    ResultadoAntibiotico,
    SiembraMicrobiologia,
)
from laboratorio.muestra_estado import (
    aplicar_cancelar,
    aplicar_conservar,
    aplicar_descartar,
    aplicar_rechazar,
    aplicar_recibir,
    aplicar_tomar,
    crear_muestra,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente

User = get_user_model()


@pytest.fixture
def base_data(db):
    suf = uuid.uuid4().hex[:8]
    tm = TipoMuestra.objects.create(codigo=f"TM{suf}", nombre="Sangre", activo=True)
    te = TipoExamen.objects.create(
        codigo=f"GLU{suf}",
        nombre="Glucosa",
        tipo_muestra_requerida=tm,
        precio=1,
        activo=True,
    )
    pac = Paciente.objects.create(dni=f"DNI{suf}", nombre="P", apellido="Test")
    esp = Especialidad.objects.create(nombre=f"Esp {suf}")
    med = Medico.objects.create(nombre="Dr", apellido="X", matricula=f"M{suf}", especialidad=esp)
    sol = SolicitudExamen.objects.create(
        paciente=pac,
        medico_interno=med,
        origen_solicitud="AMBULATORIO_CEHTA",
        estado="PENDIENTE",
    )
    sol.tipos_examen.add(te)
    return {"suf": suf, "tm": tm, "te": te, "pac": pac, "med": med, "sol": sol}


def _muestra_recibida(sol, tm):
    m = crear_muestra(
        solicitud=sol,
        tipo_muestra_id=tm.pk,
        tipo_contenedor_id=None,
        observaciones="",
        actor=None,
        view="t",
    )
    aplicar_tomar(m.pk, actor=None, view="t")
    aplicar_recibir(m.pk, actor=None, view="t")
    m.refresh_from_db()
    return m


def _muestra_conservada(sol, tm):
    m = _muestra_recibida(sol, tm)
    aplicar_conservar(m.pk, actor=None, view="t")
    m.refresh_from_db()
    assert m.estado == "CONSERVADA"
    return m


def _medio(activo=True, codigo_suf=""):
    return MedioCultivo.objects.create(
        codigo=f"AGS{codigo_suf or uuid.uuid4().hex[:6]}",
        nombre="Agar sangre",
        tipo="solido",
        activo=activo,
    )


@pytest.mark.django_db
class TestMedioCultivoModel:
    def test_crear_medio(self):
        m = _medio()
        assert m.pk is not None
        assert m.activo is True

    def test_codigo_unico(self):
        _medio(codigo_suf="UNIQ1")
        with pytest.raises(Exception):
            MedioCultivo.objects.create(codigo="AGSUNIQ1", nombre="Otro")


@pytest.mark.django_db
class TestEstudioMicrobiologiaModel:
    def test_crear_con_muestra_recibida(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        estudio = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"],
            muestra=m,
            paciente=base_data["pac"],
            tipo_estudio="CULTIVO_RUTINA",
        )
        assert estudio.estado == "PENDIENTE"
        assert estudio.numero and estudio.numero.startswith("MIC-")

    def test_crear_con_muestra_en_proceso(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        Muestra.objects.filter(pk=m.pk).update(estado="EN_PROCESO")
        m.refresh_from_db()
        e = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"],
            muestra=m,
            paciente=base_data["pac"],
            tipo_estudio="CULTIVO_RUTINA",
        )
        assert e.estado == "PENDIENTE"

    def test_estudio_microbiologia_permite_muestra_conservada(self, base_data):
        m = _muestra_conservada(base_data["sol"], base_data["tm"])
        estudio = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"],
            muestra=m,
            paciente=base_data["pac"],
            tipo_estudio="CULTIVO_RUTINA",
        )
        estudio.full_clean()
        assert estudio.estado == "PENDIENTE"

    def test_falla_muestra_pendiente_toma(self, base_data):
        m = crear_muestra(
            solicitud=base_data["sol"],
            tipo_muestra_id=base_data["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        assert m.estado == "PENDIENTE_TOMA"
        with pytest.raises(DjangoValidationError):
            EstudioMicrobiologia.objects.create(
                solicitud=base_data["sol"],
                muestra=m,
                paciente=base_data["pac"],
                tipo_estudio="CULTIVO_RUTINA",
            )

    def test_falla_muestra_tomada(self, base_data):
        m = crear_muestra(
            solicitud=base_data["sol"],
            tipo_muestra_id=base_data["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        m.refresh_from_db()
        with pytest.raises(DjangoValidationError):
            EstudioMicrobiologia.objects.create(
                solicitud=base_data["sol"],
                muestra=m,
                paciente=base_data["pac"],
            )

    def test_falla_muestra_rechazada(self, base_data):
        m = crear_muestra(
            solicitud=base_data["sol"],
            tipo_muestra_id=base_data["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        aplicar_rechazar(m.pk, actor=None, view="t", motivo_rechazo="x")
        m.refresh_from_db()
        with pytest.raises(DjangoValidationError):
            EstudioMicrobiologia.objects.create(
                solicitud=base_data["sol"],
                muestra=m,
                paciente=base_data["pac"],
            )

    def test_falla_muestra_descartada(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        aplicar_descartar(m.pk, actor=None, view="t")
        m.refresh_from_db()
        with pytest.raises(DjangoValidationError):
            EstudioMicrobiologia.objects.create(
                solicitud=base_data["sol"],
                muestra=m,
                paciente=base_data["pac"],
            )

    def test_falla_muestra_cancelada(self, base_data):
        m = crear_muestra(
            solicitud=base_data["sol"],
            tipo_muestra_id=base_data["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="t",
        )
        aplicar_cancelar(m.pk, actor=None, view="t", motivo="test")
        m.refresh_from_db()
        with pytest.raises(DjangoValidationError):
            EstudioMicrobiologia.objects.create(
                solicitud=base_data["sol"],
                muestra=m,
                paciente=base_data["pac"],
            )

    def test_falla_muestra_otra_solicitud(self, base_data):
        sol2 = SolicitudExamen.objects.create(
            paciente=base_data["pac"],
            medico_interno=base_data["med"],
            origen_solicitud="AMBULATORIO_CEHTA",
            estado="PENDIENTE",
        )
        m_otra = _muestra_recibida(sol2, base_data["tm"])
        with pytest.raises(DjangoValidationError):
            EstudioMicrobiologia.objects.create(
                solicitud=base_data["sol"],
                muestra=m_otra,
                paciente=base_data["pac"],
            )

    def test_falla_paciente_inconsistente(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        otro = Paciente.objects.create(dni=f"O{base_data['suf']}", nombre="O", apellido="X")
        with pytest.raises(DjangoValidationError):
            EstudioMicrobiologia.objects.create(
                solicitud=base_data["sol"],
                muestra=m,
                paciente=otro,
            )


@pytest.mark.django_db
class TestSiembraMicrobiologiaModel:
    def test_crear_con_medio_activo(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        e = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
        )
        medio = _medio()
        s = SiembraMicrobiologia.objects.create(estudio=e, muestra=m, medio=medio)
        assert s.estado == "SEMBRADA"

    def test_falla_medio_inactivo(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        e = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
        )
        medio = _medio(activo=False)
        with pytest.raises(DjangoValidationError):
            SiembraMicrobiologia.objects.create(estudio=e, muestra=m, medio=medio)

    def test_siembra_microbiologia_permite_muestra_conservada(self, base_data):
        m = _muestra_conservada(base_data["sol"], base_data["tm"])
        e = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
        )
        s = SiembraMicrobiologia.objects.create(estudio=e, muestra=m, medio=_medio())
        s.full_clean()
        assert s.estado == "SEMBRADA"

    def test_falla_si_muestra_distinta(self, base_data):
        m1 = _muestra_recibida(base_data["sol"], base_data["tm"])
        m2 = _muestra_recibida(base_data["sol"], base_data["tm"])
        e = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m1, paciente=base_data["pac"]
        )
        medio = _medio()
        with pytest.raises(DjangoValidationError):
            SiembraMicrobiologia.objects.create(estudio=e, muestra=m2, medio=medio)


@pytest.mark.django_db
class TestLecturaCultivoModel:
    def test_crear_lectura(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        e = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
        )
        medio = _medio()
        s = SiembraMicrobiologia.objects.create(estudio=e, muestra=m, medio=medio)
        lec = LecturaCultivo.objects.create(
            siembra=s, estudio=e, crecimiento="SIN_DESARROLLO"
        )
        assert lec.pk is not None

    def test_falla_lectura_siembra_de_otro_estudio(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        e1 = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
        )
        e2 = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
        )
        medio = _medio()
        s = SiembraMicrobiologia.objects.create(estudio=e1, muestra=m, medio=medio)
        with pytest.raises(DjangoValidationError):
            LecturaCultivo.objects.create(siembra=s, estudio=e2, crecimiento="SIN_DESARROLLO")

    def test_falla_fecha_anterior_a_siembra(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        e = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
        )
        medio = _medio()
        s = SiembraMicrobiologia.objects.create(estudio=e, muestra=m, medio=medio)
        with pytest.raises(DjangoValidationError):
            LecturaCultivo.objects.create(
                siembra=s,
                estudio=e,
                crecimiento="PENDIENTE",
                fecha_lectura=s.fecha_siembra - timedelta(hours=1),
            )

    def test_falla_si_estudio_cancelado(self, base_data):
        m = _muestra_recibida(base_data["sol"], base_data["tm"])
        e = EstudioMicrobiologia.objects.create(
            solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
        )
        medio = _medio()
        s = SiembraMicrobiologia.objects.create(estudio=e, muestra=m, medio=medio)
        EstudioMicrobiologia.objects.filter(pk=e.pk).update(estado="CANCELADO")
        e.refresh_from_db()
        with pytest.raises(DjangoValidationError):
            LecturaCultivo.objects.create(siembra=s, estudio=e, crecimiento="PENDIENTE")


# ---------------------------------------------------------------------------
# B3.2 — Microorganismos / Aislados / Identificación
# ---------------------------------------------------------------------------


def _setup_lectura(base_data):
    m = _muestra_recibida(base_data["sol"], base_data["tm"])
    estudio = EstudioMicrobiologia.objects.create(
        solicitud=base_data["sol"], muestra=m, paciente=base_data["pac"]
    )
    medio = _medio(codigo_suf=uuid.uuid4().hex[:6])
    siembra = SiembraMicrobiologia.objects.create(estudio=estudio, muestra=m, medio=medio)
    EstudioMicrobiologia.objects.filter(pk=estudio.pk).update(estado="SEMBRADO")
    estudio.refresh_from_db()
    lectura = LecturaCultivo.objects.create(siembra=siembra, estudio=estudio, crecimiento="MODERADO")
    return {"muestra": m, "estudio": estudio, "siembra": siembra, "lectura": lectura}


def _micro(activo=True, suf=""):
    return Microorganismo.objects.create(
        codigo=f"M{suf or uuid.uuid4().hex[:6]}",
        nombre="Escherichia coli",
        genero="Escherichia",
        especie="coli",
        activo=activo,
    )


@pytest.mark.django_db
class TestMicroorganismoModel:
    def test_crear(self):
        m = _micro(suf="A1")
        assert m.pk and m.activo

    def test_codigo_unico(self):
        _micro(suf="UNQ1")
        with pytest.raises(Exception):
            Microorganismo.objects.create(codigo="MUNQ1", nombre="otra")


@pytest.mark.django_db
class TestAisladoModel:
    def test_crear_desde_lectura(self, base_data):
        ctx = _setup_lectura(base_data)
        a = AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"],
            lectura_origen=ctx["lectura"],
        )
        assert a.estado == "SOSPECHADO"
        assert a.significancia == "NO_DEFINIDA"
        assert a.requiere_antibiograma is False

    def test_falla_lectura_de_otro_estudio(self, base_data):
        ctx1 = _setup_lectura(base_data)
        ctx2 = _setup_lectura(base_data)
        with pytest.raises(DjangoValidationError):
            AisladoMicrobiologico.objects.create(
                estudio=ctx1["estudio"],
                lectura_origen=ctx2["lectura"],
            )

    def test_falla_estudio_cancelado(self, base_data):
        ctx = _setup_lectura(base_data)
        EstudioMicrobiologia.objects.filter(pk=ctx["estudio"].pk).update(estado="CANCELADO")
        ctx["estudio"].refresh_from_db()
        with pytest.raises(DjangoValidationError):
            AisladoMicrobiologico.objects.create(
                estudio=ctx["estudio"], lectura_origen=ctx["lectura"]
            )

    def test_falla_microorganismo_inactivo(self, base_data):
        ctx = _setup_lectura(base_data)
        m = _micro(activo=False, suf="OFF")
        with pytest.raises(DjangoValidationError):
            AisladoMicrobiologico.objects.create(
                estudio=ctx["estudio"], lectura_origen=ctx["lectura"], microorganismo=m
            )

    def test_identificado_requiere_microorganismo(self, base_data):
        ctx = _setup_lectura(base_data)
        with pytest.raises(DjangoValidationError):
            AisladoMicrobiologico.objects.create(
                estudio=ctx["estudio"],
                lectura_origen=ctx["lectura"],
                estado="IDENTIFICADO",
            )

    def test_requiere_antibiograma_marca_pero_no_crea(self, base_data):
        ctx = _setup_lectura(base_data)
        a = AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"],
            lectura_origen=ctx["lectura"],
            requiere_antibiograma=True,
        )
        assert a.requiere_antibiograma is True
        # No existe modelo de antibiograma en B3.2: nada que asertar más allá del flag.


@pytest.mark.django_db
class TestIdentificacionModel:
    def test_crear_identificacion(self, base_data):
        ctx = _setup_lectura(base_data)
        a = AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"], lectura_origen=ctx["lectura"]
        )
        m = _micro(suf="ID1")
        idn = IdentificacionMicroorganismo.objects.create(aislado=a, microorganismo=m)
        assert idn.pk is not None

    def test_falla_microorganismo_inactivo(self, base_data):
        ctx = _setup_lectura(base_data)
        a = AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"], lectura_origen=ctx["lectura"]
        )
        m = _micro(activo=False, suf="ID2")
        with pytest.raises(DjangoValidationError):
            IdentificacionMicroorganismo.objects.create(aislado=a, microorganismo=m)

    def test_falla_aislado_descartado(self, base_data):
        ctx = _setup_lectura(base_data)
        a = AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"], lectura_origen=ctx["lectura"]
        )
        AisladoMicrobiologico.objects.filter(pk=a.pk).update(estado="DESCARTADO")
        a.refresh_from_db()
        m = _micro(suf="ID3")
        with pytest.raises(DjangoValidationError):
            IdentificacionMicroorganismo.objects.create(aislado=a, microorganismo=m)

    def test_servicio_actualiza_aislado_y_estudio(self, base_data):
        ctx = _setup_lectura(base_data)
        a = AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"], lectura_origen=ctx["lectura"]
        )
        m = _micro(suf="ID4")
        crear_identificacion(
            aislado_id=a.pk,
            microorganismo_id=m.pk,
            metodo="MALDI-TOF",
            resultado="E. coli",
            confianza=98.5,
            observaciones="",
            actor=None,
            view="t",
        )
        a.refresh_from_db()
        ctx["estudio"].refresh_from_db()
        assert a.estado == "IDENTIFICADO"
        assert a.microorganismo_id == m.pk
        assert ctx["estudio"].estado == "IDENTIFICACION"


# ---------------------------------------------------------------------------
# B3.3 — Antibiótico / Antibiograma / ResultadoAntibiotico
# ---------------------------------------------------------------------------


def _aislado_identificado(base_data, suf=""):
    ctx = _setup_lectura(base_data)
    a = AisladoMicrobiologico.objects.create(
        estudio=ctx["estudio"], lectura_origen=ctx["lectura"]
    )
    m = _micro(suf=suf or uuid.uuid4().hex[:6])
    crear_identificacion(
        aislado_id=a.pk,
        microorganismo_id=m.pk,
        metodo="MALDI-TOF",
        resultado="E. coli",
        confianza=99,
        observaciones="",
        actor=None,
        view="t",
    )
    a.refresh_from_db()
    ctx["aislado"] = a
    ctx["microorganismo"] = m
    return ctx


def _ab(activo=True, suf=""):
    return Antibiotico.objects.create(
        codigo=f"AB{suf or uuid.uuid4().hex[:6]}",
        nombre="Ampicilina",
        familia="betalactamicos",
        activo=activo,
    )


@pytest.mark.django_db
class TestAntibioticoModel:
    def test_crear(self):
        a = _ab(suf="A1")
        assert a.pk and a.activo

    def test_codigo_unico(self):
        _ab(suf="UNQ")
        with pytest.raises(Exception):
            Antibiotico.objects.create(codigo="ABUNQ", nombre="Otro")


@pytest.mark.django_db
class TestAntibiogramaModel:
    def test_crear_para_aislado_identificado(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = Antibiograma.objects.create(aislado=ctx["aislado"])
        assert ag.estado == "PENDIENTE"

    def test_falla_aislado_sospechado(self, base_data):
        ctx = _setup_lectura(base_data)
        a = AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"], lectura_origen=ctx["lectura"]
        )
        with pytest.raises(DjangoValidationError):
            Antibiograma.objects.create(aislado=a)

    def test_falla_aislado_descartado(self, base_data):
        ctx = _aislado_identificado(base_data)
        AisladoMicrobiologico.objects.filter(pk=ctx["aislado"].pk).update(estado="DESCARTADO")
        ctx["aislado"].refresh_from_db()
        with pytest.raises(DjangoValidationError):
            Antibiograma.objects.create(aislado=ctx["aislado"])

    def test_falla_estudio_cancelado(self, base_data):
        ctx = _aislado_identificado(base_data)
        EstudioMicrobiologia.objects.filter(pk=ctx["estudio"].pk).update(estado="CANCELADO")
        ctx["aislado"].estudio.refresh_from_db()
        with pytest.raises(DjangoValidationError):
            Antibiograma.objects.create(aislado=ctx["aislado"])


@pytest.mark.django_db
class TestResultadoAntibioticoModel:
    def test_crear_resultado(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = Antibiograma.objects.create(aislado=ctx["aislado"])
        r = ResultadoAntibiotico.objects.create(
            antibiograma=ag, antibiotico=_ab(), interpretacion="S"
        )
        assert r.pk is not None

    def test_falla_antibiotico_inactivo(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = Antibiograma.objects.create(aislado=ctx["aislado"])
        with pytest.raises(DjangoValidationError):
            ResultadoAntibiotico.objects.create(
                antibiograma=ag, antibiotico=_ab(activo=False), interpretacion="S"
            )

    def test_falla_duplicar_antibiotico(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = Antibiograma.objects.create(aislado=ctx["aislado"])
        ab = _ab(suf="DUP")
        ResultadoAntibiotico.objects.create(antibiograma=ag, antibiotico=ab, interpretacion="S")
        with pytest.raises(Exception):
            ResultadoAntibiotico.objects.create(antibiograma=ag, antibiotico=ab, interpretacion="R")

    def test_falla_interpretacion_invalida(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = Antibiograma.objects.create(aislado=ctx["aislado"])
        with pytest.raises(DjangoValidationError):
            ResultadoAntibiotico.objects.create(
                antibiograma=ag, antibiotico=_ab(), interpretacion="ZZZ"
            )

    def test_falla_si_antibiograma_completo(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = Antibiograma.objects.create(aislado=ctx["aislado"])
        Antibiograma.objects.filter(pk=ag.pk).update(estado="COMPLETO")
        ag.refresh_from_db()
        with pytest.raises(DjangoValidationError):
            ResultadoAntibiotico.objects.create(antibiograma=ag, antibiotico=_ab(), interpretacion="S")

    def test_falla_si_antibiograma_cancelado(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = Antibiograma.objects.create(aislado=ctx["aislado"])
        Antibiograma.objects.filter(pk=ag.pk).update(estado="CANCELADO")
        ag.refresh_from_db()
        with pytest.raises(DjangoValidationError):
            ResultadoAntibiotico.objects.create(antibiograma=ag, antibiotico=_ab(), interpretacion="S")


@pytest.mark.django_db
class TestServiciosAntibiograma:
    def test_completar_sin_resultados_falla(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = crear_antibiograma(
            aislado_id=ctx["aislado"].pk,
            metodo="Disco",
            observaciones="",
            actor=None,
            view="t",
        )
        from laboratorio.microbiologia_estado import MicrobiologiaAccionError
        with pytest.raises(MicrobiologiaAccionError):
            aplicar_completar_antibiograma(ag.pk, actor=None, view="t")

    def test_completar_con_resultados_funciona_y_setea_fecha(self, base_data):
        ctx = _aislado_identificado(base_data)
        ag = crear_antibiograma(
            aislado_id=ctx["aislado"].pk,
            metodo="Disco",
            observaciones="",
            actor=None,
            view="t",
        )
        crear_resultado_antibiotico(
            antibiograma_id=ag.pk,
            antibiotico_id=_ab().pk,
            halo_mm=20,
            mic="",
            interpretacion="S",
            observaciones="",
            actor=None,
            view="t",
        )
        ag2 = aplicar_completar_antibiograma(ag.pk, actor=None, view="t")
        assert ag2.estado == "COMPLETO"
        assert ag2.fecha_resultado is not None

    def test_primer_resultado_pasa_a_en_proceso_y_estudio_a_antibiograma(self, base_data):
        ctx = _aislado_identificado(base_data)
        # Aseguramos que el estudio está en IDENTIFICACION (lo dejó la identificación).
        ctx["estudio"].refresh_from_db()
        assert ctx["estudio"].estado == "IDENTIFICACION"
        ag = crear_antibiograma(
            aislado_id=ctx["aislado"].pk,
            metodo="Disco",
            observaciones="",
            actor=None,
            view="t",
        )
        ctx["estudio"].refresh_from_db()
        assert ctx["estudio"].estado == "ANTIBIOGRAMA"
        crear_resultado_antibiotico(
            antibiograma_id=ag.pk,
            antibiotico_id=_ab().pk,
            halo_mm=18,
            mic="",
            interpretacion="R",
            observaciones="",
            actor=None,
            view="t",
        )
        ag.refresh_from_db()
        assert ag.estado == "EN_PROCESO"


# ---------------------------------------------------------------------------
# B3.4 — Informes microbiológicos
# ---------------------------------------------------------------------------


def _estudio_con_lectura_sin_aislados(base_data):
    m = _muestra_recibida(base_data["sol"], base_data["tm"])
    medio = _medio()
    e = EstudioMicrobiologia.objects.create(
        solicitud=base_data["sol"],
        muestra=m,
        paciente=base_data["pac"],
        tipo_estudio="CULTIVO_RUTINA",
    )
    s = SiembraMicrobiologia.objects.create(estudio=e, muestra=m, medio=medio)
    EstudioMicrobiologia.objects.filter(pk=e.pk).update(estado="SEMBRADO")
    e.refresh_from_db()
    lec = LecturaCultivo.objects.create(siembra=s, estudio=e, crecimiento="SIN_DESARROLLO")
    return {"estudio": e, "lectura": lec, "siembra": s, "muestra": m}


@pytest.mark.django_db
class TestInformeMicrobiologiaModel:
    def test_varios_preliminares(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        i1 = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="PRELIMINAR",
            texto="p1",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        i2 = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="PRELIMINAR",
            texto="p2",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        assert i1.pk != i2.pk

    def test_preliminar_emitido_no_mueve_estudio(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        EstudioMicrobiologia.objects.filter(pk=ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        ctx["estudio"].refresh_from_db()
        inf = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="PRELIMINAR",
            texto="borrador",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        aplicar_emitir_informe(inf.pk, actor=None, view="t", texto="Preliminar emitido.")
        ctx["estudio"].refresh_from_db()
        assert ctx["estudio"].estado == "ANTIBIOGRAMA"

    def test_final_emitido_pasa_a_listo_para_validar(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        EstudioMicrobiologia.objects.filter(pk=ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        ctx["estudio"].refresh_from_db()
        inf = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="FINAL",
            texto="borrador final",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        aplicar_emitir_informe(inf.pk, actor=None, view="t", texto="Cultivo sin desarrollo.")
        ctx["estudio"].refresh_from_db()
        assert ctx["estudio"].estado == "LISTO_PARA_VALIDAR"
        inf.refresh_from_db()
        assert inf.estado == "EMITIDO"

    def test_validar_pasa_estudio_a_validado(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        EstudioMicrobiologia.objects.filter(pk=ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        inf = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="FINAL",
            texto="x",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        aplicar_emitir_informe(inf.pk, actor=None, view="t", texto="Informe final.")
        aplicar_validar_informe_final(inf.pk, actor=None, view="t")
        ctx["estudio"].refresh_from_db()
        inf.refresh_from_db()
        assert ctx["estudio"].estado == "VALIDADO"
        assert inf.estado == "VALIDADO"

    def test_marcar_informado(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        EstudioMicrobiologia.objects.filter(pk=ctx["estudio"].pk).update(estado="ANTIBIOGRAMA")
        inf = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="FINAL",
            texto="x",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        aplicar_emitir_informe(inf.pk, actor=None, view="t", texto="Final.")
        aplicar_validar_informe_final(inf.pk, actor=None, view="t")
        aplicar_marcar_estudio_informado(ctx["estudio"].pk, actor=None, view="t")
        ctx["estudio"].refresh_from_db()
        assert ctx["estudio"].estado == "INFORMADO"

    def test_segundo_final_vigente_falla(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="FINAL",
            texto="a",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        with pytest.raises(MicrobiologiaAccionError):
            crear_informe_borrador(
                estudio_id=ctx["estudio"].pk,
                tipo="FINAL",
                texto="b",
                observaciones="",
                reemplaza_a_id=None,
                actor=None,
                view="t",
            )

    def test_emitir_final_texto_vacio_falla(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        inf = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="FINAL",
            texto="",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        with pytest.raises(MicrobiologiaAccionError):
            aplicar_emitir_informe(inf.pk, actor=None, view="t", texto="   ")

    def test_final_bloqueado_aislado_sospechoso_significativo(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"],
            lectura_origen=ctx["lectura"],
            estado="SOSPECHADO",
            significancia="SIGNIFICATIVO",
        )
        with pytest.raises(MicrobiologiaAccionError):
            crear_informe_borrador(
                estudio_id=ctx["estudio"].pk,
                tipo="FINAL",
                texto="x",
                observaciones="",
                reemplaza_a_id=None,
                actor=None,
                view="t",
            )

    def test_final_permite_flora_sospechoso(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        AisladoMicrobiologico.objects.create(
            estudio=ctx["estudio"],
            lectura_origen=ctx["lectura"],
            estado="SOSPECHADO",
            significancia="FLORA_HABITUAL",
        )
        inf = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="FINAL",
            texto="x",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        aplicar_emitir_informe(inf.pk, actor=None, view="t", texto="Flora habitual, sin patógenos.")
        inf.refresh_from_db()
        assert inf.estado == "EMITIDO"

    def test_final_requiere_antibiograma_completo(self, base_data):
        ctx = _aislado_identificado(base_data)
        AisladoMicrobiologico.objects.filter(pk=ctx["aislado"].pk).update(requiere_antibiograma=True)
        ctx["aislado"].refresh_from_db()
        with pytest.raises(MicrobiologiaAccionError):
            crear_informe_borrador(
                estudio_id=ctx["estudio"].pk,
                tipo="FINAL",
                texto="x",
                observaciones="",
                reemplaza_a_id=None,
                actor=None,
                view="t",
            )

    def test_final_con_antibiograma_completo(self, base_data):
        ctx = _aislado_identificado(base_data)
        AisladoMicrobiologico.objects.filter(pk=ctx["aislado"].pk).update(requiere_antibiograma=True)
        ctx["aislado"].refresh_from_db()
        ag = crear_antibiograma(
            aislado_id=ctx["aislado"].pk,
            metodo="D",
            observaciones="",
            actor=None,
            view="t",
        )
        crear_resultado_antibiotico(
            antibiograma_id=ag.pk,
            antibiotico_id=_ab().pk,
            halo_mm=15,
            mic="",
            interpretacion="S",
            observaciones="",
            actor=None,
            view="t",
        )
        aplicar_completar_antibiograma(ag.pk, actor=None, view="t")
        inf = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="FINAL",
            texto="x",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        aplicar_emitir_informe(inf.pk, actor=None, view="t", texto="Informe con antibiograma completo.")
        inf.refresh_from_db()
        assert inf.estado == "EMITIDO"

    def test_no_editar_borrador_tras_validado_por_otro_flujo(self, base_data):
        ctx = _estudio_con_lectura_sin_aislados(base_data)
        inf = crear_informe_borrador(
            estudio_id=ctx["estudio"].pk,
            tipo="FINAL",
            texto="x",
            observaciones="",
            reemplaza_a_id=None,
            actor=None,
            view="t",
        )
        aplicar_emitir_informe(inf.pk, actor=None, view="t", texto="Emitido.")
        aplicar_validar_informe_final(inf.pk, actor=None, view="t")
        with pytest.raises(MicrobiologiaAccionError):
            actualizar_informe_borrador(inf.pk, actor=None, view="t", texto="hack")
