"""
Tests para los modelos de la app medicos.
"""
import pytest
from django.db.utils import IntegrityError
from medicos.models import Medico, Especialidad, DisponibilidadMedico, ExcepcionMedico
from datetime import time


@pytest.mark.django_db
class TestMedicoModel:
    """Tests para el modelo Medico."""
    
    def test_matricula_unique_constraint(self):
        """
        Test Integridad: Intenta crear dos médicos con la misma matrícula
        y asegura que lance IntegrityError.
        """
        # Nombre único para no chocar con especialidades precargadas por migraciones
        esp_nombre = 'Cardiología Test Matricula Unique'
        especialidad = Especialidad.objects.create(
            nombre=esp_nombre,
            descripcion='Especialidad en cardiología'
        )
        
        # Crear primer médico
        Medico.objects.create(
            matricula='MAT-001',
            nombre='Juan',
            apellido='García',
            especialidad=especialidad
        )
        
        # Intentar crear segundo médico con la misma matrícula debería fallar
        with pytest.raises(IntegrityError):
            Medico.objects.create(
                matricula='MAT-001',
                nombre='Pedro',
                apellido='López',
                especialidad=especialidad
            )
    
    def test_especialidad_set_null_al_borrar(self):
        """
        Test Relación: Verifica que al borrar una Especialidad,
        el campo especialidad del médico pase a NULL (no borre al médico).
        """
        esp_nombre = 'Neurología Test Set Null'
        especialidad = Especialidad.objects.create(
            nombre=esp_nombre,
            descripcion='Especialidad en neurología'
        )
        
        # Crear médico con esa especialidad
        medico = Medico.objects.create(
            matricula='MAT-002',
            nombre='María',
            apellido='Rodríguez',
            especialidad=especialidad
        )
        
        # Verificar que el médico tiene la especialidad
        assert medico.especialidad == especialidad
        assert medico.especialidad.nombre == esp_nombre
        
        # Guardar el ID del médico para verificar que no se borra
        medico_id = medico.id
        
        # Borrar la especialidad
        especialidad.delete()
        
        # Refrescar el médico desde la base de datos
        medico.refresh_from_db()
        
        # Verificar que el médico sigue existiendo
        assert Medico.objects.filter(id=medico_id).exists()
        
        # Verificar que el campo especialidad es NULL
        assert medico.especialidad is None
    
    def test_nombre_completo_con_nombre_y_apellido(self):
        """Test que nombre_completo funciona correctamente con nombre y apellido."""
        medico = Medico.objects.create(
            matricula='MAT-003',
            nombre='Carlos',
            apellido='Fernández'
        )
        
        assert medico.nombre_completo == 'Carlos Fernández'
    
    def test_nombre_completo_sin_nombre_usa_id(self):
        """Test que nombre_completo usa ID como fallback si no hay nombre/apellido."""
        medico = Medico.objects.create(
            matricula='MAT-004'
        )
        
        assert medico.nombre_completo == f'Médico {medico.id}'


@pytest.mark.django_db
class TestEspecialidadModel:
    """Tests para el modelo Especialidad."""
    
    def test_especialidad_nombre_unique(self):
        """Test que el nombre de especialidad debe ser único."""
        dup_nombre = 'Pediatría Test Nombre Unique'
        Especialidad.objects.create(
            nombre=dup_nombre,
            descripcion='Especialidad en pediatría'
        )
        
        # Intentar crear otra especialidad con el mismo nombre debería fallar
        with pytest.raises(IntegrityError):
            Especialidad.objects.create(
                nombre=dup_nombre,
                descripcion='Otra descripción'
            )


@pytest.mark.django_db
class TestDisponibilidadMedicoModel:
    """Tests para el modelo DisponibilidadMedico."""
    
    def test_crear_disponibilidad_medico(self):
        """Test crear una disponibilidad para un médico."""
        medico = Medico.objects.create(
            matricula='MAT-005',
            nombre='Ana',
            apellido='Martínez'
        )
        
        disponibilidad = DisponibilidadMedico.objects.create(
            medico=medico,
            dia_semana=0,  # Lunes
            hora_inicio=time(8, 0),
            hora_fin=time(17, 0),
            duracion_slot_min=30,
            activo=True
        )
        
        assert disponibilidad.medico == medico
        assert disponibilidad.dia_semana == 0
        assert disponibilidad.hora_inicio == time(8, 0)
        assert disponibilidad.hora_fin == time(17, 0)
        assert disponibilidad.duracion_slot_min == 30
        assert disponibilidad.activo is True


@pytest.mark.django_db
class TestExcepcionMedicoModel:
    """Tests para el modelo ExcepcionMedico."""
    
    def test_crear_excepcion_bloqueo(self):
        """Test crear una excepción de tipo BLOQUEO."""
        medico = Medico.objects.create(
            matricula='MAT-006',
            nombre='Luis',
            apellido='Sánchez'
        )
        
        from datetime import date
        
        excepcion = ExcepcionMedico.objects.create(
            medico=medico,
            fecha=date.today(),
            tipo='BLOQUEO',
            motivo='Vacaciones'
        )
        
        assert excepcion.medico == medico
        assert excepcion.tipo == 'BLOQUEO'
        assert excepcion.motivo == 'Vacaciones'
        assert excepcion.hora_inicio is None
        assert excepcion.hora_fin is None
    
    def test_crear_excepcion_ajuste_horario(self):
        """Test crear una excepción de tipo AJUSTE."""
        medico = Medico.objects.create(
            matricula='MAT-007',
            nombre='Laura',
            apellido='Gómez'
        )
        
        from datetime import date
        
        excepcion = ExcepcionMedico.objects.create(
            medico=medico,
            fecha=date.today(),
            tipo='AJUSTE',
            hora_inicio=time(10, 0),
            hora_fin=time(14, 0),
            motivo='Reunión médica'
        )
        
        assert excepcion.medico == medico
        assert excepcion.tipo == 'AJUSTE'
        assert excepcion.hora_inicio == time(10, 0)
        assert excepcion.hora_fin == time(14, 0)
        assert excepcion.motivo == 'Reunión médica'



