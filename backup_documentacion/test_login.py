#!/usr/bin/env python
import requests
import json

def test_login():
    """Probar el sistema de login"""
    
    print("🔐 PROBANDO SISTEMA DE LOGIN")
    print("=" * 40)
    
    url = "http://localhost:8000/api/auth/login/"
    
    # Caso 1: Login con credenciales válidas
    print("\n1️⃣ Probando login con credenciales válidas...")
    login_data = {
        "username": "paciente_test",
        "password": "Test123456"
    }
    
    try:
        response = requests.post(
            url, 
            json=login_data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login exitoso!")
            print(f"Usuario: {data.get('user', {}).get('username', 'N/A')}")
            print(f"Rol: {data.get('user', {}).get('rol', 'N/A')}")
        else:
            print("❌ Login falló")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Caso 2: Login con credenciales inválidas
    print("\n2️⃣ Probando login con credenciales inválidas...")
    invalid_data = {
        "username": "usuario_inexistente",
        "password": "password_incorrecta"
    }
    
    try:
        response = requests.post(
            url, 
            json=invalid_data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 401:
            print("✅ Error esperado para credenciales inválidas")
        else:
            print("⚠️  Respuesta inesperada")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Caso 3: Login con datos faltantes
    print("\n3️⃣ Probando login con datos faltantes...")
    incomplete_data = {
        "username": "paciente_test"
        # password faltante
    }
    
    try:
        response = requests.post(
            url, 
            json=incomplete_data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_login_frontend_simulation():
    """Simular exactamente lo que hace el frontend"""
    
    print("\n🌐 SIMULANDO LOGIN DESDE FRONTEND")
    print("-" * 40)
    
    url = "http://localhost:8000/api/auth/login/"
    
    # Simular request del frontend
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
    
    try:
        response = requests.post(
            url, 
            json=login_data,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Login exitoso desde frontend!")
        else:
            print("❌ Login falló desde frontend")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def verificar_usuarios_existentes():
    """Verificar qué usuarios existen para probar"""
    
    print("\n👥 VERIFICANDO USUARIOS EXISTENTES")
    print("-" * 40)
    
    # Usar Django shell para verificar usuarios
    import os
    import django
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
    django.setup()
    
    from usuarios.models import User
    
    users = User.objects.all()[:5]  # Primeros 5 usuarios
    
    print("Usuarios disponibles para probar:")
    for user in users:
        print(f"  - Username: {user.username}")
        print(f"    Email: {user.email}")
        print(f"    Rol: {user.rol}")
        print(f"    Activo: {user.is_active}")
        print()

if __name__ == "__main__":
    test_login()
    test_login_frontend_simulation()
    verificar_usuarios_existentes()
