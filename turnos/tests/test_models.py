"""Tests para los modelos de la app ``turnos``.

Convenciones de seed local (para no chocar con datos del seed global):
- ``Especialidad`` se crea con ``get_or_create`` y nombres con sufijos del
  archivo (``... Models``) para no colisionar con seeds compartidos.
- ``Paciente`` se crea con DNIs claramente del bloque (``TM-XXXX``).
- ``Medico`` se crea con matrículas ``MTM-XXX``.
"""
import pytest
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

from turnos.models import Recurso, Turno, Atencion
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad


def _esp(nombre: str) -> Especialidad:
    obj, _ = Especialidad.objects.get_or_create(nombre=nombre)
    return obj


@pytest.mark.django_db
class TestTimestampedModel:
    """Tests para los timestamps automáticos provistos por ``TimestampedModel``."""

    def test_timestamp_created_at_se_llena_automaticamente(self):
        recurso = Recurso.objects.create(
            nombre='Consultorio TM-1',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        assert recurso.created_at is not None
        assert isinstance(recurso.created_at, datetime)
        assert recurso.updated_at is not None
        assert isinstance(recurso.updated_at, datetime)
        diferencia = abs((recurso.updated_at - recurso.created_at).total_seconds())
        assert diferencia < 1


@pytest.mark.django_db
class TestTurnoModel:
    """Tests para el modelo ``Turno``."""

    def test_turno_flow_reservado_con_paciente_y_medico(self):
        especialidad = _esp('Cardiología Models')
        paciente = Paciente.objects.create(
            dni='TM-1001',
            nombre='Juan',
            apellido='Pérez',
        )
        medico = Medico.objects.create(
            matricula='MTM-001',
            nombre='Dr. Carlos',
            apellido='García',
            especialidad=especialidad,
        )
        recurso = Recurso.objects.create(
            nombre='Consultorio TM-2',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        fecha_inicio = timezone.now() + timedelta(days=1)
        fecha_fin = fecha_inicio + timedelta(hours=1)
        turno = Turno.objects.create(
            paciente=paciente,
            medico=medico,
            recurso=recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_fin,
            estado=Turno.Estado.RESERVADO,
            motivo_reserva='Consulta de rutina',
        )

        assert turno.paciente == paciente
        assert turno.medico == medico
        assert turno.recurso == recurso
        assert turno.estado == Turno.Estado.RESERVADO
        assert turno.motivo_reserva == 'Consulta de rutina'
        assert turno.fecha_hora_inicio == fecha_inicio
        assert turno.fecha_hora_fin == fecha_fin

    def test_turno_fecha_fin_anterior_a_inicio_debe_fallar(self):
        recurso = Recurso.objects.create(
            nombre='Consultorio TM-3',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        fecha_inicio = timezone.now() + timedelta(days=1)
        fecha_fin = fecha_inicio - timedelta(hours=1)
        turno = Turno(
            recurso=recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_fin,
            estado=Turno.Estado.DISPONIBLE,
        )

        with pytest.raises(ValidationError) as exc_info:
            turno.save()

        assert 'fecha_hora_fin' in exc_info.value.error_dict
        assert 'posterior' in str(exc_info.value.error_dict['fecha_hora_fin'][0]).lower()

    def test_turno_fecha_fin_igual_a_inicio_debe_fallar(self):
        recurso = Recurso.objects.create(
            nombre='Consultorio TM-4',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno(
            recurso=recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio,
            estado=Turno.Estado.DISPONIBLE,
        )

        with pytest.raises(ValidationError):
            turno.save()

    def test_turno_sin_fecha_fin_no_valida(self):
        recurso = Recurso.objects.create(
            nombre='Consultorio TM-5',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno(
            recurso=recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=None,
            estado=Turno.Estado.DISPONIBLE,
        )

        try:
            turno.save()
        except ValidationError:
            pytest.fail("save() no debería lanzar ValidationError cuando fecha_hora_fin es None")

        assert Turno.objects.filter(id=turno.id).exists()

    def test_turno_integridad_medico_set_null_al_borrar(self):
        especialidad = _esp('Neurología Models')
        medico = Medico.objects.create(
            matricula='MTM-002',
            nombre='Dr. Ana',
            apellido='Martínez',
            especialidad=especialidad,
        )
        recurso = Recurso.objects.create(
            nombre='Consultorio TM-6',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            medico=medico,
            recurso=recurso,
            fecha_hora_inicio=fecha_inicio,
            estado=Turno.Estado.RESERVADO,
        )
        turno_id = turno.id

        assert turno.medico == medico

        medico.delete()
        turno.refresh_from_db()

        assert Turno.objects.filter(id=turno_id).exists()
        assert turno.medico is None

    def test_turno_integridad_recurso_cascade_al_borrar_modelo(self):
        """A nivel de modelo, ``Turno.recurso`` sigue siendo CASCADE.

        La protección operativa contra esta cascada se hace en
        ``RecursoViewSet.destroy`` (baja lógica). Este test resguarda el
        contrato a nivel de DB para que cualquier cambio futuro de modelo
        rompa explícitamente el suite y exija decisión consciente.
        """
        recurso = Recurso.objects.create(
            nombre='Consultorio TM-7',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            recurso=recurso,
            fecha_hora_inicio=fecha_inicio,
            estado=Turno.Estado.DISPONIBLE,
        )
        turno_id = turno.id

        assert Turno.objects.filter(id=turno_id).exists()

        recurso.delete()

        assert not Turno.objects.filter(id=turno_id).exists()

    def test_turno_str_representation(self):
        paciente = Paciente.objects.create(
            dni='TM-1002',
            nombre='María',
            apellido='González',
        )
        recurso = Recurso.objects.create(
            nombre='Quirófano TM-1',
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.QUIROFANO,
            activo=True,
        )

        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=paciente,
            recurso=recurso,
            fecha_hora_inicio=fecha_inicio,
            estado=Turno.Estado.CONFIRMADO,
        )

        str_repr = str(turno)
        assert f"Turno #{turno.id}" in str_repr
        assert "González" in str_repr or "María" in str_repr
        assert "Quirófano TM-1" in str_repr


@pytest.mark.django_db
class TestRecursoModel:
    """Tests adicionales para el modelo ``Recurso``."""

    def test_recurso_str_representation(self):
        recurso = Recurso.objects.create(
            nombre='Sala Hemodinamia TM-1',
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.SALA_HEMODINAMIA,
            activo=True,
        )

        str_repr = str(recurso)
        assert "Recurso:" in str_repr
        assert "Sala Hemodinamia TM-1" in str_repr
        assert "ICPL" in str_repr


@pytest.mark.django_db
class TestAtencionModel:
    """Tests para el modelo ``Atencion``."""

    def test_atencion_vinculada_a_turno(self):
        paciente = Paciente.objects.create(
            dni='TM-2001',
            nombre='Laura',
            apellido='Gómez',
        )
        especialidad = _esp('Cardiología Models Atencion')
        medico = Medico.objects.create(
            matricula='MTM-004',
            nombre='Dr. Roberto',
            apellido='Díaz',
            especialidad=especialidad,
        )
        recurso = Recurso.objects.create(
            nombre='Consultorio TM-Atencion-2',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        fecha_inicio = timezone.now() + timedelta(days=1)
        fecha_fin = fecha_inicio + timedelta(hours=1)

        turno = Turno.objects.create(
            paciente=paciente,
            medico=medico,
            recurso=recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_fin,
            estado=Turno.Estado.CONFIRMADO,
        )

        atencion = Atencion.objects.create(
            turno=turno,
            paciente=paciente,
            medico_principal=medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
        )

        assert atencion.turno == turno
        assert atencion.paciente == paciente
        assert atencion.medico_principal == medico
        assert atencion.estado_clinico == Atencion.EstadoClinico.ABIERTA
        assert atencion.fecha_admision is not None

    def test_atencion_sin_turno(self):
        paciente = Paciente.objects.create(
            dni='TM-2002',
            nombre='Miguel',
            apellido='Torres',
        )
        especialidad = _esp('Emergencias Models')
        medico = Medico.objects.create(
            matricula='MTM-005',
            nombre='Dr. Elena',
            apellido='Vargas',
            especialidad=especialidad,
        )

        atencion = Atencion.objects.create(
            turno=None,
            paciente=paciente,
            medico_principal=medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
        )

        assert atencion.turno is None
        assert atencion.paciente == paciente
        assert atencion.medico_principal == medico

    def test_atencion_protect_paciente_y_medico(self):
        paciente = Paciente.objects.create(
            dni='TM-2003',
            nombre='Sofía',
            apellido='Ramírez',
        )
        especialidad = _esp('Pediatría Models')
        medico = Medico.objects.create(
            matricula='MTM-006',
            nombre='Dr. Pablo',
            apellido='Morales',
            especialidad=especialidad,
        )

        Atencion.objects.create(
            paciente=paciente,
            medico_principal=medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
        )

        with pytest.raises(Exception):
            paciente.delete()
        with pytest.raises(Exception):
            medico.delete()

    def test_atencion_str_representation(self):
        paciente = Paciente.objects.create(
            dni='TM-2004',
            nombre='Diego',
            apellido='Castro',
        )
        especialidad = _esp('Traumatología Models')
        medico = Medico.objects.create(
            matricula='MTM-007',
            nombre='Dr. Carmen',
            apellido='Jiménez',
            especialidad=especialidad,
        )

        atencion = Atencion.objects.create(
            paciente=paciente,
            medico_principal=medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
        )

        str_repr = str(atencion)
        assert f"Atención #{atencion.id}" in str_repr
        assert "Castro" in str_repr or "Diego" in str_repr
        assert "Jiménez" in str_repr or "Carmen" in str_repr
        assert "Abierta" in str_repr
