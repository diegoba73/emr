#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"

def test_backend_connection():
    print("🔍 Probando conexión al backend...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Backend conectado correctamente")
            return True
        else:
            print(f"❌ Backend error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando al backend: {e}")
        return False

def test_current_user():
    print("🔍 Probando endpoint current-user...")
    try:
        response = requests.get(f"{BASE_URL}/auth/current-user/")
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Usuario autenticado: {user_data.get('username')}")
            return True
        else:
            error_data = response.json()
            print(f"⚠️ Usuario no autenticado: {error_data.get('detail')}")
            return False
    except Exception as e:
        print(f"❌ Error obteniendo usuario: {e}")
        return False

def test_login():
    print("🔍 Probando login...")
    try:
        response = requests.post(f"{BASE_URL}/auth/login/", 
                               json={
                                   "username": "secretaria1",
                                   "password": "changeme123"
                               })
        
        print(f"📊 Login response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login exitoso: {data.get('user', {}).get('username')}")
            return True
        else:
            error_data = response.json()
            print(f"❌ Login falló: {error_data.get('error', 'Error desconocido')}")
            return False
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return False

def test_data_with_session():
    print("🔍 Probando carga de datos con sesión...")
    
    # Crear una sesión para mantener cookies
    session = requests.Session()
    
    # Hacer login
    print("  📝 Haciendo login...")
    login_response = session.post(f"{BASE_URL}/auth/login/", 
                                 json={
                                     "username": "secretaria1",
                                     "password": "changeme123"
                                 })
    
    if login_response.status_code != 200:
        print(f"❌ Login falló: {login_response.status_code}")
        return False
    
    print("✅ Login exitoso")
    
    # Probar current-user con sesión
    print("  👤 Probando current-user...")
    user_response = session.get(f"{BASE_URL}/auth/current-user/")
    print(f"  📊 Current-user status: {user_response.status_code}")
    
    if user_response.status_code == 200:
        user_data = user_response.json()
        print(f"✅ Usuario autenticado: {user_data.get('username')}")
    else:
        print(f"❌ Current-user falló: {user_response.status_code}")
        return False
    
    # Probar pacientes con sesión
    print("  📊 Probando pacientes...")
    pacientes_response = session.get(f"{BASE_URL}/pacientes/")
    print(f"  📊 Pacientes status: {pacientes_response.status_code}")
    
    if pacientes_response.status_code == 200:
        pacientes_data = pacientes_response.json()
        print(f"✅ Pacientes cargados: {len(pacientes_data.get('results', []))} registros")
    else:
        print(f"❌ Pacientes falló: {pacientes_response.status_code}")
        return False
    
    # Probar turnos con sesión
    print("  📅 Probando turnos...")
    turnos_response = session.get(f"{BASE_URL}/turnos/")
    print(f"  📊 Turnos status: {turnos_response.status_code}")
    
    if turnos_response.status_code == 200:
        turnos_data = turnos_response.json()
        print(f"✅ Turnos cargados: {len(turnos_data.get('results', []))} registros")
    else:
        print(f"❌ Turnos falló: {turnos_response.status_code}")
        return False
    
    return True

def main():
    print("🚀 Iniciando debug de autenticación...")
    print("=" * 50)
    
    # Test 1: Conexión al backend
    if not test_backend_connection():
        print("❌ Backend no disponible")
        return
    
    print()
    
    # Test 2: Usuario actual (sin login)
    test_current_user()
    
    print()
    
    # Test 3: Login
    if not test_login():
        print("❌ Login falló")
        return
    
    print()
    
    # Test 4: Datos con sesión
    if not test_data_with_session():
        print("❌ Carga de datos falló")
        return
    
    print()
    print("✅ Todas las pruebas completadas exitosamente!")

if __name__ == "__main__":
    main()
