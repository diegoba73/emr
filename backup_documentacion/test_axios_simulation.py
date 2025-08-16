#!/usr/bin/env python3
"""
Test que simula el comportamiento exacto de Axios
"""

import requests
import json

# Configuración
BASE_URL = 'http://127.0.0.1:8000/api'

def test_axios_simulation():
    """Simula el comportamiento exacto de Axios con withCredentials"""
    print("🧪 SIMULANDO COMPORTAMIENTO DE AXIOS")
    print("=" * 50)
    
    session = requests.Session()
    
    # Configurar headers como Axios
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'User-Agent': 'axios-simulation'
    })
    
    print("📋 Headers iniciales:", dict(session.headers))
    print("🍪 Cookies iniciales:", dict(session.cookies))
    
    # 1. Login (como hace el DataContext)
    print("\n1️⃣ Login automático...")
    try:
        login_data = {
            "username": "secretaria1",
            "password": "changeme123"
        }
        response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
        
        print(f"📊 Login response status: {response.status_code}")
        print(f"📋 Login response headers: {dict(response.headers)}")
        print(f"🍪 Cookies después del login: {dict(session.cookies)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login exitoso: {data.get('user', {}).get('username', 'N/A')}")
        else:
            print(f"❌ Login falló: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return
    
    # 2. Verificar usuario actual
    print("\n2️⃣ Verificando usuario actual...")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        print(f"📊 Current user status: {response.status_code}")
        print(f"🍪 Cookies para current-user: {dict(session.cookies)}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Usuario autenticado: {user_data.get('username', 'N/A')}")
        else:
            print(f"❌ Error verificando usuario: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 3. Cargar datos en paralelo (como hace refreshAll)
    print("\n3️⃣ Cargando datos en paralelo...")
    
    endpoints = [
        ('/medicos/', 'Médicos'),
        ('/especialidades/', 'Especialidades'),
        ('/pacientes/', 'Pacientes'),
        ('/turnos/', 'Turnos')
    ]
    
    for endpoint, name in endpoints:
        print(f"\n   🔍 Cargando {name}...")
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            print(f"   📊 {name} status: {response.status_code}")
            print(f"   🍪 Cookies para {name}: {dict(session.cookies)}")
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                print(f"   ✅ {name}: {count} registros")
            else:
                print(f"   ❌ {name}: {response.text}")
        except Exception as e:
            print(f"   ❌ Error en {name}: {e}")

def test_individual_requests():
    """Test de peticiones individuales para comparar"""
    print("\n🧪 TEST DE PETICIONES INDIVIDUALES")
    print("=" * 40)
    
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': '*/*'
    })
    
    # Login
    login_data = {"username": "secretaria1", "password": "changeme123"}
    response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
    
    if response.status_code != 200:
        print("❌ No se pudo hacer login")
        return
    
    print("✅ Login exitoso")
    print(f"🍪 Cookies: {dict(session.cookies)}")
    
    # Test individual de pacientes
    print("\n🔍 Test individual de pacientes...")
    response = session.get(f"{BASE_URL}/pacientes/")
    print(f"📊 Status: {response.status_code}")
    print(f"📋 Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Pacientes cargados: {len(data.get('results', []))} registros")
    else:
        print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    test_axios_simulation()
    test_individual_requests()
