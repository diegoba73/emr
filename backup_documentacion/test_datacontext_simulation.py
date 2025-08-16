#!/usr/bin/env python3
"""
Test que simula exactamente el flujo del DataContext
"""

import requests
import json
import time

# Configuración
BASE_URL = 'http://127.0.0.1:8000/api'

def test_datacontext_flow():
    """Simula exactamente el flujo del DataContext"""
    print("🧪 SIMULANDO FLUJO DEL DATACONTEXT")
    print("=" * 50)
    
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': '*/*'
    })
    
    # 1. loadCurrentUser (con delay de 100ms como en el DataContext)
    print("1️⃣ loadCurrentUser (con delay de 100ms)...")
    time.sleep(0.1)
    
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        print(f"📊 Current user status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Usuario ya autenticado: {user_data.get('username', 'N/A')}")
        else:
            print("⚠️ Usuario no autenticado, iniciando login automático...")
            # 2. performAutoLogin
            await_perform_auto_login(session)
    except Exception as e:
        print(f"❌ Error en loadCurrentUser: {e}")
        await_perform_auto_login(session)
    
    # 3. refreshAll (cargar todos los datos)
    print("\n3️⃣ refreshAll (cargando todos los datos)...")
    await_refresh_all(session)

def await_perform_auto_login(session):
    """Simula performAutoLogin"""
    print("2️⃣ performAutoLogin...")
    try:
        login_data = {
            "username": "secretaria1",
            "password": "changeme123"
        }
        response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login automático exitoso: {data.get('user', {}).get('username', 'N/A')}")
        else:
            print(f"❌ Login automático falló: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en login automático: {e}")

def await_refresh_all(session):
    """Simula refreshAll"""
    print("   🔄 Cargando turnos...")
    try:
        response = session.get(f"{BASE_URL}/turnos/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Turnos: {len(data.get('results', []))} registros")
        else:
            print(f"   ❌ Turnos: Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error turnos: {e}")
    
    print("   🔄 Cargando pacientes...")
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
    
    print("   🔄 Cargando médicos...")
    try:
        response = session.get(f"{BASE_URL}/medicos/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Médicos: {len(data.get('results', []))} registros")
        else:
            print(f"   ❌ Médicos: Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error médicos: {e}")
    
    print("   🔄 Cargando especialidades...")
    try:
        response = session.get(f"{BASE_URL}/especialidades/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Especialidades: {len(data.get('results', []))} registros")
        else:
            print(f"   ❌ Especialidades: Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error especialidades: {e}")

def test_parallel_loading():
    """Test de carga en paralelo como hace refreshAll"""
    print("\n🧪 TEST DE CARGA EN PARALELO")
    print("=" * 40)
    
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': '*/*'
    })
    
    # Login primero
    login_data = {"username": "secretaria1", "password": "changeme123"}
    response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
    
    if response.status_code != 200:
        print("❌ No se pudo hacer login")
        return
    
    print("✅ Login exitoso")
    
    # Cargar todo en paralelo (como refreshAll)
    import concurrent.futures
    
    endpoints = [
        ('/turnos/', 'Turnos'),
        ('/pacientes/', 'Pacientes'),
        ('/medicos/', 'Médicos'),
        ('/especialidades/', 'Especialidades')
    ]
    
    def load_endpoint(endpoint, name):
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                data = response.json()
                return f"✅ {name}: {len(data.get('results', []))} registros"
            else:
                return f"❌ {name}: Status {response.status_code}"
        except Exception as e:
            return f"❌ {name}: Error {e}"
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(load_endpoint, endpoint, name) for endpoint, name in endpoints]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        for result in results:
            print(f"   {result}")

if __name__ == "__main__":
    test_datacontext_flow()
    test_parallel_loading()
