#!/usr/bin/env python3
"""
Script para probar el login y ver qué datos devuelve
"""

import requests
import json

def test_login():
    print("🧪 Probando login...")
    
    session = requests.Session()
    
    # 2. Probar login con diferentes usuarios
    test_users = [
        {'username': 'secretaria1', 'password': 'changeme123', 'expected_role': 'SECRETARIA'},
        {'username': 'medico1', 'password': 'changeme123', 'expected_role': 'MEDICO'},
        {'username': 'paciente1', 'password': 'changeme123', 'expected_role': 'PACIENTE'},
        {'username': 'admin1', 'password': 'changeme123', 'expected_role': 'ADMIN'},
    ]
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    for user in test_users:
        print(f"\n🔐 Probando login con {user['username']}...")
        
        login_data = {
            'username': user['username'],
            'password': user['password']
        }
        
        login_response = session.post('http://localhost:8000/api/auth/login/', 
                                    json=login_data, 
                                    headers=headers)
        
        print(f"📊 Status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            print("✅ Login exitoso!")
            print("📄 Respuesta completa:")
            print(json.dumps(login_result, indent=2, ensure_ascii=False))
            
            # Verificar si hay usuario en la respuesta
            if 'user' in login_result:
                user_data = login_result['user']
                print(f"👤 Usuario: {user_data.get('username', 'N/A')}")
                print(f"🎭 Rol: {user_data.get('rol', 'N/A')}")
                print(f"📧 Email: {user_data.get('email', 'N/A')}")
                print(f"✅ Activo: {user_data.get('is_active', 'N/A')}")
                
                # Verificar si el rol coincide con el esperado
                if user_data.get('rol') == user['expected_role']:
                    print(f"✅ Rol correcto: {user_data.get('rol')}")
                else:
                    print(f"⚠️ Rol inesperado: {user_data.get('rol')} (esperado: {user['expected_role']})")
            else:
                print("❌ No hay datos de usuario en la respuesta")
        else:
            print(f"❌ Login falló")
            print(f"📄 Respuesta: {login_response.text}")
    
    # 3. Probar endpoint de usuario actual
    print(f"\n🔍 Probando endpoint de usuario actual...")
    current_user_response = session.get('http://localhost:8000/api/auth/current-user/')
    
    print(f"📊 Status: {current_user_response.status_code}")
    
    if current_user_response.status_code == 200:
        current_user = current_user_response.json()
        print("✅ Usuario actual obtenido!")
        print("📄 Datos del usuario actual:")
        print(json.dumps(current_user, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Error obteniendo usuario actual: {current_user_response.text}")

if __name__ == "__main__":
    test_login()
