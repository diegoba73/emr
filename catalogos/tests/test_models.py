"""
Tests de modelos para catalogos.
"""
import uuid

import pytest
from django.db.utils import IntegrityError

from catalogos.models import (
    AreaInternacion,
    CamaInternacion,
    CentroFisico,
    EstudioDiagnostico,
    Procedimiento,
    ProcedimientoCatalogo,
    TipoAtencion,
)
from medicos.models import Especialidad


@pytest.mark.django_db
class TestCatalogosModels:
    def test_centro_fisico_get_or_create(self):
        centro, created = CentroFisico.objects.get_or_create(
            codigo="CEHTA",
            defaults={
                "nombre": "CEHTA Test Catalog",
                "activo": True,
            },
        )
        assert centro.pk
        assert centro.codigo == "CEHTA"

    def test_tipo_atencion_linked_to_centro(self):
        centro, _ = CentroFisico.objects.get_or_create(
            codigo="CEHTA",
            defaults={"nombre": "CEHTA Test", "activo": True},
        )
        tipo, _ = TipoAtencion.objects.get_or_create(
            codigo="AMBULATORIA",
            defaults={
                "nombre": "Ambulatoria Test Cat",
                "centro_fisico": centro,
                "activo": True,
            },
        )
        assert tipo.codigo == "AMBULATORIA"
        assert tipo.centro_fisico_id is not None

    def test_area_internacion_and_cama(self):
        centro, _ = CentroFisico.objects.get_or_create(
            codigo="CEHTA",
            defaults={"nombre": "CEHTA Test", "activo": True},
        )
        area, _ = AreaInternacion.objects.get_or_create(
            codigo="UCO",
            defaults={
                "nombre": "UCO Test Cat",
                "centro_fisico": centro,
                "capacidad_camas": 5,
                "activo": True,
            },
        )
        numero = f"T-{uuid.uuid4().hex[:12]}"
        cama = CamaInternacion.objects.create(
            numero=numero,
            area=area,
            estado="DISPONIBLE",
            tipo_cama="ESTANDAR",
            activa=True,
        )
        assert cama.area_id == area.id
        assert cama.numero == numero

    def test_estudio_diagnostico_nombre_unique(self):
        suffix = uuid.uuid4().hex[:10]
        nombre = f"Estudio único catálogo {suffix}"
        EstudioDiagnostico.objects.create(nombre=nombre, activo=True)
        with pytest.raises(IntegrityError):
            EstudioDiagnostico.objects.create(nombre=nombre, activo=True)

    def test_procedimiento_catalogo_nombre_unique(self):
        suffix = uuid.uuid4().hex[:10]
        nombre = f"Proc cat único {suffix}"
        ProcedimientoCatalogo.objects.create(nombre=nombre, activo=True)
        with pytest.raises(IntegrityError):
            ProcedimientoCatalogo.objects.create(nombre=nombre, activo=True)

    def test_procedimiento_requires_especialidad(self):
        esp = Especialidad.objects.create(
            nombre=f"Esp Catalog Test {uuid.uuid4().hex[:8]}",
            descripcion="test",
        )
        proc = Procedimiento.objects.create(
            codigo=f"P-{uuid.uuid4().hex[:8]}",
            nombre="Procedimiento test cat",
            descripcion="desc",
            especialidad=esp,
            duracion_estimada=30,
            activo=True,
        )
        assert proc.especialidad_id == esp.id
