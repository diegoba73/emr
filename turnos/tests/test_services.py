"""
Tests para el Service Layer de AtencionService.

Tests de la lógica de negocio de transiciones de Turno a Atención.
"""

from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from turnos.models import Turno, Atencion, ConsultaAmbulatoria, RegistroProcedimiento, RegistroQuirurgico, Recurso
from auditoria.models import AuditEvent

from turnos.services import AtencionService, BusinessLogicError
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad

User = get_user_model()


class TestAtencionServiceHappyPath(TestCase):
    """Tests del Happy Path para iniciar_atencion_desde_turno."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.especialidad, _ = Especialidad.objects.get_or_create(nombre="Cardiología")
        
        self.user_medico = User.objects.create_user(
            username='medico_test',
            email='medico@test.com',
            password='testpass123',
            first_name='Dr. Juan',
            last_name='Pérez',
            rol='medico'
        )
        self.medico = Medico.objects.create(
            user=self.user_medico,
            nombre='Juan',
            apellido='Pérez',
            matricula='12345',
            especialidad=self.especialidad
        )
        
        self.user_paciente = User.objects.create_user(
            username='12345678',
            email='paciente@test.com',
            password='testpass123',
            first_name='Ana',
            last_name='García',
            rol='paciente'
        )
        self.paciente = Paciente.objects.create(
            user=self.user_paciente,
            dni='12345678',
            nombre='Ana',
            apellido='García',
            fecha_nacimiento='1990-01-01',
            email='paciente@test.com'
        )
        
        self.recurso_consultorio = Recurso.objects.create(
            nombre='Consultorio 1',
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True
        )
        
        self.recurso_sala_procedimiento = Recurso.objects.create(
            nombre='Sala Procedimiento 1',
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
            activo=True
        )
        
        self.recurso_quirofano = Recurso.objects.create(
            nombre='Quirófano 1',
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.QUIROFANO,
            activo=True
        )

    def test_iniciar_atencion_desde_turno_consultorio(self):
        """
        Happy Path: Crear atención desde turno de tipo CONSULTORIO.
        
        Verifica que:
        - El turno cambie de estado a REALIZADO
        - Se cree la Atencion
        - Se cree la ConsultaAmbulatoria asociada
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso_consultorio,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado='CONFIRMADO',
            motivo_reserva='Consulta de prueba'
        )
        turno_id = turno.id
        estado_inicial = turno.estado
        
        # Ejecutar el servicio
        atencion = AtencionService.iniciar_atencion_desde_turno(turno_id).atencion
        
        # Verificar que la atención se creó
        self.assertIsNotNone(atencion)
        self.assertIsNotNone(atencion.id)
        self.assertEqual(atencion.turno_id, turno_id)
        self.assertEqual(atencion.paciente, self.paciente)
        self.assertEqual(atencion.medico_principal, self.medico)
        self.assertEqual(atencion.tipo_atencion, Recurso.TipoRecurso.CONSULTORIO)
        self.assertEqual(atencion.tipo_intervencion, Atencion.TipoIntervencion.CONSULTA)
        self.assertEqual(atencion.estado_clinico, Atencion.EstadoClinico.ABIERTA)
        
        # Verificar que el turno cambió de estado
        turno.refresh_from_db()
        self.assertEqual(turno.estado, 'REALIZADO')
        
        # Verificar que existe la ConsultaAmbulatoria
        consulta = ConsultaAmbulatoria.objects.get(atencion=atencion)
        self.assertIsNotNone(consulta)
        self.assertEqual(consulta.atencion_id, atencion.id)

    def test_iniciar_atencion_desde_turno_sala_procedimiento(self):
        """
        Happy Path: Crear atención desde turno de tipo SALA_PROCEDIMIENTO.
        
        Verifica que se cree el RegistroProcedimiento asociado.
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso_sala_procedimiento,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado='CONFIRMADO'
        )
        
        # Ejecutar el servicio
        atencion = AtencionService.iniciar_atencion_desde_turno(turno.id).atencion
        
        # Verificar que la atención se creó
        self.assertEqual(atencion.tipo_atencion, Recurso.TipoRecurso.SALA_PROCEDIMIENTO)
        self.assertEqual(atencion.tipo_intervencion, Atencion.TipoIntervencion.ESTUDIO)
        
        # Verificar que existe el RegistroProcedimiento
        registro = RegistroProcedimiento.objects.get(atencion=atencion)
        self.assertIsNotNone(registro)
        self.assertEqual(registro.atencion_id, atencion.id)

    def test_iniciar_atencion_desde_turno_quirofano(self):
        """
        Happy Path: Crear atención desde turno de tipo QUIROFANO.
        
        Verifica que se cree el RegistroQuirurgico asociado.
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso_quirofano,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=2),
            estado='CONFIRMADO'
        )
        
        # Ejecutar el servicio
        atencion = AtencionService.iniciar_atencion_desde_turno(turno.id).atencion
        
        # Verificar que la atención se creó
        self.assertEqual(atencion.tipo_atencion, Recurso.TipoRecurso.QUIROFANO)
        self.assertEqual(atencion.tipo_intervencion, Atencion.TipoIntervencion.CIRUGIA)
        
        # Verificar que existe el RegistroQuirurgico
        registro = RegistroQuirurgico.objects.get(atencion=atencion)
        self.assertIsNotNone(registro)
        self.assertEqual(registro.atencion_id, atencion.id)
        self.assertEqual(registro.anestesista, atencion.medico_principal)

    def test_iniciar_atencion_desde_turno_reservado(self):
        """
        Happy Path: Crear atención desde turno en estado RESERVADO.
        
        Verifica que también funciona con turnos en estado RESERVADO.
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso_consultorio,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado='RESERVADO',
            motivo_reserva='Consulta de prueba'
        )
        turno_id = turno.id
        
        # Ejecutar el servicio
        atencion = AtencionService.iniciar_atencion_desde_turno(turno_id).atencion
        
        # Verificar que la atención se creó
        self.assertIsNotNone(atencion)
        
        # Verificar que el turno cambió a REALIZADO
        turno.refresh_from_db()
        self.assertEqual(turno.estado, 'REALIZADO')


class TestAtencionServiceEdgeCases(TestCase):
    """Tests de Edge Cases para iniciar_atencion_desde_turno."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.especialidad, _ = Especialidad.objects.get_or_create(nombre="Cardiología")
        
        self.user_medico = User.objects.create_user(
            username='medico_test',
            email='medico@test.com',
            password='testpass123',
            first_name='Dr. Juan',
            last_name='Pérez',
            rol='medico'
        )
        self.medico = Medico.objects.create(
            user=self.user_medico,
            nombre='Juan',
            apellido='Pérez',
            matricula='12345',
            especialidad=self.especialidad
        )
        
        self.user_paciente = User.objects.create_user(
            username='12345678',
            email='paciente@test.com',
            password='testpass123',
            first_name='Ana',
            last_name='García',
            rol='paciente'
        )
        self.paciente = Paciente.objects.create(
            user=self.user_paciente,
            dni='12345678',
            nombre='Ana',
            apellido='García',
            fecha_nacimiento='1990-01-01',
            email='paciente@test.com'
        )
        
        self.recurso_consultorio = Recurso.objects.create(
            nombre='Consultorio 1',
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True
        )

    def test_iniciar_atencion_turno_ya_tiene_atencion(self):
        """
        Edge Case 1: Intentar iniciar atención de un turno que ya tiene atención (debe fallar).
        
        Verifica que se lance BusinessLogicError y no se cree una segunda atención.
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso_consultorio,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado='CONFIRMADO',
            motivo_reserva='Consulta de prueba'
        )
        turno_id = turno.id
        
        # Crear una atención existente para el turno
        atencion_existente = Atencion.objects.create(
            turno=turno,
            paciente=self.paciente,
            medico_principal=self.medico,
            tipo_atencion=Recurso.TipoRecurso.CONSULTORIO,
            tipo_intervencion=Atencion.TipoIntervencion.CONSULTA
        )
        
        # Intentar iniciar otra atención debería fallar
        with self.assertRaises(BusinessLogicError) as context:
            AtencionService.iniciar_atencion_desde_turno(turno_id)
        
        self.assertIn("ya tiene una atención asociada", str(context.exception))
        
        # Verificar que no se creó una segunda atención
        atenciones = Atencion.objects.filter(turno=turno)
        self.assertEqual(atenciones.count(), 1)
        self.assertEqual(atenciones.first().id, atencion_existente.id)

    def test_iniciar_atencion_turno_cancelado(self):
        """
        Edge Case 2: Intentar iniciar atención de un turno cancelado (debe fallar).
        
        Verifica que se lance BusinessLogicError.
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso_consultorio,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado='CANCELADO',
            motivo_reserva='Consulta cancelada'
        )
        turno_id = turno.id
        
        # Intentar iniciar atención debería fallar
        with self.assertRaises(BusinessLogicError) as context:
            AtencionService.iniciar_atencion_desde_turno(turno_id)
        
        error_message = str(context.exception)
        self.assertIn("CANCELADO", error_message)
        self.assertIn("Solo se pueden iniciar atenciones desde turnos en estado", error_message)
        
        # Verificar que no se creó ninguna atención
        self.assertFalse(Atencion.objects.filter(turno=turno).exists())

    def test_iniciar_atencion_turno_no_existe(self):
        """
        Edge Case: Intentar iniciar atención de un turno que no existe (debe fallar).
        
        Verifica que se lance BusinessLogicError.
        """
        turno_id_inexistente = 99999
        
        with self.assertRaises(BusinessLogicError) as context:
            AtencionService.iniciar_atencion_desde_turno(turno_id_inexistente)
        
        self.assertIn("no existe", str(context.exception))

    def test_iniciar_atencion_turno_sin_paciente(self):
        """
        Edge Case: Intentar iniciar atención de un turno sin paciente (debe fallar).
        
        Verifica que se lance BusinessLogicError.
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=None,  # Sin paciente
            medico=self.medico,
            recurso=self.recurso_consultorio,
            fecha_hora_inicio=fecha_inicio,
            estado='CONFIRMADO'
        )
        
        with self.assertRaises(BusinessLogicError) as context:
            AtencionService.iniciar_atencion_desde_turno(turno.id)
        
        self.assertIn("no tiene un paciente asociado", str(context.exception))

    def test_iniciar_atencion_turno_sin_medico(self):
        """
        Edge Case: Intentar iniciar atención de un turno sin médico (debe fallar).
        
        Verifica que se lance BusinessLogicError.
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=None,  # Sin médico
            recurso=self.recurso_consultorio,
            fecha_hora_inicio=fecha_inicio,
            estado='CONFIRMADO'
        )
        
        with self.assertRaises(BusinessLogicError) as context:
            AtencionService.iniciar_atencion_desde_turno(turno.id)
        
        self.assertIn("no tiene un médico asociado", str(context.exception))

    def test_iniciar_atencion_turno_sin_recurso(self):
        """
        Edge Case: Intentar iniciar atención de un turno sin recurso (debe fallar).
        
        Verifica que se lance BusinessLogicError.
        """
        fecha_inicio = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=None,  # Sin recurso
            fecha_hora_inicio=fecha_inicio,
            estado='CONFIRMADO'
        )
        
        with self.assertRaises(BusinessLogicError) as context:
            AtencionService.iniciar_atencion_desde_turno(turno.id)
        
        self.assertIn("no tiene un recurso asociado", str(context.exception))


class TestAtencionServiceApiPostCompat(TestCase):
    """Compatibilidad con POST /api/atenciones/ (api_post_compat=True): idempotencia, auditoría, atomic."""

    def setUp(self):
        self.especialidad, _ = Especialidad.objects.get_or_create(nombre="Cardiología ApiPost")
        self.actor = User.objects.create_user(
            username="actor_api_post",
            email="actor@test.com",
            password="secret",
            rol="medico",
        )
        self.medico = Medico.objects.create(
            user=self.actor,
            nombre="Ana",
            apellido="López",
            matricula="API01",
            especialidad=self.especialidad,
        )
        self.paciente = Paciente.objects.create(
            user=User.objects.create_user(
                username="paciente_api_post",
                email="pacap@test.com",
                password="secret",
                rol="paciente",
            ),
            dni="APIPOST01",
            nombre="Pac",
            apellido="Test",
            fecha_nacimiento="1990-01-01",
        )
        self.recurso = Recurso.objects.create(
            nombre="Consultorio ApiPost",
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

    def test_api_post_compat_crea_y_es_idempotente(self):
        fecha_inicio = timezone.now() + timedelta(days=3)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado="CONFIRMADO",
        )

        first = AtencionService.iniciar_atencion_desde_turno(
            turno.id,
            usuario_solicitante=self.actor,
            observaciones_generales="notas",
            api_post_compat=True,
            actor=self.actor,
        )
        self.assertTrue(first.created_new)

        second = AtencionService.iniciar_atencion_desde_turno(
            turno.id,
            usuario_solicitante=self.actor,
            api_post_compat=True,
            actor=self.actor,
        )
        self.assertFalse(second.created_new)
        self.assertEqual(first.atencion.id, second.atencion.id)

    def test_api_post_compat_auditoria_solo_en_alta_real(self):
        """Auditoría se persiste solo en alta real (idempotencia no audita).

        ``audit_service.log_event`` usa ``transaction.on_commit``: dentro de
        ``TestCase`` esos callbacks no disparan a menos que se capturen con
        ``captureOnCommitCallbacks(execute=True)``.
        """
        fecha_inicio = timezone.now() + timedelta(days=3)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado="CONFIRMADO",
        )

        before = AuditEvent.objects.count()

        with self.captureOnCommitCallbacks(execute=True):
            out1 = AtencionService.iniciar_atencion_desde_turno(
                turno.id,
                api_post_compat=True,
                actor=self.actor,
            )
        self.assertTrue(out1.created_new)
        after_first = AuditEvent.objects.count()
        self.assertGreater(after_first, before)

        with self.captureOnCommitCallbacks(execute=True):
            out2 = AtencionService.iniciar_atencion_desde_turno(
                turno.id,
                api_post_compat=True,
                actor=self.actor,
            )
        self.assertFalse(out2.created_new)
        self.assertEqual(AuditEvent.objects.count(), after_first)

    def test_orquestacion_roll_back_restaura_turno_si_falla_create(self):
        fecha_inicio = timezone.now() + timedelta(days=3)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado="CONFIRMADO",
        )
        estado_antes = turno.estado

        with patch.object(Atencion.objects, "create", side_effect=RuntimeError("simulated")):
            with self.assertRaises(RuntimeError):
                AtencionService.iniciar_atencion_desde_turno(turno.id)

        turno.refresh_from_db()
        self.assertEqual(turno.estado, estado_antes)
        self.assertFalse(Atencion.objects.filter(turno_id=turno.id).exists())

    def test_api_post_compat_roll_back_sin_fila_atencion_si_falla_create(self):
        fecha_inicio = timezone.now() + timedelta(days=3)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado="CONFIRMADO",
        )

        with patch.object(Atencion.objects, "create", side_effect=RuntimeError("simulated")):
            with self.assertRaises(RuntimeError):
                AtencionService.iniciar_atencion_desde_turno(
                    turno.id,
                    api_post_compat=True,
                    actor=self.actor,
                )

        self.assertFalse(Atencion.objects.filter(turno_id=turno.id).exists())


class TestAtencionServiceClinicaDesdeTurno(TestCase):
    """C5.10.1: iniciar_atencion_clinica_desde_turno — idempotente y REALIZADO."""

    def setUp(self):
        self.especialidad, _ = Especialidad.objects.get_or_create(nombre="Cardiología Clinica")
        self.medico = Medico.objects.create(
            nombre="Ana",
            apellido="Clin",
            matricula="CLIN01",
            especialidad=self.especialidad,
        )
        self.paciente = Paciente.objects.create(
            dni="CLINPAC01",
            nombre="Pac",
            apellido="Clin",
            fecha_nacimiento="1990-01-01",
        )
        self.recurso = Recurso.objects.create(
            nombre="Consultorio Clinica",
            ubicacion=Recurso.Ubicacion.ICPL,
            tipo_recurso=Recurso.TipoRecurso.CONSULTORIO,
            activo=True,
        )

    def test_clinica_idempotente_con_atencion_existente(self):
        fecha_inicio = timezone.now() + timedelta(days=4)
        turno = Turno.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            recurso=self.recurso,
            fecha_hora_inicio=fecha_inicio,
            fecha_hora_fin=fecha_inicio + timedelta(hours=1),
            estado="CONFIRMADO",
        )
        compat = AtencionService.iniciar_atencion_desde_turno(
            turno.id, api_post_compat=True,
        )
        turno.refresh_from_db()
        self.assertEqual(turno.estado, "CONFIRMADO")

        outcome = AtencionService.iniciar_atencion_clinica_desde_turno(turno)
        self.assertFalse(outcome.created_new)
        self.assertEqual(outcome.atencion.id, compat.atencion.id)
        turno.refresh_from_db()
        self.assertEqual(turno.estado, "REALIZADO")
        self.assertTrue(outcome.turno_estado_changed)
