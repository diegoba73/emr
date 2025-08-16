#!/usr/bin/env python
import requests
import json

def simulate_browser_login():
    """Simular exactamente el comportamiento del navegador"""
    
    print("🌐 SIMULANDO LOGIN DESDE NAVEGADOR")
    print("=" * 50)
    
    url = "http://localhost:8000/api/auth/login/"
    
    # Simular exactamente lo que hace el frontend
    login_data = {
        "username": "paciente_test",
        "password": "Test123456"
    }
    
    # Headers exactos del navegador
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': 'http://localhost:3000',
        'Referer': 'http://localhost:3000/login',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"📡 URL: {url}")
    print(f"📤 Data: {json.dumps(login_data, indent=2)}")
    
    try:
        # Simular el fetch del frontend
        print("\n🔄 Simulando fetch del frontend...")
        response = requests.post(
            url, 
            json=login_data, 
            headers=headers,
            timeout=10
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        # Intentar parsear JSON como lo hace el frontend
        try:
            data = response.json()
            print(f"📄 JSON Response: {json.dumps(data, indent=2)}")
            
            # Simular la lógica del frontend
            if response.status_code == 200 and data.get('user'):
                print("\n✅ Frontend debería considerar esto como login exitoso")
                print(f"Usuario: {data['user'].get('username', 'N/A')}")
                print(f"Grupos: {data['user'].get('groups', [])}")
                
                # Simular redirección
                groups = data['user'].get('groups', [])
                if 'Secretarias' in groups:
                    print("🔄 Redirigiría a: /turnos")
                elif 'Médicos' in groups:
                    print("🔄 Redirigiría a: /consultas")
                elif 'Pacientes' in groups:
                    print("🔄 Redirigiría a: /dashboard")
                elif 'Laboratorio' in groups:
                    print("🔄 Redirigiría a: /laboratorio")
                else:
                    print("🔄 Redirigiría a: /dashboard")
                    
            elif response.status_code != 200:
                print(f"\n❌ Frontend debería mostrar error")
                if data.get('error'):
                    print(f"Error: {data['error']}")
                else:
                    print("Error genérico")
            else:
                print(f"\n⚠️  Respuesta inesperada")
                print(f"Status: {response.status_code}")
                print(f"Data: {data}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Error parseando JSON: {str(e)}")
            print(f"Response text: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {str(e)}")
    except requests.exceptions.Timeout as e:
        print(f"⏰ Timeout: {str(e)}")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def test_with_credentials():
    """Probar con las credenciales que deberían funcionar"""
    
    print("\n🧪 PROBANDO CREDENCIALES VÁLIDAS")
    print("-" * 40)
    
    # Credenciales que sabemos que funcionan
    valid_credentials = [
        {"username": "paciente_test", "password": "Test123456", "description": "Paciente Test"},
        {"username": "medico_prueba", "password": "1234@asd", "description": "Médico Prueba"},
    ]
    
    url = "http://localhost:8000/api/auth/login/"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': 'http://localhost:3000',
        'Referer': 'http://localhost:3000/login'
    }
    
    for cred in valid_credentials:
        print(f"\n🔍 Probando: {cred['description']}")
        print(f"   Username: {cred['username']}")
        
        try:
            response = requests.post(url, json=cred, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Éxito - Status: {response.status_code}")
                print(f"   Usuario: {data.get('user', {}).get('username', 'N/A')}")
                print(f"   Grupos: {data.get('user', {}).get('groups', [])}")
                print(f"   Message: {data.get('message', 'N/A')}")
            else:
                print(f"   ❌ Falló - Status: {response.status_code}")
                try:
                    data = response.json()
                    print(f"   Error: {data.get('error', 'N/A')}")
                except:
                    print(f"   Response: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")

if __name__ == "__main__":
    simulate_browser_login()
    test_with_credentials()
