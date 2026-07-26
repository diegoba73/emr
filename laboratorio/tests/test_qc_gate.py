"""Gate QC: última corrida del día por material."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from laboratorio.models import TipoExamen, TipoMuestra
from laboratorio.models_qc import CorridaQC, LoteControl, MaterialControl
from laboratorio.qc_service import QcGateError, validar_qc_para_cierre


class _FakeSolicitud:
    def __init__(self, examen_ids):
        self.id = 1
        self._ids = list(examen_ids)

    @property
    def tipos_examen(self):
        class _VS:
            def __init__(self, ids):
                self._ids = ids

            def values_list(self, *_a, **_k):
                return self

            def flat(self):
                return self

            def __iter__(self):
                return iter(self._ids)

        # Django values_list returns ValuesListQuerySet; mimic enough for set()
        return _Values(self._ids)

    @property
    def paneles(self):
        class _Empty:
            def prefetch_related(self, *_a):
                return self

            def all(self):
                return []

        return _Empty()

    @property
    def resultados(self):
        class _Empty:
            def values_list(self, *_a, **_k):
                return self

            def distinct(self):
                return []

        return _Empty()


class _Values:
    def __init__(self, ids):
        self._ids = ids

    def values_list(self, *_a, **_k):
        return self

    def __iter__(self):
        return iter(self._ids)


class TestQcGateUltimaCorrida(TestCase):
    def setUp(self):
        self.muestra = TipoMuestra.objects.create(codigo="SANGRE_QG", nombre="Sangre QG")
        self.examen = TipoExamen.objects.create(
            codigo="GLU_QG",
            nombre="Glucosa QG",
            tipo_muestra_requerida=self.muestra,
            tipo_resultado="NUMERICO",
        )
        self.mat = MaterialControl.objects.create(
            nombre="Ctrl GLU S1",
            nivel=MaterialControl.Nivel.N1,
            tipo_examen=self.examen,
            media_target=Decimal("100"),
            de_target=Decimal("5"),
            activo=True,
        )
        self.lote = LoteControl.objects.create(
            material=self.mat,
            codigo_lote="L-QG",
            vencimiento=timezone.localdate() + timedelta(days=30),
        )
        self.solicitud = _FakeSolicitud([self.examen.id])

    def _corrida(self, estado, minutes_ago=0):
        return CorridaQC.objects.create(
            lote_control=self.lote,
            fecha=timezone.now() - timedelta(minutes=minutes_ago),
            estado=estado,
        )

    def test_rechazo_previo_y_aceptada_posterior_ok(self):
        self._corrida(CorridaQC.Estado.RECHAZADA, minutes_ago=60)
        self._corrida(CorridaQC.Estado.ACEPTADA, minutes_ago=5)
        validar_qc_para_cierre(self.solicitud)

    def test_ultima_rechazada_bloquea(self):
        self._corrida(CorridaQC.Estado.ACEPTADA, minutes_ago=60)
        self._corrida(CorridaQC.Estado.RECHAZADA, minutes_ago=5)
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        self.assertIn("GLU_QG", str(ctx.exception))
        self.assertIn("rechazado", str(ctx.exception).lower())

    def test_sin_corrida_bloquea(self):
        with self.assertRaises(QcGateError) as ctx:
            validar_qc_para_cierre(self.solicitud)
        self.assertIn("Sin corrida", str(ctx.exception))
