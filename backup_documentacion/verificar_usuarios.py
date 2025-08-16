#!/usr/bin/env python3
"""
Script para verificar usuarios médicos en el sistema
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from usuarios.models import User, UserProfile

def verificar_usuarios():
    print("🔍 Verificando usuarios en el sistema...")
    print("=" * 50)
    
    # Verificar usuarios
    try:
        usuarios = User.objects.all()
        print(f"📊 Total de usuarios: {usuarios.count()}")
        
        for user in usuarios:
            print(f"\n👤 Usuario: {user.username}")
            print(f"   Nombre: {user.first_name} {user.last_name}")
            print(f"   Email: {user.email}")
            print(f"   Rol: {user.rol}")
            print(f"   Activo: {user.is_active}")
            
            # Verificar si es médico
            if user.rol == 'medico':
                try:
                    medico = user.medico
                    print(f"   🏥 Médico: Dr. {medico.nombre} {medico.apellido}")
                    print(f"   📋 Matrícula: {medico.matricula}")
                    print(f"   🏥 Especialidad: {medico.especialidad.nombre}")
                except:
                    print(f"   ⚠️ No tiene perfil de médico asociado")
            
            # Verificar si es paciente
            elif user.rol == 'paciente':
                try:
                    paciente = user.paciente
                    print(f"   👤 Paciente: {paciente.nombre} {paciente.apellido}")
                    print(f"   🆔 DNI: {paciente.dni}")
                except:
                    print(f"   ⚠️ No tiene perfil de paciente asociado")
    
    except Exception as e:
        print(f"❌ Error accediendo a usuarios: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Usuarios médicos disponibles para login:")
    
    medicos = User.objects.filter(rol='medico')
    if medicos.exists():
        for user in medicos:
            print(f"   👨‍⚕️ {user.username} - {user.first_name} {user.last_name}")
    else:
        print("   ⚠️ No hay usuarios médicos registrados")
    
    print("\n🔧 Para crear un médico de prueba:")
    print("1. Ve a http://localhost:3000/register")
    print("2. Selecciona 'Registrar como Médico'")
    print("3. Completa el formulario")
    print("4. O usa el comando: python manage.py createsuperuser")

if __name__ == "__main__":
    verificar_usuarios()
