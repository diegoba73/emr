#!/usr/bin/env python
"""
Script para configurar los grupos del sistema EMR
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from pacientes.models import Paciente
from medicos.models import Medico
from turnos.models import Turno
from historias_clinicas.models import HistoriaClinica
from laboratorio.models import SolicitudExamen

def setup_groups():
    """
    Configurar los grupos del sistema
    """
    print("🔧 Configurando grupos del sistema...")
    
    # Crear grupos
    grupos = {
        'Secretarias': {
            'description': 'Secretarias que gestionan turnos y pacientes',
            'permissions': [
                'pacientes.view_paciente',
                'pacientes.add_paciente',
                'pacientes.change_paciente',
                'medicos.view_medico',
                'turnos.view_turno',
                'turnos.add_turno',
                'turnos.change_turno',
                'turnos.delete_turno',
                'laboratorio.view_solicitudexamen',
                'laboratorio.add_solicitudexamen',
                'laboratorio.change_solicitudexamen',
            ]
        },
        'Médicos': {
            'description': 'Médicos que atienden pacientes',
            'permissions': [
                'pacientes.view_paciente',
                'medicos.view_medico',
                'turnos.view_turno',
                'turnos.change_turno',
                'historias_clinicas.view_historiaclinica',
                'historias_clinicas.add_historiaclinica',
                'historias_clinicas.change_historiaclinica',
                'laboratorio.view_solicitudexamen',
                'laboratorio.add_solicitudexamen',
            ]
        },
        'Pacientes': {
            'description': 'Pacientes que consultan el sistema',
            'permissions': [
                'pacientes.view_paciente',
                'turnos.view_turno',
                'historias_clinicas.view_historiaclinica',
                'laboratorio.view_solicitudexamen',
            ]
        }
    }
    
    for nombre_grupo, config in grupos.items():
        grupo, created = Group.objects.get_or_create(name=nombre_grupo)
        
        if created:
            print(f"✅ Grupo '{nombre_grupo}' creado")
        else:
            print(f"ℹ️  Grupo '{nombre_grupo}' ya existe")
        
        # Asignar permisos
        permisos_asignados = []
        for perm_codigo in config['permissions']:
            try:
                app_label, codename = perm_codigo.split('.')
                perm = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                grupo.permissions.add(perm)
                permisos_asignados.append(perm_codigo)
            except Permission.DoesNotExist:
                print(f"⚠️  Permiso '{perm_codigo}' no encontrado")
        
        print(f"   📋 Permisos asignados: {len(permisos_asignados)}")
    
    print("\n🎉 Grupos configurados exitosamente!")

def create_test_users():
    """
    Crear usuarios de prueba (opcional)
    """
    print("\n👥 Creando usuarios de prueba...")
    
    from django.contrib.auth.models import User
    
    # Usuario secretaria
    secretaria, created = User.objects.get_or_create(
        username='secretaria1',
        defaults={
            'email': 'secretaria1@emr.com',
            'first_name': 'María',
            'last_name': 'González',
            'is_staff': True,
        }
    )
    if created:
        secretaria.set_password('secretaria123')
        secretaria.save()
        secretaria.groups.add(Group.objects.get(name='Secretarias'))
        print("✅ Usuario secretaria creado: secretaria1 / secretaria123")
    
    # Usuario médico
    medico, created = User.objects.get_or_create(
        username='medico1',
        defaults={
            'email': 'medico1@emr.com',
            'first_name': 'Dr. Juan',
            'last_name': 'Pérez',
            'is_staff': True,
        }
    )
    if created:
        medico.set_password('medico123')
        medico.save()
        medico.groups.add(Group.objects.get(name='Médicos'))
        print("✅ Usuario médico creado: medico1 / medico123")
    
    # Usuario paciente
    paciente, created = User.objects.get_or_create(
        username='paciente1',
        defaults={
            'email': 'paciente1@emr.com',
            'first_name': 'Ana',
            'last_name': 'López',
        }
    )
    if created:
        paciente.set_password('paciente123')
        paciente.save()
        paciente.groups.add(Group.objects.get(name='Pacientes'))
        print("✅ Usuario paciente creado: paciente1 / paciente123")

if __name__ == '__main__':
    print("🚀 Configurando sistema de autenticación...")
    
    setup_groups()
    
    # Preguntar si crear usuarios de prueba
    response = input("\n¿Deseas crear usuarios de prueba? (s/n): ").lower()
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        create_test_users()
    
    print("\n🎉 Sistema de autenticación configurado!")
    print("\n📋 Próximos pasos:")
    print("   1. Ir al Django Admin: http://127.0.0.1:8000/admin/")
    print("   2. Crear usuarios y asignarlos a grupos")
    print("   3. Probar las APIs de autenticación")
    print("   4. Implementar login en React")
