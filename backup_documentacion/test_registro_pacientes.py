#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from usuarios.models import User
from pacientes.models import Paciente

def test_registro_paciente():
    """Probar el endpoint de registro de pacientes"""
    
    print("🧪 PROBANDO SISTEMA DE REGISTRO DE PACIENTES")
    print("=" * 50)
    
    # URL del endpoint
    url = "http://localhost:8000/api/auth/register/patient/"
    
    # Datos de prueba
    test_data = {
        "username": "paciente_test",
        "email": "paciente.test@email.com",
        "password": "Test123456",
        "password2": "Test123456",
        "first_name": "Juan",
        "last_name": "Pérez",
        "telefono": "+1234567890",
        "dni": "12345678",
        "fecha_nacimiento": "1990-01-01",
        "genero": "M",
        "direccion": "Calle Test 123",
        "ciudad": "Ciudad Test",
        "codigo_postal": "1234",
        "grupo_sanguineo": "A+",
        "alergias": "Ninguna",
        "medicamentos_actuales": "Ninguno",
        "contacto_emergencia_nombre": "María Pérez",
        "contacto_emergencia_telefono": "+1234567891",
        "contacto_emergencia_relacion": "Madre",
        "antecedentes_personales": "Sin antecedentes",
        "antecedentes_familiares": "Sin antecedentes familiares"
    }
    
    try:
        print("📤 Enviando solicitud de registro...")
        response = requests.post(url, json=test_data)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Registro exitoso!")
            
            # Verificar que se creó el usuario
            try:
                user = User.objects.get(username="paciente_test")
                print(f"✅ Usuario creado: {user.username} (Rol: {user.rol})")
                
                # Verificar que se creó el paciente
                try:
                    paciente = Paciente.objects.get(user=user)
                    print(f"✅ Paciente creado: {paciente.dni}")
                    print(f"✅ Relación User-Paciente: {hasattr(user, 'paciente')}")
                except Paciente.DoesNotExist:
                    print("❌ Error: No se creó el modelo Paciente")
                    
            except User.DoesNotExist:
                print("❌ Error: No se creó el usuario")
                
        else:
            print("❌ Error en el registro")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se puede conectar al servidor")
        print("   Asegúrate de que Django esté ejecutándose en http://localhost:8000")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def verificar_usuarios_existentes():
    """Verificar usuarios existentes para evitar conflictos"""
    
    print("\n🔍 VERIFICANDO USUARIOS EXISTENTES")
    print("-" * 30)
    
    # Verificar username
    if User.objects.filter(username="paciente_test").exists():
        print("⚠️  El usuario 'paciente_test' ya existe")
        return False
    
    # Verificar email
    if User.objects.filter(email="paciente.test@email.com").exists():
        print("⚠️  El email 'paciente.test@email.com' ya existe")
        return False
    
    # Verificar DNI
    if Paciente.objects.filter(dni="12345678").exists():
        print("⚠️  El DNI '12345678' ya existe")
        return False
    
    print("✅ No hay conflictos con usuarios existentes")
    return True

def limpiar_datos_prueba():
    """Limpiar datos de prueba"""
    
    print("\n🧹 LIMPIANDO DATOS DE PRUEBA")
    print("-" * 30)
    
    try:
        # Eliminar usuario de prueba
        user = User.objects.filter(username="paciente_test").first()
        if user:
            user.delete()
            print("✅ Usuario de prueba eliminado")
        else:
            print("ℹ️  No se encontró usuario de prueba para eliminar")
            
    except Exception as e:
        print(f"❌ Error al limpiar datos: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Probar sistema de registro de pacientes')
    parser.add_argument('--clean', action='store_true', help='Limpiar datos de prueba antes de probar')
    parser.add_argument('--cleanup', action='store_true', help='Solo limpiar datos de prueba')
    
    args = parser.parse_args()
    
    if args.cleanup:
        limpiar_datos_prueba()
    else:
        if args.clean:
            limpiar_datos_prueba()
        
        if verificar_usuarios_existentes():
            test_registro_paciente()
        else:
            print("\n💡 Usa --clean para limpiar datos existentes antes de probar")
