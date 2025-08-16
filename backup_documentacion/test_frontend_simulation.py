#!/usr/bin/env python3
"""
Test que simula exactamente lo que hace el frontend
"""

import requests
import json

# Configuración
BASE_URL = 'http://127.0.0.1:8000/api'

def test_frontend_simulation():
    """Simula exactamente el flujo del frontend"""
    print("🧪 SIMULANDO FLUJO DEL FRONTEND")
    print("=" * 50)
    
    session = requests.Session()
    
    # 1. Login automático (como hace el DataContext)
    print("1️⃣ Login automático...")
    try:
        login_data = {
            "username": "secretaria1",
            "password": "changeme123"
        }
        response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login exitoso: {data.get('user', {}).get('username', 'N/A')}")
        else:
            print(f"❌ Login falló: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return
    
    # 2. Verificar usuario actual
    print("2️⃣ Verificando usuario actual...")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Usuario autenticado: {user_data.get('username', 'N/A')}")
        else:
            print(f"❌ Error verificando usuario: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 3. Cargar datos (como hace refreshAll)
    print("3️⃣ Cargando datos...")
    
    # Médicos (sin autenticación requerida)
    print("   🔍 Cargando médicos...")
    try:
        response = session.get(f"{BASE_URL}/medicos/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Médicos: {len(data.get('results', []))} registros")
        else:
            print(f"   ❌ Médicos: Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error médicos: {e}")
    
    # Especialidades (sin autenticación requerida)
    print("   🔍 Cargando especialidades...")
    try:
        response = session.get(f"{BASE_URL}/especialidades/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Especialidades: {len(data.get('results', []))} registros")
        else:
            print(f"   ❌ Especialidades: Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error especialidades: {e}")
    
    # Pacientes (CON autenticación requerida)
    print("   🔍 Cargando pacientes...")
    try:
        response = session.get(f"{BASE_URL}/pacientes/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Pacientes: {len(data.get('results', []))} registros")
        else:
            print(f"   ❌ Pacientes: Status {response.status_code}")
            print(f"   📄 Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error pacientes: {e}")
    
    # Turnos (CON autenticación requerida)
    print("   🔍 Cargando turnos...")
    try:
        response = session.get(f"{BASE_URL}/turnos/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Turnos: {len(data.get('results', []))} registros")
        else:
            print(f"   ❌ Turnos: Status {response.status_code}")
            print(f"   📄 Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error turnos: {e}")
    
    # 4. Verificar cookies y headers
    print("4️⃣ Verificando cookies y headers...")
    print(f"   🍪 Cookies: {dict(session.cookies)}")
    print(f"   📋 Headers: {dict(session.headers)}")

def test_without_session():
    """Test sin sesión para comparar"""
    print("\n🧪 TEST SIN SESIÓN")
    print("=" * 30)
    
    # Médicos (sin autenticación)
    print("🔍 Médicos sin sesión...")
    try:
        response = requests.get(f"{BASE_URL}/medicos/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Médicos: {len(data.get('results', []))} registros")
        else:
            print(f"❌ Médicos: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Especialidades (sin autenticación)
    print("🔍 Especialidades sin sesión...")
    try:
        response = requests.get(f"{BASE_URL}/especialidades/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Especialidades: {len(data.get('results', []))} registros")
        else:
            print(f"❌ Especialidades: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Pacientes (con autenticación requerida)
    print("🔍 Pacientes sin sesión...")
    try:
        response = requests.get(f"{BASE_URL}/pacientes/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pacientes: {len(data.get('results', []))} registros")
        else:
            print(f"❌ Pacientes: Status {response.status_code}")
            print(f"📄 Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_frontend_simulation()
    test_without_session()
