"""
Tests de modelos y servicio de muestras (LIMS Fase B0/B1).
"""
import uuid

import pytest
from django.core.exceptions import ValidationError

from laboratorio.models import SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import (
    AreaLaboratorio,
    EventoMuestra,
    Muestra,
    SeccionLaboratorio,
    TipoContenedor,
)
from laboratorio.muestra_estado import (
    MuestraAccionError,
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


@pytest.mark.django_db
class TestCatalogosB0:
    def test_area_laboratorio_codigo_unico(self):
        AreaLaboratorio.objects.create(codigo="CLIN", nombre="Clínica", activo=True)
        with pytest.raises(Exception):  # IntegrityError
            AreaLaboratorio.objects.create(codigo="CLIN", nombre="Otro nombre", activo=True)

    def test_seccion_unique_por_area(self):
        a1 = AreaLaboratorio.objects.create(codigo="A1", nombre="Área 1", activo=True)
        a2 = AreaLaboratorio.objects.create(codigo="A2", nombre="Área 2", activo=True)
        SeccionLaboratorio.objects.create(area=a1, codigo="HEM", nombre="Hema", activo=True)
        SeccionLaboratorio.objects.create(area=a2, codigo="HEM", nombre="Hema 2", activo=True)
        with pytest.raises(Exception):
            SeccionLaboratorio.objects.create(area=a1, codigo="HEM", nombre="Dup", activo=True)

    def test_tipo_contenedor(self):
        TipoContenedor.objects.create(codigo="EDTA", nombre="Tubo EDTA", activo=True)


@pytest.mark.django_db
class TestMuestraModeloYServicio:
    @pytest.fixture
    def base(self):
        suf = uuid.uuid4().hex[:8]
        pac = Paciente.objects.create(dni=str(uuid.uuid4().int)[:8], nombre="Ana", apellido="Test")
        esp = Especialidad.objects.create(nombre=f"Esp {suf}")
        med = Medico.objects.create(nombre="Dr", apellido="X", matricula=f"M{suf}", especialidad=esp)
        tm = TipoMuestra.objects.create(codigo=f"TM{suf}", nombre="Sangre", activo=True)
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
            estado="PENDIENTE",
        )
        sol.tipos_examen.add(te)
        return {"pac": pac, "med": med, "tm": tm, "sol": sol}

    def test_crear_muestra_codigo_barra_y_evento(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        assert m.codigo_barra
        assert m.codigo_barra.startswith("MUE-")
        assert m.estado == "PENDIENTE_TOMA"
        assert m.paciente_id == base["sol"].paciente_id
        assert EventoMuestra.objects.filter(muestra=m, accion="CREADA").exists()

    def test_paciente_debe_coincidir_con_solicitud(self, base):
        otro = Paciente.objects.create(dni=str(uuid.uuid4().int)[-8:], nombre="Otro", apellido="P")
        m = Muestra(
            solicitud=base["sol"],
            paciente=otro,
            tipo_muestra=base["tm"],
            estado="PENDIENTE_TOMA",
        )
        with pytest.raises(ValidationError):
            m.full_clean()

    def test_rechazar_exige_motivo(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        with pytest.raises(MuestraAccionError):
            aplicar_rechazar(m.pk, actor=None, view="t", motivo_rechazo="   ")

    def test_no_recibir_rechazada(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_rechazar(m.pk, actor=None, view="t", motivo_rechazo="Hemólisis")
        with pytest.raises(MuestraAccionError):
            aplicar_recibir(m.pk, actor=None, view="t")

    def test_no_procesar_cancelada(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_cancelar(m.pk, actor=None, view="t", motivo="x")
        with pytest.raises(MuestraAccionError):
            aplicar_conservar(m.pk, actor=None, view="t")

    def test_flujo_tomar_recibir_conservar_descartar(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        aplicar_tomar(m.pk, actor=None, view="t")
        m.refresh_from_db()
        assert m.estado == "TOMADA"
        aplicar_recibir(m.pk, actor=None, view="t", ubicacion_actual="Rack 1")
        m.refresh_from_db()
        assert m.estado == "RECIBIDA"
        aplicar_conservar(m.pk, actor=None, view="t", ubicacion_actual="Heladera")
        m.refresh_from_db()
        assert m.estado == "CONSERVADA"
        aplicar_descartar(m.pk, actor=None, view="t")
        m.refresh_from_db()
        assert m.estado == "DESCARTADA"
        assert EventoMuestra.objects.filter(muestra_id=m.pk).count() >= 5

    def test_tomar_coordina_solicitud_pendiente(self, base):
        m = crear_muestra(
            solicitud=base["sol"],
            tipo_muestra_id=base["tm"].pk,
            tipo_contenedor_id=None,
            observaciones="",
            actor=None,
            view="test",
        )
        assert base["sol"].estado == "PENDIENTE"
        aplicar_tomar(m.pk, actor=None, view="test_tomar")
        base["sol"].refresh_from_db()
        assert base["sol"].estado == "TOMA_MUESTRA"
