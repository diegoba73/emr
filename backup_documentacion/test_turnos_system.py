#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema de turnos
"""

import requests
import json
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://127.0.0.1:8000/api"
SESSION = requests.Session()

def get_csrf_token():
    """Obtener token CSRF"""
    try:
        response = SESSION.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 200:
            # El token CSRF se establece automáticamente en las cookies
            return True
        return False
    except:
        return False

def test_login(username, password):
    """Probar login con diferentes usuarios"""
    print(f"\n🔐 Probando login con usuario: {username}")
    
    # Primero obtener el token CSRF
    if not get_csrf_token():
        print("❌ No se pudo obtener el token CSRF")
        return False
    
    login_data = {
        "username": username,
        "password": password
    }
    
    try:
        response = SESSION.post(f"{BASE_URL}/auth/login/", json=login_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login exitoso")
            print(f"Usuario: {data.get('username')}")
            print(f"Rol: {data.get('rol')}")
            return True
        else:
            print(f"❌ Login fallido: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return False

def test_current_user():
    """Obtener información del usuario actual"""
    print(f"\n👤 Obteniendo información del usuario actual...")
    
    try:
        response = SESSION.get(f"{BASE_URL}/auth/current-user/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Usuario actual obtenido")
            print(f"Username: {data.get('username')}")
            print(f"Rol: {data.get('rol')}")
            if data.get('paciente'):
                print(f"Paciente: {data.get('paciente', {}).get('nombre')} {data.get('paciente', {}).get('apellido')}")
            return data
        else:
            print(f"❌ Error obteniendo usuario: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_get_data():
    """Obtener datos de pacientes, médicos y especialidades"""
    print(f"\n📊 Obteniendo datos del sistema...")
    
    endpoints = [
        ("pacientes", "/pacientes/"),
        ("médicos", "/medicos/"),
        ("especialidades", "/especialidades/"),
        ("turnos", "/turnos/")
    ]
    
    results = {}
    
    for name, endpoint in endpoints:
        try:
            response = SESSION.get(f"{BASE_URL}{endpoint}")
            print(f"Status {name}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                print(f"✅ {name.capitalize()}: {count} registros")
                results[name] = count
            else:
                print(f"❌ Error obteniendo {name}: {response.text}")
                results[name] = 0
                
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            results[name] = 0
    
    return results

def test_create_turno():
    """Probar crear un turno"""
    print(f"\n📅 Probando crear un turno...")
    
    # Obtener datos necesarios
    try:
        # Obtener especialidades
        response = SESSION.get(f"{BASE_URL}/especialidades/")
        if response.status_code == 200:
            especialidades = response.json().get('results', [])
            if especialidades:
                especialidad_id = especialidades[0]['id']
            else:
                print("❌ No hay especialidades disponibles")
                return False
        else:
            print("❌ Error obteniendo especialidades")
            return False
        
        # Obtener médicos
        response = SESSION.get(f"{BASE_URL}/medicos/")
        if response.status_code == 200:
            medicos = response.json().get('results', [])
            if medicos:
                medico_id = medicos[0]['id']
            else:
                print("❌ No hay médicos disponibles")
                return False
        else:
            print("❌ Error obteniendo médicos")
            return False
        
        # Obtener pacientes
        response = SESSION.get(f"{BASE_URL}/pacientes/")
        if response.status_code == 200:
            pacientes = response.json().get('results', [])
            if pacientes:
                paciente_id = pacientes[0]['id']
            else:
                print("❌ No hay pacientes disponibles")
                return False
        else:
            print("❌ Error obteniendo pacientes")
            return False
        
        # Crear turno
        fecha_inicio = datetime.now() + timedelta(days=1)
        turno_data = {
            "fecha_hora_inicio": fecha_inicio.isoformat(),
            "paciente": paciente_id,
            "medico": medico_id,
            "especialidad": especialidad_id,
            "motivo_consulta": "Consulta de prueba",
            "estado": "DISPONIBLE"
        }
        
        print(f"📝 Datos del turno a crear:")
        print(json.dumps(turno_data, indent=2, default=str))
        
        response = SESSION.post(f"{BASE_URL}/turnos/", json=turno_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Turno creado exitosamente")
            print(f"ID: {data.get('id')}")
            print(f"Fecha: {data.get('fecha_hora_inicio')}")
            return True
        else:
            print(f"❌ Error creando turno: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando pruebas del sistema de turnos")
    print("=" * 50)
    
    # Credenciales de prueba
    users = [
        ("secretaria1", "changeme123"),
        ("paciente1", "changeme123"),
        ("medico1", "changeme123")
    ]
    
    for username, password in users:
        print(f"\n{'='*20} PROBANDO USUARIO: {username} {'='*20}")
        
        # Login
        if test_login(username, password):
            # Obtener usuario actual
            user_data = test_current_user()
            
            # Obtener datos del sistema
            data_counts = test_get_data()
            
            # Solo probar crear turno con secretaria
            if username == "secretaria1":
                test_create_turno()
        
        print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
