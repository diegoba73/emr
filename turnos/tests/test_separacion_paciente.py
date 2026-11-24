"""Separación mínima entre turnos del mismo paciente según tipo."""
from datetime import datetime, timedelta
from datetime import time as dt_time

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from medicos.models import DisponibilidadMedico, Especialidad, Medico
from pacientes.models import Paciente
from turnos.models import Recurso, Turno
from turnos.separacion_paciente import (
    SEPARACION_CONSULTA_ESTUDIO_MINUTOS,
    SEPARACION_CONSULTA_MINUTOS,
    SEPARACION_ESTUDIO_ESTUDIO_MINUTOS,
    SeparacionPacienteError,
    minutos_separacion_requeridos,
    validar_separacion_paciente,
)
from usuarios.models import User


def _aware(day_offset: int, hour: int, minute: int = 0):
    fecha = timezone.localdate() + timedelta(days=14 + day_offset)
    return timezone.make_aware(datetime.combine(fecha, dt_time(hour, minute)))


@pytest.mark.django_db
class TestSeparacionPacienteHelper:
    def setup_method(self):
        esp = Especialidad.objects.create(nombre='Sep Esp')
        self.medico = Medico.objects.create(
            nombre='Dr', apellido='Sep', matricula='SEP-M1', especialidad=esp,
        )
        self.paciente = Paciente.objects.create(
            dni='SEP-P1', nombre='Pac', apellido='Sep',
        )
        self.cons = Recurso.objects.create(
            nombre='Cons Sep',
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )
        self.sala = Recurso.objects.create(
            nombre='Sala Sep',
            tipo_recurso=Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
            activo=True,
        )

    def _turno(self, recurso, inicio, fin, estado=Turno.Estado.CONFIRMADO):
        return Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=recurso,
            fecha_hora_inicio=inicio,
            fecha_hora_fin=fin,
            estado=estado,
        )

    def test_minutos_por_par_de_tipos(self):
        assert minutos_separacion_requeridos('CONSULTA', 'CONSULTA') == SEPARACION_CONSULTA_MINUTOS
        assert minutos_separacion_requeridos('CONSULTA', 'ESTUDIO') == SEPARACION_CONSULTA_ESTUDIO_MINUTOS
        assert minutos_separacion_requeridos('ESTUDIO', 'CONSULTA') == SEPARACION_CONSULTA_ESTUDIO_MINUTOS
        assert minutos_separacion_requeridos('ESTUDIO', 'ESTUDIO') == SEPARACION_ESTUDIO_ESTUDIO_MINUTOS

    def test_dos_consultas_rechaza_menos_de_30(self):
        ini = _aware(0, 9)
        self._turno(self.cons, ini, ini + timedelta(minutes=20))
        # Empieza 20 min después del fin → gap 20 < 30
        nuevo_ini = ini + timedelta(minutes=40)
        with pytest.raises(SeparacionPacienteError, match='30 minutos'):
            validar_separacion_paciente(
                paciente=self.paciente,
                inicio=nuevo_ini,
                fin=nuevo_ini + timedelta(minutes=20),
                recurso=self.cons,
            )

    def test_dos_consultas_permite_30(self):
        ini = _aware(0, 9)
        self._turno(self.cons, ini, ini + timedelta(minutes=20))
        nuevo_ini = ini + timedelta(minutes=50)  # gap 30
        validar_separacion_paciente(
            paciente=self.paciente,
            inicio=nuevo_ini,
            fin=nuevo_ini + timedelta(minutes=20),
            recurso=self.cons,
        )

    def test_dos_estudios_rechaza_menos_de_60(self):
        ini = _aware(1, 10)
        self._turno(self.sala, ini, ini + timedelta(minutes=40))
        # gap 40 min entre fin e inicio del nuevo
        nuevo_ini = ini + timedelta(minutes=80)
        with pytest.raises(SeparacionPacienteError, match='60 minutos'):
            validar_separacion_paciente(
                paciente=self.paciente,
                inicio=nuevo_ini,
                fin=nuevo_ini + timedelta(minutes=40),
                recurso=self.sala,
            )

    def test_dos_estudios_permite_60(self):
        ini = _aware(1, 10)
        self._turno(self.sala, ini, ini + timedelta(minutes=40))
        nuevo_ini = ini + timedelta(minutes=100)  # gap 60
        validar_separacion_paciente(
            paciente=self.paciente,
            inicio=nuevo_ini,
            fin=nuevo_ini + timedelta(minutes=40),
            recurso=self.sala,
        )

    def test_consulta_y_estudio_usa_60(self):
        ini = _aware(2, 11)
        self._turno(self.cons, ini, ini + timedelta(minutes=20))
        nuevo_ini = ini + timedelta(minutes=50)  # gap 30 < 60
        with pytest.raises(SeparacionPacienteError, match='60 minutos'):
            validar_separacion_paciente(
                paciente=self.paciente,
                inicio=nuevo_ini,
                fin=nuevo_ini + timedelta(minutes=40),
                recurso=self.sala,
            )
        ok_ini = ini + timedelta(minutes=80)  # gap 60
        validar_separacion_paciente(
            paciente=self.paciente,
            inicio=ok_ini,
            fin=ok_ini + timedelta(minutes=40),
            recurso=self.sala,
        )

    def test_excluye_turno_al_reprogramar(self):
        ini = _aware(3, 9)
        t = self._turno(self.cons, ini, ini + timedelta(minutes=20))
        # Mismo horario al reprogramar (excluye el propio) no choca.
        validar_separacion_paciente(
            paciente=self.paciente,
            inicio=ini,
            fin=ini + timedelta(minutes=20),
            recurso=self.cons,
            excluir_turno_id=t.pk,
        )


@pytest.mark.django_db
class TestSeparacionPacienteAPI:
    def setup_method(self):
        esp = Especialidad.objects.create(nombre='Sep API Esp')
        self.medico = Medico.objects.create(
            nombre='Dr', apellido='ApiSep', matricula='SEP-API-M', especialidad=esp,
        )
        self.paciente = Paciente.objects.create(
            dni='SEP-API-P', nombre='Pac', apellido='Api',
        )
        self.cons = Recurso.objects.create(
            nombre='Cons API Sep',
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )
        self.sala = Recurso.objects.create(
            nombre='Sala API Sep',
            tipo_recurso=Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
            activo=True,
        )
        for dia in range(7):
            DisponibilidadMedico.objects.create(
                medico=self.medico,
                dia_semana=dia,
                hora_inicio=dt_time(8, 0),
                hora_fin=dt_time(18, 0),
                tipo='CONSULTA',
                recurso=self.cons,
                activo=True,
            )
        self.admin = User.objects.create_user(
            username='sep_api_adm', password='x', rol='admin', is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _crear(self, recurso, inicio, fin, estado=Turno.Estado.CONFIRMADO):
        return Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=recurso,
            fecha_hora_inicio=inicio,
            fecha_hora_fin=fin,
            estado=estado,
        )

    def test_staff_post_rechaza_consulta_cerca(self):
        ini = _aware(0, 9)
        self._crear(self.cons, ini, ini + timedelta(minutes=20))
        cerca = ini + timedelta(minutes=40)
        r = self.client.post(
            '/api/turnos/',
            {
                'paciente_id': self.paciente.id,
                'medico_id': self.medico.id,
                'recurso_id': self.cons.id,
                'fecha_hora_inicio': cerca.isoformat(),
                'fecha_hora_fin': (cerca + timedelta(minutes=20)).isoformat(),
                'estado': Turno.Estado.CONFIRMADO,
            },
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert '30' in str(r.data)

    def test_staff_post_rechaza_dos_estudios_cerca(self):
        ini = _aware(1, 10)
        self._crear(self.sala, ini, ini + timedelta(minutes=40))
        cerca = ini + timedelta(minutes=80)  # gap 40 < 60
        r = self.client.post(
            '/api/turnos/',
            {
                'paciente_id': self.paciente.id,
                'medico_id': self.medico.id,
                'recurso_id': self.sala.id,
                'fecha_hora_inicio': cerca.isoformat(),
                'fecha_hora_fin': (cerca + timedelta(minutes=40)).isoformat(),
                'estado': Turno.Estado.CONFIRMADO,
            },
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert '60' in str(r.data)

    def test_staff_post_rechaza_consulta_cerca_de_estudio(self):
        ini = _aware(2, 11)
        self._crear(self.sala, ini, ini + timedelta(minutes=40))
        cerca = ini + timedelta(minutes=70)  # gap 30 < 60
        r = self.client.post(
            '/api/turnos/',
            {
                'paciente_id': self.paciente.id,
                'medico_id': self.medico.id,
                'recurso_id': self.cons.id,
                'fecha_hora_inicio': cerca.isoformat(),
                'fecha_hora_fin': (cerca + timedelta(minutes=20)).isoformat(),
                'estado': Turno.Estado.CONFIRMADO,
            },
            format='json',
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert '60' in str(r.data)

    def test_staff_reprogramar_consulta_rechaza_cerca(self):
        from turnos import turno_estado

        ini = _aware(3, 9)
        self._crear(self.cons, ini, ini + timedelta(minutes=20))
        lejos = _aware(3, 14)
        a_mover = self._crear(self.cons, lejos, lejos + timedelta(minutes=20))
        destino = ini + timedelta(minutes=40)  # gap 20 < 30
        with pytest.raises(turno_estado.TurnoEstadoTransitionError, match='30 minutos'):
            turno_estado.reprogramar_turno(
                a_mover,
                actor=self.admin,
                fecha_hora_inicio=destino,
                fecha_hora_fin=destino + timedelta(minutes=20),
                motivo='Demasiado cerca de otra consulta',
                recurso=self.cons,
            )
