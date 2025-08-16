#!/usr/bin/env python3
"""
Test específico para debug de cookies
"""

import requests
import json

# Configuración
BASE_URL = 'http://127.0.0.1:8000/api'

def test_cookie_handling():
    """Test específico para el manejo de cookies"""
    print("🍪 TEST DE MANEJO DE COOKIES")
    print("=" * 50)
    
    session = requests.Session()
    
    # Configurar headers como el navegador
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    print("📋 Headers iniciales:", dict(session.headers))
    print("🍪 Cookies iniciales:", dict(session.cookies))
    
    # 1. Login
    print("\n1️⃣ Login...")
    try:
        login_data = {
            "username": "secretaria1",
            "password": "changeme123"
        }
        response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
        
        print(f"📊 Login status: {response.status_code}")
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
    
    # 3. Test de pacientes
    print("\n3️⃣ Test de pacientes...")
    try:
        response = session.get(f"{BASE_URL}/pacientes/")
        print(f"📊 Pacientes status: {response.status_code}")
        print(f"🍪 Cookies para pacientes: {dict(session.cookies)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pacientes cargados: {len(data.get('results', []))} registros")
        else:
            print(f"❌ Error pacientes: {response.text}")
    except Exception as e:
        print(f"❌ Error en pacientes: {e}")

def test_browser_simulation():
    """Simula exactamente el comportamiento del navegador"""
    print("\n🌐 SIMULACIÓN DEL NAVEGADOR")
    print("=" * 40)
    
    session = requests.Session()
    
    # Headers exactos del navegador
    session.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:3000',
        'Referer': 'http://localhost:3000/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    print("📋 Headers del navegador:", dict(session.headers))
    
    # Login
    print("\n🔐 Login con headers del navegador...")
    try:
        login_data = {
            "username": "secretaria1",
            "password": "changeme123"
        }
        response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
        
        print(f"📊 Login status: {response.status_code}")
        print(f"🍪 Cookies: {dict(session.cookies)}")
        
        if response.status_code == 200:
            print("✅ Login exitoso")
            
            # Test inmediato de current-user
            print("\n👤 Test inmediato de current-user...")
            response2 = session.get(f"{BASE_URL}/auth/current-user/")
            print(f"📊 Current user status: {response2.status_code}")
            
            if response2.status_code == 200:
                print("✅ Usuario verificado correctamente")
                
                # Test de pacientes
                print("\n📊 Test de pacientes...")
                response3 = session.get(f"{BASE_URL}/pacientes/")
                print(f"📊 Pacientes status: {response3.status_code}")
                
                if response3.status_code == 200:
                    data = response3.json()
                    print(f"✅ Pacientes: {len(data.get('results', []))} registros")
                else:
                    print(f"❌ Pacientes error: {response3.text}")
            else:
                print(f"❌ Current user error: {response2.text}")
        else:
            print(f"❌ Login falló: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_cookie_handling()
    test_browser_simulation()



