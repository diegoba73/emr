#!/usr/bin/env python
import requests
import json

def debug_login_frontend():
    """Debuggear el login desde el frontend paso a paso"""
    
    print("🔍 DEBUGGEANDO LOGIN DESDE FRONTEND")
    print("=" * 50)
    
    url = "http://localhost:8000/api/auth/login/"
    
    # Simular exactamente lo que hace el frontend
    login_data = {
        "username": "paciente_test",
        "password": "Test123456"
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': 'http://localhost:3000',
        'Referer': 'http://localhost:3000/login'
    }
    
    print(f"📡 URL: {url}")
    print(f"📤 Data: {json.dumps(login_data, indent=2)}")
    print(f"📋 Headers: {json.dumps(headers, indent=2)}")
    
    try:
        print("\n🔄 Enviando request...")
        response = requests.post(url, json=login_data, headers=headers)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print(f"📄 Response Text: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Login exitoso!")
            print(f"Usuario: {data.get('user', {}).get('username', 'N/A')}")
            print(f"Grupos: {data.get('user', {}).get('groups', [])}")
            print(f"Message: {data.get('message', 'N/A')}")
        else:
            print(f"\n❌ Login falló con status {response.status_code}")
            try:
                data = response.json()
                print(f"Error: {data.get('error', 'N/A')}")
                print(f"Message: {data.get('message', 'N/A')}")
            except:
                print(f"Response no es JSON válido: {response.text}")
                
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {str(e)}")
    except requests.exceptions.Timeout as e:
        print(f"⏰ Timeout: {str(e)}")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def test_different_credentials():
    """Probar con diferentes credenciales"""
    
    print("\n🧪 PROBANDO DIFERENTES CREDENCIALES")
    print("-" * 40)
    
    test_cases = [
        {"username": "admin", "password": "admin123", "description": "Admin válido"},
        {"username": "medico_prueba", "password": "1234@asd", "description": "Médico válido"},
        {"username": "secretaria1", "password": "1234@asd", "description": "Secretaria válida"},
        {"username": "usuario_inexistente", "password": "password", "description": "Usuario inexistente"},
        {"username": "paciente_test", "password": "password_incorrecta", "description": "Contraseña incorrecta"},
    ]
    
    url = "http://localhost:8000/api/auth/login/"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': 'http://localhost:3000',
        'Referer': 'http://localhost:3000/login'
    }
    
    for test_case in test_cases:
        print(f"\n🔍 Probando: {test_case['description']}")
        print(f"   Username: {test_case['username']}")
        
        try:
            response = requests.post(url, json=test_case, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Éxito - Usuario: {data.get('user', {}).get('username', 'N/A')}")
                print(f"   Grupos: {data.get('user', {}).get('groups', [])}")
            else:
                try:
                    data = response.json()
                    print(f"   ❌ Error: {data.get('error', 'N/A')}")
                except:
                    print(f"   ❌ Error: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")

def check_backend_health():
    """Verificar que el backend esté funcionando"""
    
    print("\n🏥 VERIFICANDO SALUD DEL BACKEND")
    print("-" * 40)
    
    # Probar endpoints básicos
    endpoints = [
        "http://localhost:8000/api/",
        "http://localhost:8000/admin/",
        "http://localhost:8000/api/auth/login/"
    ]
    
    for endpoint in endpoints:
        try:
            if "login" in endpoint:
                # Para login, probar OPTIONS
                response = requests.options(endpoint)
            else:
                response = requests.get(endpoint)
            
            print(f"✅ {endpoint}: {response.status_code}")
            
        except Exception as e:
            print(f"❌ {endpoint}: {str(e)}")

if __name__ == "__main__":
    check_backend_health()
    debug_login_frontend()
    test_different_credentials()
