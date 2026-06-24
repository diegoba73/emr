"""
Tests modelos B4.1 — resultados clínicos estructurados.
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen, TipoMuestra
from laboratorio.models_catalog import AreaLaboratorio, SeccionLaboratorio
from laboratorio.resultados_clinicos import (
    aplicar_carga_estructurada,
    aplicar_snapshots_desde_tipo_examen,
    calcular_es_critico,
    calcular_es_patologico,
)
from pacientes.models import Paciente


@pytest.mark.django_db
class TestTipoExamenClinico:
    @pytest.fixture
    def tipo_muestra(self):
        return TipoMuestra.objects.create(codigo="SNG-B41", nombre="Sangre", activo=True)

    def test_unidad_default_y_rango_valido(self, tipo_muestra):
        te = TipoExamen.objects.create(
            codigo="GLU-B41",
            nombre="Glucosa",
            tipo_muestra_requerida=tipo_muestra,
            tipo_resultado="NUMERICO",
            unidad_default="mg/dL",
            rango_min=Decimal("70"),
            rango_max=Decimal("110"),
            valor_critico_min=Decimal("40"),
            valor_critico_max=Decimal("400"),
            activo=True,
        )
        assert te.unidad_default == "mg/dL"
        te.full_clean()

    def test_rango_invalido_falla(self, tipo_muestra):
        te = TipoExamen(
            codigo="BAD-RNG",
            nombre="Bad",
            tipo_muestra_requerida=tipo_muestra,
            rango_min=Decimal("200"),
            rango_max=Decimal("100"),
        )
        with pytest.raises(ValidationError):
            te.full_clean()

    def test_critico_invalido_falla(self, tipo_muestra):
        te = TipoExamen(
            codigo="BAD-CRIT",
            nombre="Bad crit",
            tipo_muestra_requerida=tipo_muestra,
            valor_critico_min=Decimal("500"),
            valor_critico_max=Decimal("100"),
        )
        with pytest.raises(ValidationError):
            te.full_clean()

    def test_seccion_inactiva_falla(self, tipo_muestra):
        area = AreaLaboratorio.objects.create(codigo="HEM", nombre="Hematología")
        sec = SeccionLaboratorio.objects.create(
            area=area, codigo="HEM-GEN", nombre="General", activo=False
        )
        te = TipoExamen(
            codigo="SEC-INACT",
            nombre="Test",
            tipo_muestra_requerida=tipo_muestra,
            seccion=sec,
        )
        with pytest.raises(ValidationError):
            te.full_clean()


@pytest.mark.django_db
class TestResultadoExamenClinico:
    @pytest.fixture
    def setup(self):
        tm = TipoMuestra.objects.create(codigo="S-B41M", nombre="Sangre", activo=True)
        te = TipoExamen.objects.create(
            codigo="GLU-B41M",
            nombre="Glucosa",
            tipo_muestra_requerida=tm,
            tipo_resultado="NUMERICO",
            unidad_default="mg/dL",
            rango_min=Decimal("70"),
            rango_max=Decimal("110"),
            valor_critico_min=Decimal("40"),
            valor_critico_max=Decimal("400"),
            rango_referencia_texto="70-110 mg/dL",
            activo=True,
        )
        pac = Paciente.objects.create(dni="99887766", nombre="P", apellido="B41")
        sol = SolicitudExamen.objects.create(
            paciente=pac, origen_solicitud="EMR", estado="EN_PROCESO"
        )
        res = ResultadoExamen.objects.create(
            solicitud=sol, tipo_examen=te, valor_obtenido=""
        )
        return te, res

    def test_valor_textual_sin_numerico(self, setup):
        te, res = setup
        aplicar_carga_estructurada(res, te, {"valor": "Negativo"})
        res.save()
        res.refresh_from_db()
        assert res.valor_obtenido == "Negativo"
        assert res.valor_numerico is None

    def test_valor_numerico_y_snapshot(self, setup):
        te, res = setup
        aplicar_carga_estructurada(
            res, te, {"valor": "90", "valor_numerico": 90}
        )
        res.save()
        res.refresh_from_db()
        assert res.valor_numerico == Decimal("90")
        assert res.unidad == "mg/dL"
        assert res.rango_min_snapshot == Decimal("70")
        assert res.rango_max_snapshot == Decimal("110")
        assert "70" in res.rango_referencia_snapshot

    def test_patologico_fuera_de_rango(self, setup):
        te, res = setup
        aplicar_carga_estructurada(
            res, te, {"valor": "120", "valor_numerico": 120}
        )
        assert res.es_patologico is True
        assert calcular_es_patologico(Decimal("120"), Decimal("70"), Decimal("110")) is True

    def test_patologico_dentro_de_rango(self, setup):
        te, res = setup
        aplicar_carga_estructurada(
            res, te, {"valor": "90", "valor_numerico": 90}
        )
        assert res.es_patologico is False

    def test_critico_alto(self, setup):
        te, res = setup
        aplicar_carga_estructurada(
            res, te, {"valor": "500", "valor_numerico": 500}
        )
        assert res.es_critico is True
        assert calcular_es_critico(Decimal("500"), Decimal("40"), Decimal("400")) is True

    def test_audit_metadata_sin_valores_clinicos_crudos(self, setup):
        te, res = setup
        res.valor_obtenido = "88"
        res.valor_numerico = Decimal("88")
        audit = aplicar_carga_estructurada(
            res, te, {"valor": "145", "valor_numerico": 145}
        )
        for forbidden in (
            "valor_anterior",
            "valor_nuevo",
            "valor_numerico_anterior",
            "valor_numerico_nuevo",
            "unidad_anterior",
            "unidad_nueva",
        ):
            assert forbidden not in audit
        assert audit["valor_anterior_presente"] is True
        assert audit["valor_nuevo_presente"] is True
        assert audit["valor_numerico_anterior_presente"] is True
        assert audit["valor_numerico_nuevo_presente"] is True
        assert "145" not in str(audit)
        assert "88" not in str(audit)

    def test_pendiente_si_valor_obtenido_vacio(self, setup):
        te, res = setup
        res.valor_numerico = Decimal("99")
        res.valor_obtenido = ""
        with pytest.raises(ValidationError):
            res.full_clean()

    def test_snapshot_conservado_tras_cambio_catalogo(self, setup):
        te, res = setup
        aplicar_snapshots_desde_tipo_examen(res, te)
        res.unidad = "mg/dL"
        res.rango_min_snapshot = te.rango_min
        res.rango_max_snapshot = te.rango_max
        res.save()
        te.rango_min = Decimal("50")
        te.rango_max = Decimal("90")
        te.save()
        res.refresh_from_db()
        assert res.rango_min_snapshot == Decimal("70")
