#!/usr/bin/env python3
"""
Test completo del sistema EMR - Autenticación y Carga de Datos
"""

import requests
import json
import time

# Configuración
BASE_URL = 'http://127.0.0.1:8000/api'
FRONTEND_URL = 'http://localhost:3000'

def test_backend_connection():
    """Test de conexión al backend"""
    print("🔍 Probando conexión al backend...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ Backend conectado correctamente")
            return True
        else:
            print(f"❌ Backend responde con status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando al backend: {e}")
        return False

def test_frontend_connection():
    """Test de conexión al frontend"""
    print("🔍 Probando conexión al frontend...")
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Frontend conectado correctamente")
            return True
        else:
            print(f"❌ Frontend responde con status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando al frontend: {e}")
        return False

def test_authentication_flow():
    """Test completo del flujo de autenticación"""
    print("\n🔐 Probando flujo de autenticación...")
    
    session = requests.Session()
    
    # 1. Verificar usuario actual (debería fallar)
    print("1️⃣ Verificando usuario actual (sin autenticación)...")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 403:
            print("✅ Correcto: Usuario no autenticado")
        else:
            print(f"⚠️  Inesperado: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 2. Login con secretaria
    print("2️⃣ Intentando login con secretaria...")
    try:
        login_data = {
            "username": "secretaria1",
            "password": "changeme123"
        }
        response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login exitoso: {data.get('user', {}).get('username', 'N/A')}")
            print(f"   Rol: {data.get('user', {}).get('rol', 'N/A')}")
        else:
            print(f"❌ Login falló: Status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return False
    
    # 3. Verificar usuario actual (debería funcionar)
    print("3️⃣ Verificando usuario actual (con autenticación)...")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Usuario autenticado: {user_data.get('username', 'N/A')}")
        else:
            print(f"❌ Error verificando usuario: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # 4. Cargar datos protegidos
    print("4️⃣ Cargando datos protegidos...")
    endpoints = ['/pacientes/', '/turnos/', '/medicos/', '/especialidades/']
    
    for endpoint in endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                print(f"✅ {endpoint}: {count} registros")
            else:
                print(f"❌ {endpoint}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Error en {endpoint}: {e}")
    
    # 5. Logout
    print("5️⃣ Probando logout...")
    try:
        response = session.post(f"{BASE_URL}/auth/logout/")
        if response.status_code == 200:
            print("✅ Logout exitoso")
        else:
            print(f"⚠️  Logout con status {response.status_code}")
    except Exception as e:
        print(f"❌ Error en logout: {e}")
    
    return True

def test_data_consistency():
    """Test de consistencia de datos"""
    print("\n📊 Probando consistencia de datos...")
    
    session = requests.Session()
    
    # Login
    login_data = {"username": "secretaria1", "password": "changeme123"}
    response = session.post(f"{BASE_URL}/auth/login/", json=login_data)
    
    if response.status_code != 200:
        print("❌ No se pudo hacer login para test de datos")
        return False
    
    # Verificar que todos los endpoints devuelven datos válidos
    endpoints = {
        '/pacientes/': 'pacientes',
        '/turnos/': 'turnos', 
        '/medicos/': 'médicos',
        '/especialidades/': 'especialidades'
    }
    
    for endpoint, name in endpoints.items():
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                data = response.json()
                if 'results' in data:
                    print(f"✅ {name}: {len(data['results'])} registros")
                else:
                    print(f"⚠️  {name}: Formato inesperado")
            else:
                print(f"❌ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
    
    return True

def main():
    """Función principal"""
    print("🚀 INICIANDO TEST COMPLETO DEL SISTEMA EMR")
    print("=" * 50)
    
    # Test de conexiones
    backend_ok = test_backend_connection()
    frontend_ok = test_frontend_connection()
    
    if not backend_ok or not frontend_ok:
        print("\n❌ ERROR: No se pueden conectar los servidores")
        print("   Asegúrate de que Django esté en puerto 8000 y React en puerto 3000")
        return
    
    # Test de autenticación
    auth_ok = test_authentication_flow()
    
    # Test de datos
    data_ok = test_data_consistency()
    
    # Resumen
    print("\n" + "=" * 50)
    print("📋 RESUMEN DE PRUEBAS")
    print("=" * 50)
    print(f"Backend: {'✅ OK' if backend_ok else '❌ FALLÓ'}")
    print(f"Frontend: {'✅ OK' if frontend_ok else '❌ FALLÓ'}")
    print(f"Autenticación: {'✅ OK' if auth_ok else '❌ FALLÓ'}")
    print(f"Datos: {'✅ OK' if data_ok else '❌ FALLÓ'}")
    
    if all([backend_ok, frontend_ok, auth_ok, data_ok]):
        print("\n🎉 ¡SISTEMA FUNCIONANDO CORRECTAMENTE!")
        print("   Puedes acceder a:")
        print(f"   - Frontend: {FRONTEND_URL}")
        print(f"   - Backend API: {BASE_URL}")
        print(f"   - Admin Django: http://localhost:8000/admin/")
    else:
        print("\n⚠️  Hay problemas que necesitan atención")

if __name__ == "__main__":
    main()
