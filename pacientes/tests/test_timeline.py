"""Timeline clínica: eventos LIMS alineados con permiso de lectura del rol."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model

from laboratorio.models import SolicitudExamen
from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from pacientes.services_timeline import build_paciente_timeline
from turnos.models import Atencion

User = get_user_model()


@pytest.mark.django_db
class TestTimelineLimsVisibilidadMedico:
    def setup_method(self):
        self.paciente = Paciente.objects.create(
            dni="TL-LAB-001",
            nombre="Ana",
            apellido="Timeline",
            fecha_nacimiento=date(1990, 1, 1),
        )
        esp = Especialidad.objects.create(nombre="Esp Timeline Lab")
        self.user_medico = User.objects.create_user(
            username="medico.timeline.lab",
            email="medico.timeline@example.com",
            password="x",
            rol="medico",
        )
        self.medico = Medico.objects.create(
            user=self.user_medico,
            nombre="Dr",
            apellido="Propio",
            matricula="MAT-TL-OWN",
            especialidad=esp,
        )
        self.otro_medico = Medico.objects.create(
            nombre="Dr",
            apellido="Ajeno",
            matricula="MAT-TL-OTH",
            especialidad=esp,
        )
        self.sol_propia = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.medico,
            origen_solicitud="AMBULATORIO_CEHTA",
        )
        self.sol_ajena = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=self.otro_medico,
            origen_solicitud="AMBULATORIO_CEHTA",
        )
        self.sol_externa = SolicitudExamen.objects.create(
            paciente=self.paciente,
            medico_interno=None,
            medico_externo_nombre="Dr Papel",
            origen_solicitud="AMBULATORIO_CEHTA",
        )

    def _lab_ids(self, events):
        return {
            ev["meta"]["solicitud_examen_id"]
            for ev in events
            if ev.get("type") == "solicitud" and ev.get("meta", {}).get("solicitud_examen_id")
        }

    def test_medico_sin_vinculo_solo_ve_propias_en_timeline(self):
        events = build_paciente_timeline(self.paciente.id, user=self.user_medico)
        assert self._lab_ids(events) == {self.sol_propia.id}

    def test_medico_con_vinculo_ve_labs_de_otros_en_timeline(self):
        Atencion.objects.create(
            paciente=self.paciente,
            medico_principal=self.medico,
            tipo_atencion="CONSULTORIO",
            tipo_intervencion="CONSULTA",
            estado_clinico="ABIERTA",
        )
        events = build_paciente_timeline(self.paciente.id, user=self.user_medico)
        assert self._lab_ids(events) == {
            self.sol_propia.id,
            self.sol_ajena.id,
            self.sol_externa.id,
        }

    def test_admin_ve_todas_las_ordenes_lims_en_timeline(self):
        admin = User.objects.create_user(
            username="admin.timeline.lab",
            email="admin.timeline@example.com",
            password="x",
            rol="admin",
            is_staff=True,
        )
        events = build_paciente_timeline(self.paciente.id, user=admin)
        assert self._lab_ids(events) == {
            self.sol_propia.id,
            self.sol_ajena.id,
            self.sol_externa.id,
        }
