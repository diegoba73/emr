"""
Tests modelo ResultadoExamen ↔ Muestra (LIMS Fase B2).
"""
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra
from laboratorio.muestra_estado import aplicar_recibir, aplicar_tomar, crear_muestra
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente


@pytest.mark.django_db
class TestResultadoExamenMuestra:
    @pytest.fixture
    def base(self):
        suf = uuid.uuid4().hex[:8]
        pac = Paciente.objects.create(
            dni=str(uuid.uuid4().int)[:8], nombre="Juan", apellido="P"
        )
        esp = Especialidad.objects.create(nombre=f"E{suf}")
        med = Medico.objects.create(
            nombre="Dr", apellido="X", matricula=f"M{suf}", especialidad=esp
        )
        tm = TipoMuestra.objects.create(
            codigo=f"TM{suf}", nombre="Sangre", activo=True
        )
        te = TipoExamen.objects.create(
            codigo=f"GLU{suf}",
            nombre="Glucosa",
            tipo_muestra_requerida=tm,
            precio=1,
            activo=True,
        )
        sol = SolicitudExamen.objects.create(
            paciente=pac,
            medico_interno=med,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol.tipos_examen.add(te)
        sol_otra = SolicitudExamen.objects.create(
            paciente=pac,
            medico_interno=med,
            origen_solicitud="EMR",
            estado="EN_PROCESO",
        )
        sol_otra.tipos_examen.add(te)
        return {
            "pac": pac,
            "tm": tm,
            "te": te,
            "sol": sol,
            "sol_otra": sol_otra,
        }

    def test_resultado_sin_muestra_ok(self, base):
        r = ResultadoExamen.objects.create(
            solicitud=base["sol"],
            tipo_examen=base["te"],
            valor_obtenido="10",
        )
        assert r.muestra_id is None

    def test_asociar_muestra_misma_solicitud_ok(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        r = ResultadoExamen.objects.create(
            solicitud=base["sol"],
            tipo_examen=base["te"],
            valor_obtenido="10",
            muestra=m,
        )
        assert r.muestra_id == m.pk

    def test_falla_muestra_otra_solicitud(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        with pytest.raises(ValidationError):
            ResultadoExamen(
                solicitud=base["sol_otra"],
                tipo_examen=base["te"],
                valor_obtenido="10",
                muestra=m,
            ).save()

    def test_falla_muestra_rechazada(self, base):
        from laboratorio.muestra_estado import aplicar_rechazar

        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_rechazar(
            m.pk, actor=None, view="t", motivo_rechazo="Hemólisis"
        )
        m.refresh_from_db()
        with pytest.raises(ValidationError):
            ResultadoExamen(
                solicitud=base["sol"],
                tipo_examen=base["te"],
                valor_obtenido="10",
                muestra=m,
            ).save()

    def test_falla_muestra_descartada(self, base):
        from laboratorio.muestra_estado import aplicar_descartar

        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        aplicar_descartar(m.pk, actor=None, view="t")
        m.refresh_from_db()
        with pytest.raises(ValidationError):
            ResultadoExamen(
                solicitud=base["sol"],
                tipo_examen=base["te"],
                valor_obtenido="10",
                muestra=m,
            ).save()

    def test_falla_muestra_cancelada(self, base):
        from laboratorio.muestra_estado import aplicar_cancelar

        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_cancelar(m.pk, actor=None, view="t", motivo="Pedido")
        m.refresh_from_db()
        with pytest.raises(ValidationError):
            ResultadoExamen(
                solicitud=base["sol"],
                tipo_examen=base["te"],
                valor_obtenido="10",
                muestra=m,
            ).save()

    def test_no_rechazar_muestra_con_resultados(self, base):
        from laboratorio.muestra_estado import MuestraAccionError, aplicar_rechazar

        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        ResultadoExamen.objects.create(
            solicitud=base["sol"],
            tipo_examen=base["te"],
            valor_obtenido="10",
            muestra=m,
        )
        with pytest.raises(MuestraAccionError):
            aplicar_rechazar(m.pk, actor=None, view="t", motivo_rechazo="x")

    def test_protect_no_borrar_muestra_con_resultado(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        aplicar_recibir(m.pk, actor=None, view="t")
        ResultadoExamen.objects.create(
            solicitud=base["sol"],
            tipo_examen=base["te"],
            valor_obtenido="10",
            muestra=m,
        )
        with pytest.raises(IntegrityError):
            m.delete()

    def test_tipo_examen_requiere_muestra_configurable(self, base):
        te = base["te"]
        assert te.requiere_muestra is False
        te.requiere_muestra = True
        te.save(update_fields=["requiere_muestra"])
        te.refresh_from_db()
        assert te.requiere_muestra is True
        assert te.tipo_muestra_requerida_id == base["tm"].pk
