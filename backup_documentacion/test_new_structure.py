#!/usr/bin/env python
"""
Script para probar la nueva estructura unificada
"""
import requests
import json

# Configuración
BASE_URL = 'http://127.0.0.1:8000/api'
SESSION = requests.Session()

def test_login_admin():
    """Probar login con admin"""
    print("🔐 Probando login con admin...")
    
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        response = SESSION.post(f'{BASE_URL}/auth/login/', json=login_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login exitoso!")
            print(f"Usuario: {data['user']['username']}")
            print(f"Rol: {data['user']['groups']}")
            return True
        else:
            print(f"❌ Login falló: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_register_patient():
    """Probar registro de paciente"""
    print("\n👤 Probando registro de paciente...")
    
    patient_data = {
        'username': 'paciente_test',
        'email': 'paciente@test.com',
        'password': 'test123',
        'first_name': 'Juan',
        'last_name': 'Pérez',
        'dni': '12345678',
        'telefono': '+1234567890',
        'fecha_nacimiento': '1990-01-01',
        'genero': 'M',
        'direccion': 'Calle Test 123',
        'ciudad': 'Buenos Aires',
        'codigo_postal': '1000',
        'grupo_sanguineo': 'A+',
        'alergias': 'Ninguna',
        'medicamentos_actuales': 'Ninguno',
        'antecedentes_personales': 'Ninguno',
        'antecedentes_familiares': 'Ninguno'
    }
    
    try:
        response = SESSION.post(f'{BASE_URL}/auth/register/patient/', json=patient_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Paciente registrado exitosamente!")
            print(f"User ID: {data['user_id']}")
            return True
        else:
            print(f"❌ Registro falló: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_register_doctor():
    """Probar registro de médico (requiere estar logueado como admin)"""
    print("\n👨‍⚕️ Probando registro de médico...")
    
    doctor_data = {
        'username': 'medico_test',
        'email': 'medico@test.com',
        'password': 'test123',
        'first_name': 'Dr. María',
        'last_name': 'González',
        'matricula': 'MED12345',
        'especialidad_id': 1,  # Asumiendo que existe la especialidad con ID 1
        'telefono': '+1234567890',
        'fecha_nacimiento': '1985-01-01',
        'genero': 'F',
        'direccion': 'Av. Médico 456',
        'ciudad': 'Buenos Aires',
        'codigo_postal': '1000',
        'areas_interes_ia': 'Cardiología'
    }
    
    try:
        response = SESSION.post(f'{BASE_URL}/auth/register/doctor/', json=doctor_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Médico registrado exitosamente!")
            print(f"User ID: {data['user_id']}")
            return True
        else:
            print(f"❌ Registro falló: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_register_secretary():
    """Probar registro de secretaria (requiere estar logueado como admin)"""
    print("\n👩‍💼 Probando registro de secretaria...")
    
    secretary_data = {
        'username': 'secretaria_test',
        'email': 'secretaria@test.com',
        'password': 'test123',
        'first_name': 'Ana',
        'last_name': 'López',
        'legajo': 'SEC12345',
        'telefono': '+1234567890',
        'fecha_nacimiento': '1992-01-01',
        'genero': 'F',
        'direccion': 'Calle Secretaria 789',
        'ciudad': 'Buenos Aires',
        'codigo_postal': '1000',
        'sector': 'Recepción'
    }
    
    try:
        response = SESSION.post(f'{BASE_URL}/auth/register/secretary/', json=secretary_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Secretaria registrada exitosamente!")
            print(f"User ID: {data['user_id']}")
            return True
        else:
            print(f"❌ Registro falló: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_users():
    """Probar listar usuarios"""
    print("\n👥 Probando listar usuarios...")
    
    try:
        response = SESSION.get(f'{BASE_URL}/auth/users/')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Usuarios obtenidos!")
            print(f"Total usuarios: {len(data)}")
            for user in data:
                print(f"  - {user['username']} ({user['first_name']} {user['last_name']}) - Rol: {user.get('groups', [])}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Probando nueva estructura unificada...")
    print("=" * 50)
    
    # Probar login con admin
    if test_login_admin():
        # Probar registro de paciente
        test_register_patient()
        
        # Probar registro de médico
        test_register_doctor()
        
        # Probar registro de secretaria
        test_register_secretary()
        
        # Probar listar usuarios
        test_list_users()
    else:
        print("\n❌ No se pudo hacer login con admin.")
        print("💡 Verifica que:")
        print("   1. El servidor Django esté corriendo en http://127.0.0.1:8000")
        print("   2. El superusuario admin exista")
    
    print("\n🎉 Pruebas completadas!")

if __name__ == '__main__':
    main()


