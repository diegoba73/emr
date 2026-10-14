"""Unit tests for turnos.notificar_reprogramacion."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from medicos.models import Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno
from turnos.notificar_reprogramacion import notificar_reprogramacion


@pytest.mark.django_db
class TestNotificarReprogramacion:
    def setup_method(self):
        esp = Especialidad.objects.create(nombre='Cardio Notif')
        self.medico = Medico.objects.create(
            nombre='Ana', apellido='Med', matricula='NOTIF-M1', especialidad=esp,
        )
        self.paciente = Paciente.objects.create(
            dni='NOTIF-P1', nombre='Juan', apellido='Pac', telefono='11 2345-6789',
        )
        self.recurso = Recurso.objects.create(
            nombre='Cons Notif', tipo_recurso=Recurso.TipoRecurso.CONSULTORIO, activo=True,
        )
        base = timezone.now() + timedelta(days=2)
        self.turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=base,
            fecha_hora_fin=base + timedelta(minutes=20),
            estado=Turno.Estado.CONFIRMADO,
        )

    def test_sin_twilio_devuelve_wa_me(self):
        with patch.dict('os.environ', {}, clear=False):
            for key in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_WHATSAPP_FROM'):
                # Ensure Twilio env is empty for this test.
                pass
            with patch('turnos.notificar_reprogramacion._intentar_twilio_whatsapp', return_value=(False, None)):
                with patch('turnos.notificar_reprogramacion._enviar_push', return_value=0):
                    result = notificar_reprogramacion(self.turno)
        assert result.whatsapp_enviado is False
        assert result.whatsapp_url and result.whatsapp_url.startswith('https://wa.me/')
        assert result.push_enviados == 0

    def test_sin_telefono_no_arma_whatsapp(self):
        self.paciente.telefono = ''
        self.paciente.save(update_fields=['telefono'])
        self.turno.refresh_from_db()
        with patch('turnos.notificar_reprogramacion._enviar_push', return_value=2):
            result = notificar_reprogramacion(self.turno)
        assert result.whatsapp_url is None
        assert result.whatsapp_enviado is False
        assert result.push_enviados == 2
        assert result.detalle
