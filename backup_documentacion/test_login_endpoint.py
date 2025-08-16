#!/usr/bin/env python3
"""
Script para probar el endpoint de login directamente
"""

import requests
import json

def test_login_endpoint():
    """Prueba el endpoint de login con diferentes usuarios"""
    
    # URL del endpoint
    url = "http://localhost:8000/api/auth/login/"
    
    # Usuarios de prueba
    test_users = [
        {
            "name": "Admin",
            "username": "admin",
            "password": "admin123"
        },
        {
            "name": "Paciente",
            "username": "paciente1",
            "password": "changeme123"
        },
        {
            "name": "Médico",
            "username": "dr.garcia",
            "password": "changeme123"
        },
        {
            "name": "Secretaria",
            "username": "secretaria1",
            "password": "changeme123"
        }
    ]
    
    print("🧪 Probando endpoint de login...")
    print("=" * 50)
    
    for user in test_users:
        print(f"\n🔍 Probando login para: {user['name']} ({user['username']})")
        
        try:
            # Hacer la petición POST
            response = requests.post(
                url,
                json={
                    "username": user["username"],
                    "password": user["password"]
                },
                headers={
                    "Content-Type": "application/json"
                }
            )
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📋 Headers: {dict(response.headers)}")
            
            # Intentar parsear la respuesta JSON
            try:
                data = response.json()
                print(f"📄 Response Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if response.status_code == 200:
                    print("✅ Login exitoso!")
                    if "user" in data:
                        print(f"👤 Usuario: {data['user']['username']}")
                        print(f"📧 Email: {data['user']['email']}")
                        print(f"👥 Grupos: {data['user']['groups']}")
                else:
                    print("❌ Login falló")
                    if "error" in data:
                        print(f"🚨 Error: {data['error']}")
                        
            except json.JSONDecodeError:
                print(f"❌ Error parseando JSON: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Pruebas completadas")

if __name__ == "__main__":
    test_login_endpoint()
