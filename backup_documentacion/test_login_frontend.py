#!/usr/bin/env python3
"""
Script para probar el login frontend y verificar carga de datos
"""

import requests
import json
import time

# Configuración
BASE_URL = "http://127.0.0.1:8000/api"
FRONTEND_URL = "http://localhost:3000"

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def test_frontend_login():
    """Probar el flujo completo de login frontend"""
    print_header("PROBANDO LOGIN FRONTEND")
    
    session = requests.Session()
    
    # 1. Verificar que el frontend esté funcionando
    print_info("1. Verificando frontend...")
    try:
        response = session.get(FRONTEND_URL)
        if response.status_code == 200:
            print_success("Frontend respondiendo correctamente")
        else:
            print_error(f"Frontend respondiendo con status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error conectando al frontend: {e}")
        return False
    
    # 2. Verificar que el backend esté funcionando
    print_info("2. Verificando backend...")
    try:
        response = session.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print_success("Backend respondiendo correctamente")
        else:
            print_error(f"Backend respondiendo con status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error conectando al backend: {e}")
        return False
    
    # 3. Probar login
    print_info("3. Probando login...")
    try:
        response = session.post(f"{BASE_URL}/auth/login/", 
                              json={"username": "secretaria1", "password": "changeme123"})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('user'):
                print_success(f"Login exitoso para: {data['user']['username']}")
                print_info(f"Rol: {data['user']['groups']}")
            else:
                print_error("Login falló: no hay datos de usuario")
                return False
        else:
            print_error(f"Login falló: status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error en login: {e}")
        return False
    
    # 4. Verificar usuario actual
    print_info("4. Verificando usuario actual...")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 200:
            user_data = response.json()
            print_success(f"Usuario actual: {user_data['username']}")
        else:
            print_error(f"Error obteniendo usuario actual: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error obteniendo usuario actual: {e}")
        return False
    
    # 5. Probar carga de datos
    print_info("5. Probando carga de datos...")
    
    endpoints = [
        ("Pacientes", "/pacientes/"),
        ("Médicos", "/medicos/"),
        ("Especialidades", "/especialidades/"),
        ("Turnos", "/turnos/")
    ]
    
    for name, endpoint in endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                print_success(f"{name}: {count} registros")
            else:
                print_error(f"{name}: Error {response.status_code}")
        except Exception as e:
            print_error(f"{name}: Error de conexión - {e}")
    
    return True

def test_login_flow():
    """Probar el flujo completo de login y verificación"""
    print_header("FLUJO COMPLETO DE LOGIN")
    
    session = requests.Session()
    
    # Paso 1: Usuario no autenticado
    print_info("Paso 1: Usuario no autenticado")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 403:
            print_success("Correcto: Usuario no autenticado")
        else:
            print_error(f"Incorrecto: Status {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")
    
    # Paso 2: Login
    print_info("Paso 2: Realizando login")
    try:
        response = session.post(f"{BASE_URL}/auth/login/", 
                              json={"username": "secretaria1", "password": "changeme123"})
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Login exitoso: {data['user']['username']}")
        else:
            print_error(f"Login falló: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error en login: {e}")
        return False
    
    # Paso 3: Usuario autenticado
    print_info("Paso 3: Verificando usuario autenticado")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 200:
            user_data = response.json()
            print_success(f"Usuario autenticado: {user_data['username']}")
        else:
            print_error(f"Error: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False
    
    # Paso 4: Acceso a datos protegidos
    print_info("Paso 4: Accediendo a datos protegidos")
    try:
        response = session.get(f"{BASE_URL}/pacientes/")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('results', []))
            print_success(f"Acceso a pacientes: {count} registros")
        else:
            print_error(f"Error accediendo a pacientes: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False
    
    return True

def main():
    """Función principal"""
    print("🚀 PRUEBA DE LOGIN FRONTEND")
    print(f"📅 Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Backend: {BASE_URL}")
    print(f"⚛️  Frontend: {FRONTEND_URL}")
    
    # Probar flujo completo
    success = test_login_flow()
    
    if success:
        print_header("RESUMEN")
        print_success("🎉 Login frontend funcionando correctamente")
        print_info("📋 El sistema está listo para usar")
        print_info("🔐 Credenciales: secretaria1 / changeme123")
    else:
        print_header("ERRORES DETECTADOS")
        print_error("❌ Hay problemas con el login frontend")
        print_info("💡 Verifica la configuración de CORS y CSRF")

if __name__ == "__main__":
    main()
