"""Tests para los modelos de la app ``historias_clinicas``.

Convenciones de seed local (para no chocar con datos del seed global):
- ``Especialidad`` se crea con ``get_or_create`` y nombres con sufijo ``HC Models``.
- ``Paciente`` con DNIs ``HM-XXXX``.
- ``Medico`` con matrículas ``MHM-XXX``.
"""
import pytest
from datetime import date, timedelta

from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError
from django.utils import timezone

from catalogos.models import Medicamento
from historias_clinicas.models import (
    Consulta,
    Diagnostico,
    HistoriaClinica,
    Prescripcion,
    Sintoma,
    Tratamiento,
)
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente


def _esp(nombre: str) -> Especialidad:
    obj, _ = Especialidad.objects.get_or_create(nombre=nombre)
    return obj


@pytest.mark.django_db
class TestHistoriaClinicaModel:
    """Tests para el modelo ``HistoriaClinica``."""

    def test_flujo_clinico_completo(self):
        paciente = Paciente.objects.create(
            dni='HM-1001',
            nombre='Juan',
            apellido='Pérez',
        )
        historia_clinica = HistoriaClinica.objects.create(paciente=paciente)
        assert historia_clinica.paciente == paciente
        assert historia_clinica.fecha_creacion is not None

        especialidad = _esp('Cardiología HC Models')
        medico = Medico.objects.create(
            matricula='MHM-001',
            nombre='Dr. Carlos',
            apellido='García',
            especialidad=especialidad,
        )

        consulta = Consulta.objects.create(
            historia_clinica=historia_clinica,
            medico=medico,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Dolor de pecho',
            anamnesis='Paciente refiere dolor precordial',
            examen_fisico='TA: 120/80, FC: 80 lpm',
            diagnostico_presuntivo='Angina de pecho',
            plan_manejo='ECG y enzimas cardíacas',
        )
        assert consulta.historia_clinica.paciente == paciente
        assert consulta.medico == medico
        assert consulta.motivo_consulta_detalle == 'Dolor de pecho'

    def test_unicidad_historia_clinica_por_paciente(self):
        paciente = Paciente.objects.create(
            dni='HM-1002',
            nombre='María',
            apellido='González',
        )
        HistoriaClinica.objects.create(paciente=paciente)
        with pytest.raises(IntegrityError):
            HistoriaClinica.objects.create(paciente=paciente)

    def test_historia_clinica_se_borra_al_borrar_paciente(self):
        paciente = Paciente.objects.create(
            dni='HM-1003',
            nombre='Pedro',
            apellido='López',
        )
        historia_clinica = HistoriaClinica.objects.create(paciente=paciente)
        historia_id = historia_clinica.paciente_id

        paciente.delete()

        assert not HistoriaClinica.objects.filter(paciente_id=historia_id).exists()

    def test_str_tolerante_a_none(self):
        """``__str__`` no debe romper si ``apellido``/``nombre`` están vacíos."""
        paciente = Paciente.objects.create(dni='HM-1004')
        historia_clinica = HistoriaClinica.objects.create(paciente=paciente)
        # No exigimos un texto exacto, solo que no estalle y mencione el DNI
        # como fallback en ausencia de apellido/nombre.
        assert 'HM-1004' in str(historia_clinica)


@pytest.mark.django_db
class TestConsultaModel:
    """Tests para el modelo ``Consulta``."""

    def test_consulta_con_turno(self):
        from turnos.models import Recurso, Turno

        paciente = Paciente.objects.create(
            dni='HM-2001',
            nombre='Ana',
            apellido='Martínez',
        )
        historia_clinica = HistoriaClinica.objects.create(paciente=paciente)

        especialidad = _esp('Neurología HC Models')
        medico = Medico.objects.create(
            matricula='MHM-002',
            nombre='Dr. Ana',
            apellido='Rodríguez',
            especialidad=especialidad,
        )

        recurso = Recurso.objects.create(
            nombre='Consultorio HC-1',
            ubicacion=Recurso.Ubicacion.CEHTA,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

        turno = Turno.objects.create(
            paciente=paciente,
            medico=medico,
            recurso=recurso,
            fecha_hora_inicio=timezone.now() + timedelta(days=1),
            estado=Turno.Estado.CONFIRMADO,
        )

        consulta = Consulta.objects.create(
            historia_clinica=historia_clinica,
            medico=medico,
            turno=turno,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Control de rutina',
        )

        assert consulta.turno == turno
        assert consulta.historia_clinica.paciente == paciente

    def test_str_consulta_tolerante_a_none(self):
        paciente = Paciente.objects.create(dni='HM-2002')
        historia_clinica = HistoriaClinica.objects.create(paciente=paciente)
        consulta = Consulta.objects.create(
            historia_clinica=historia_clinica,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Sin médico, sin nombre',
        )
        # No debe explotar y debe mencionar al menos el DNI vía fallback.
        rendered = str(consulta)
        assert 'HM-2002' in rendered
        assert 'Sin médico' in rendered


@pytest.mark.django_db
class TestDiagnosticoModel:
    """Tests para el modelo ``Diagnostico``."""

    def test_diagnostico_con_sintomas(self):
        paciente = Paciente.objects.create(
            dni='HM-3001',
            nombre='Carlos',
            apellido='Fernández',
        )
        historia_clinica = HistoriaClinica.objects.create(paciente=paciente)
        especialidad = _esp('Medicina General HC Models')
        medico = Medico.objects.create(
            matricula='MHM-003',
            nombre='Dr. Luis',
            apellido='Sánchez',
            especialidad=especialidad,
        )
        consulta = Consulta.objects.create(
            historia_clinica=historia_clinica,
            medico=medico,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Fiebre y tos',
        )
        sintoma1, _ = Sintoma.objects.get_or_create(
            nombre='Fiebre HC Models',
            defaults={'descripcion': 'Temperatura corporal elevada'},
        )
        sintoma2, _ = Sintoma.objects.get_or_create(
            nombre='Tos HC Models',
            defaults={'descripcion': 'Tos seca o productiva'},
        )

        diagnostico = Diagnostico.objects.create(
            consulta=consulta,
            nombre_diagnostico='Infección respiratoria',
            descripcion_diagnostico='Probable infección viral',
        )
        diagnostico.sintomas_asociados.add(sintoma1, sintoma2)

        assert diagnostico.consulta == consulta
        assert diagnostico.sintomas_asociados.count() == 2
        assert sintoma1 in diagnostico.sintomas_asociados.all()
        assert sintoma2 in diagnostico.sintomas_asociados.all()


def _seed_consulta(dni: str, especialidad_nombre: str, matricula: str):
    paciente = Paciente.objects.create(dni=dni, nombre='Pac', apellido='Test')
    historia = HistoriaClinica.objects.create(paciente=paciente)
    especialidad = _esp(especialidad_nombre)
    medico = Medico.objects.create(
        matricula=matricula,
        nombre='Dr.',
        apellido='Test',
        especialidad=especialidad,
    )
    consulta = Consulta.objects.create(
        historia_clinica=historia,
        medico=medico,
        fecha_hora_consulta=timezone.now(),
        motivo_consulta_detalle='Caso',
    )
    return paciente, historia, medico, consulta


@pytest.mark.django_db
class TestPrescripcionModel:
    """Tests para el modelo ``Prescripcion``."""

    def test_prescripcion_flow_completo(self):
        medicamento, _ = Medicamento.objects.get_or_create(
            nombre='Ibuprofeno HC Models',
            defaults=dict(
                principio_activo='Ibuprofeno',
                presentacion='Comprimidos',
                concentracion='600mg',
                via_administracion='Oral',
                activo=True,
            ),
        )
        _, _, _, consulta = _seed_consulta('HM-4001', 'Pres HC Models 1', 'MHM-008')

        prescripcion = Prescripcion.objects.create(
            consulta=consulta,
            medicamento=medicamento,
            dosis='600mg',
            frecuencia='Cada 8hs',
            duracion='7 días',
            instrucciones='Tomar con alimentos',
            activa=True,
        )

        assert prescripcion.medicamento.nombre == 'Ibuprofeno HC Models'
        assert prescripcion.medicamento == medicamento
        assert prescripcion.consulta == consulta
        assert prescripcion.dosis == '600mg'
        assert prescripcion.frecuencia == 'Cada 8hs'
        assert prescripcion.activa is True

    def test_integridad_catalogo_medicamento_protect(self):
        """``Prescripcion.medicamento`` debe tener ``on_delete=PROTECT``.

        Borrar un medicamento que tenga prescripciones activas o históricas
        debe fallar con ``ProtectedError``: la trazabilidad clínica es
        prioritaria sobre la limpieza del catálogo.
        """
        medicamento, _ = Medicamento.objects.get_or_create(
            nombre='Paracetamol HC Models',
            defaults=dict(
                principio_activo='Paracetamol',
                presentacion='Comprimidos',
                concentracion='500mg',
                via_administracion='Oral',
                activo=True,
            ),
        )
        _, _, _, consulta = _seed_consulta('HM-4002', 'Pres HC Models 2', 'MHM-009')
        prescripcion = Prescripcion.objects.create(
            consulta=consulta,
            medicamento=medicamento,
            dosis='500mg',
            frecuencia='Cada 6hs',
            duracion='5 días',
            activa=True,
        )

        with pytest.raises(ProtectedError):
            medicamento.delete()

        # La prescripción y el medicamento siguen existiendo.
        assert Prescripcion.objects.filter(id=prescripcion.id).exists()
        assert Medicamento.objects.filter(pk=medicamento.pk).exists()

    def test_prescripcion_str_representation(self):
        medicamento, _ = Medicamento.objects.get_or_create(
            nombre='Ibuprofeno HC Models Repr',
            defaults=dict(
                principio_activo='Ibuprofeno',
                presentacion='Comprimidos',
                concentracion='600mg',
                via_administracion='Oral',
                activo=True,
            ),
        )
        _, _, _, consulta = _seed_consulta('HM-4003', 'Pres HC Models 3', 'MHM-010')
        prescripcion = Prescripcion.objects.create(
            consulta=consulta,
            medicamento=medicamento,
            dosis='600mg',
            frecuencia='Cada 8hs',
            duracion='7 días',
            activa=True,
        )

        rendered = str(prescripcion)
        assert 'Ibuprofeno HC Models Repr' in rendered
        assert '600mg' in rendered
        assert 'Cada 8hs' in rendered


@pytest.mark.django_db
class TestTratamientoModel:
    """Tests para el modelo ``Tratamiento``."""

    def test_tratamiento_fechas(self):
        _, _, _, consulta = _seed_consulta('HM-5001', 'Trat HC Models 1', 'MHM-011')
        fecha_inicio = date.today()
        fecha_fin = date.today() + timedelta(days=30)
        tratamiento = Tratamiento.objects.create(
            consulta=consulta,
            tipo_tratamiento='TERAPIA',
            descripcion_tratamiento='Fisioterapia para recuperación de lesión',
            dosis_frecuencia='3 veces por semana',
            fecha_inicio=fecha_inicio,
            fecha_fin_estimada=fecha_fin,
            instrucciones_adicionales='Aplicar hielo después de cada sesión',
        )

        assert tratamiento.fecha_inicio == fecha_inicio
        assert tratamiento.fecha_fin_estimada == fecha_fin
        assert tratamiento.tipo_tratamiento == 'TERAPIA'
        assert tratamiento.consulta == consulta

    def test_tratamiento_sin_fechas(self):
        _, _, _, consulta = _seed_consulta('HM-5002', 'Trat HC Models 2', 'MHM-012')
        tratamiento = Tratamiento.objects.create(
            consulta=consulta,
            tipo_tratamiento='REPOSO',
            descripcion_tratamiento='Reposo relativo por 48 horas',
        )
        assert tratamiento.fecha_inicio is None
        assert tratamiento.fecha_fin_estimada is None
        assert tratamiento.tipo_tratamiento == 'REPOSO'

    def test_tratamiento_cascade_al_borrar_consulta(self):
        _, _, _, consulta = _seed_consulta('HM-5003', 'Trat HC Models 3', 'MHM-013')
        tratamiento = Tratamiento.objects.create(
            consulta=consulta,
            tipo_tratamiento='MEDICAMENTOSO',
            descripcion_tratamiento='Anticoagulante',
        )
        tratamiento_id = tratamiento.id

        consulta.delete()

        assert not Tratamiento.objects.filter(id=tratamiento_id).exists()
