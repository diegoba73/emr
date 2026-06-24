"""Tests AUD-01: snapshots y entity_repr sin PHI/PII en auditoría genérica."""

import json
from datetime import date, timedelta

import pytest
from django.utils import timezone

from auditoria.snapshot import safe_entity_repr, safe_model_snapshot
from historias_clinicas.models import Consulta, HistoriaClinica
from medicos.models import Medico
from pacientes.models import Paciente
from solicitudes.models import Solicitud
from turnos.models import Atencion, ConsultaAmbulatoria, Recurso, Turno


def _raw(snapshot: dict) -> str:
    return json.dumps(snapshot, ensure_ascii=False, default=str)


@pytest.mark.django_db
class TestPacienteSnapshotRedaction:
    def test_snapshot_redacta_phi_demografica(self):
        pac = Paciente.objects.create(
            dni='30111222',
            nombre='Juan',
            apellido='Pérez',
            fecha_nacimiento=date(1980, 5, 10),
            telefono='1122334455',
            email='juan@example.com',
            direccion='Calle Falsa 123',
            obra_social='OSDE',
            numero_afiliado='AF-999',
            antecedentes_personales='HTA',
            antecedentes_familiares='DM padre',
            observaciones='Nota clínica libre',
        )
        snap = safe_model_snapshot(pac)
        raw = _raw(snap)

        assert '30111222' not in raw
        assert 'Juan' not in raw
        assert 'Pérez' not in raw
        assert '1122334455' not in raw
        assert 'juan@example.com' not in raw
        assert 'Calle Falsa' not in raw
        assert 'OSDE' not in raw
        assert 'AF-999' not in raw
        assert 'HTA' not in raw
        assert snap['dni'] == '<dato sensible redactado>'
        assert snap['nombre'] == '<dato sensible redactado>'
        assert snap['telefono'] == '<dato sensible redactado>'
        assert snap['antecedentes_personales'] == '<dato sensible redactado>'
        assert snap['observaciones'] == '<dato sensible redactado>'
        assert snap['id'] == pac.pk

    def test_entity_repr_sin_nombre_ni_dni(self):
        pac = Paciente.objects.create(dni='88888888', nombre='Ana', apellido='López')
        assert safe_entity_repr(pac) == f'Paciente #{pac.pk}'
        assert '88888888' not in safe_entity_repr(pac)
        assert 'Ana' not in safe_entity_repr(pac)


@pytest.mark.django_db
class TestConsultaSnapshotRedaction:
    def test_snapshot_redacta_texto_clinico(self):
        pac = Paciente.objects.create(dni='C-001', nombre='P', apellido='A')
        hc = HistoriaClinica.objects.create(paciente=pac)
        med = Medico.objects.create(matricula='MC-01', nombre='Dr', apellido='X')
        consulta = Consulta.objects.create(
            historia_clinica=hc,
            medico=med,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Dolor torácico opresivo',
            anamnesis='Paciente refiere disnea',
            examen_fisico='TA 140/90',
            diagnostico_presuntivo='Angina inestable',
            plan_manejo='ECG y troponinas',
            notas_medicas='Derivar guardia',
        )
        snap = safe_model_snapshot(consulta)
        raw = _raw(snap)

        assert 'Dolor torácico' not in raw
        assert 'disnea' not in raw
        assert 'Angina' not in raw
        assert snap['motivo_consulta_detalle'] == '<texto clínico redactado>'
        assert snap['anamnesis'] == '<texto clínico redactado>'
        assert snap['historia_clinica_id'] == hc.pk
        assert snap['medico_id'] == med.pk

    def test_entity_repr_sin_paciente_ni_medico_identificable(self):
        pac = Paciente.objects.create(dni='C-002', nombre='María', apellido='García')
        hc = HistoriaClinica.objects.create(paciente=pac)
        med = Medico.objects.create(matricula='MC-02', nombre='Luis', apellido='Doc')
        consulta = Consulta.objects.create(
            historia_clinica=hc,
            medico=med,
            fecha_hora_consulta=timezone.now(),
            motivo_consulta_detalle='Control',
        )
        repr_str = safe_entity_repr(consulta)
        assert repr_str == f'Consulta #{consulta.pk}'
        assert 'María' not in repr_str
        assert 'García' not in repr_str


@pytest.mark.django_db
class TestAtencionSnapshotRedaction:
    def test_snapshot_redacta_observaciones_generales(self):
        pac = Paciente.objects.create(dni='A-001', nombre='P', apellido='A')
        med = Medico.objects.create(matricula='MA-01', nombre='Dr', apellido='Y')
        rec = Recurso.objects.create(
            nombre='Box 1', ubicacion='CEHTA', tipo_recurso='CONSULTORIO', activo=True
        )
        inicio = timezone.now()
        fin = inicio + timedelta(minutes=30)
        turno = Turno.objects.create(
            paciente=pac,
            medico=med,
            recurso=rec,
            fecha_hora_inicio=inicio,
            fecha_hora_fin=fin,
            estado='CONFIRMADO',
        )
        atencion = Atencion.objects.create(
            turno=turno,
            paciente=pac,
            medico_principal=med,
            tipo_atencion='CONSULTORIO',
            observaciones_generales='Contenido asistencial sensible',
        )
        snap = safe_model_snapshot(atencion)
        assert 'Contenido asistencial' not in _raw(snap)
        assert snap['observaciones_generales'] == '<texto clínico redactado>'
        assert snap['paciente_id'] == pac.pk
        assert snap['medico_principal_id'] == med.pk

    def test_entity_repr_sin_nombre_paciente(self):
        pac = Paciente.objects.create(dni='A-002', nombre='Carlos', apellido='Ruiz')
        med = Medico.objects.create(matricula='MA-02', nombre='Dr', apellido='Z')
        atencion = Atencion.objects.create(
            paciente=pac,
            medico_principal=med,
            tipo_atencion='CONSULTORIO',
        )
        repr_str = safe_entity_repr(atencion)
        assert repr_str.startswith(f'Atención #{atencion.pk}')
        assert 'Carlos' not in repr_str
        assert 'Ruiz' not in repr_str


@pytest.mark.django_db
class TestSolicitudSnapshotRedaction:
    def test_snapshot_redacta_descripcion_y_observaciones(self):
        pac = Paciente.objects.create(dni='S-001', nombre='P', apellido='A')
        sol = Solicitud.objects.create(
            paciente=pac,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Hemograma completo urgente',
            observaciones='Ayuno 8h',
            estado='PENDIENTE',
        )
        snap = safe_model_snapshot(sol)
        raw = _raw(snap)

        assert 'Hemograma' not in raw
        assert 'Ayuno' not in raw
        assert snap['descripcion'] == '<texto clínico redactado>'
        assert snap['observaciones'] == '<texto clínico redactado>'
        assert snap['paciente_id'] == pac.pk
        assert snap['estado'] == 'PENDIENTE'

    def test_entity_repr_tecnico(self):
        pac = Paciente.objects.create(dni='S-002', nombre='X', apellido='Y')
        sol = Solicitud.objects.create(
            paciente=pac,
            tipo_solicitud='EXAMEN_LABORATORIO',
            descripcion='Rx tórax',
            estado='PENDIENTE',
        )
        repr_str = safe_entity_repr(sol)
        assert f'Solicitud #{sol.pk}' in repr_str
        assert 'Rx' not in repr_str


@pytest.mark.django_db
class TestConsultaAmbulatoriaSnapshotRedaction:
    def test_snapshot_redacta_texto_clinico_sensible(self):
        pac = Paciente.objects.create(dni='CA-001', nombre='P', apellido='A')
        med = Medico.objects.create(matricula='MCA-01', nombre='Dr', apellido='X')
        atencion = Atencion.objects.create(
            paciente=pac,
            medico_principal=med,
            tipo_atencion='CONSULTORIO',
        )
        consulta = ConsultaAmbulatoria.objects.create(
            atencion=atencion,
            anamnesis='Dolor precordial irradiado a brazo izquierdo',
            examen_fisico='Soplo sistólico grado II',
            diagnostico_presuntivo='Síndrome coronario agudo',
            plan_manejo='Internación UCO y troponinas seriadas',
            antecedentes_relevantes='IAM previo 2019',
            alergias='Penicilina',
            medicacion_actual='AAS 100mg',
            diagnostico_definitivo='Angina inestable',
            observaciones_medicas='Derivar cardiología',
        )
        snap = safe_model_snapshot(consulta)
        raw = _raw(snap)

        assert 'precordial' not in raw
        assert 'Soplo sistólico' not in raw
        assert 'coronario' not in raw
        assert 'Penicilina' not in raw
        assert snap['anamnesis'] == '<texto clínico redactado>'
        assert snap['examen_fisico'] == '<texto clínico redactado>'
        assert snap['diagnostico_presuntivo'] == '<texto clínico redactado>'
        assert snap['plan_manejo'] == '<texto clínico redactado>'
        assert snap['alergias'] == '<texto clínico redactado>'
        assert snap['atencion'] == atencion.pk
