#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from usuarios.models import User, Secretaria
from medicos.models import Medico, Especialidad
from pacientes.models import Paciente

def completar_integracion():
    print("🔧 COMPLETANDO INTEGRACIÓN DE USUARIOS")
    print("=" * 50)
    
    # 1. Crear modelos faltantes para usuarios médicos
    print("\n👨‍⚕️ CREANDO MODELOS MÉDICOS FALTANTES:")
    print("-" * 40)
    
    users_medico_sin_modelo = User.objects.filter(rol='medico')
    for user in users_medico_sin_modelo:
        if not hasattr(user, 'medico'):
            # Obtener una especialidad por defecto
            especialidad_default = Especialidad.objects.first()
            if not especialidad_default:
                especialidad_default = Especialidad.objects.create(
                    nombre="Medicina General",
                    descripcion="Especialidad de medicina general"
                )
            
            # Crear el modelo Medico
            medico = Medico.objects.create(
                user=user,
                matricula=f"MP{user.id:05d}",
                especialidad=especialidad_default,
                areas_interes_ia="Áreas de interés general"
            )
            print(f"✅ Creado médico para {user.username}: {user.first_name} {user.last_name}")
    
    # 2. Crear modelos faltantes para usuarios pacientes
    print("\n👤 CREANDO MODELOS PACIENTES FALTANTES:")
    print("-" * 40)
    
    users_paciente_sin_modelo = User.objects.filter(rol='paciente')
    for user in users_paciente_sin_modelo:
        if not hasattr(user, 'paciente'):
            # Crear el modelo Paciente
            paciente = Paciente.objects.create(
                user=user,
                dni=f"DNI{user.id:06d}",
                antecedentes_personales="Sin antecedentes registrados",
                antecedentes_familiares="Sin antecedentes familiares registrados"
            )
            print(f"✅ Creado paciente para {user.username}: {user.first_name} {user.last_name}")
    
    # 3. Crear algunos usuarios de secretaria de ejemplo
    print("\n👩‍💼 CREANDO USUARIOS DE SECRETARIA:")
    print("-" * 40)
    
    # Crear usuarios de secretaria
    secretarias_data = [
        {
            'username': 'secretaria1',
            'first_name': 'María',
            'last_name': 'González',
            'email': 'maria.gonzalez@hospital.com',
            'telefono': '+1234567890',
            'legajo': 'SEC001',
            'sector': 'Recepción'
        },
        {
            'username': 'secretaria2',
            'first_name': 'Carmen',
            'last_name': 'López',
            'email': 'carmen.lopez@hospital.com',
            'telefono': '+1234567891',
            'legajo': 'SEC002',
            'sector': 'Turnos'
        }
    ]
    
    for sec_data in secretarias_data:
        # Crear usuario
        user, created = User.objects.get_or_create(
            username=sec_data['username'],
            defaults={
                'first_name': sec_data['first_name'],
                'last_name': sec_data['last_name'],
                'email': sec_data['email'],
                'telefono': sec_data['telefono'],
                'rol': 'secretaria'
            }
        )
        
        if created:
            # Establecer contraseña
            user.set_password('changeme123')
            user.save()
            print(f"✅ Creado usuario secretaria: {user.username}")
        
        # Crear modelo Secretaria
        if not hasattr(user, 'secretaria'):
            secretaria = Secretaria.objects.create(
                user=user,
                legajo=sec_data['legajo'],
                sector=sec_data['sector']
            )
            print(f"✅ Creado modelo Secretaria para {user.username}")
    
    # 4. Crear algunos pacientes de ejemplo
    print("\n👤 CREANDO PACIENTES DE EJEMPLO:")
    print("-" * 40)
    
    pacientes_data = [
        {
            'username': 'paciente1',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan.perez@email.com',
            'telefono': '+1234567892',
            'dni': 'DNI12345678',
            'antecedentes_personales': 'Hipertensión arterial',
            'antecedentes_familiares': 'Diabetes en familia'
        },
        {
            'username': 'paciente2',
            'first_name': 'Ana',
            'last_name': 'Martínez',
            'email': 'ana.martinez@email.com',
            'telefono': '+1234567893',
            'dni': 'DNI87654321',
            'antecedentes_personales': 'Alergia a penicilina',
            'antecedentes_familiares': 'Sin antecedentes relevantes'
        },
        {
            'username': 'paciente3',
            'first_name': 'Carlos',
            'last_name': 'Rodríguez',
            'email': 'carlos.rodriguez@email.com',
            'telefono': '+1234567894',
            'dni': 'DNI11223344',
            'antecedentes_personales': 'Asma bronquial',
            'antecedentes_familiares': 'Asma en madre'
        }
    ]
    
    for pac_data in pacientes_data:
        # Crear usuario
        user, created = User.objects.get_or_create(
            username=pac_data['username'],
            defaults={
                'first_name': pac_data['first_name'],
                'last_name': pac_data['last_name'],
                'email': pac_data['email'],
                'telefono': pac_data['telefono'],
                'rol': 'paciente'
            }
        )
        
        if created:
            # Establecer contraseña
            user.set_password('changeme123')
            user.save()
            print(f"✅ Creado usuario paciente: {user.username}")
        
        # Crear modelo Paciente
        if not hasattr(user, 'paciente'):
            paciente = Paciente.objects.create(
                user=user,
                dni=pac_data['dni'],
                antecedentes_personales=pac_data['antecedentes_personales'],
                antecedentes_familiares=pac_data['antecedentes_familiares']
            )
            print(f"✅ Creado modelo Paciente para {user.username}")
    
    print("\n🎉 INTEGRACIÓN COMPLETADA EXITOSAMENTE!")
    print("=" * 50)

if __name__ == "__main__":
    completar_integracion()
