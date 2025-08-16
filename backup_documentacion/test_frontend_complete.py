#!/usr/bin/env python3
"""
Script para probar el flujo completo del frontend
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

def test_frontend_flow():
    """Probar el flujo completo del frontend"""
    print_header("PROBANDO FLUJO COMPLETO FRONTEND")
    
    session = requests.Session()
    
    # 1. Verificar conectividad
    print_info("1. Verificando conectividad...")
    try:
        # Backend
        response = session.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print_success("Backend conectado")
        else:
            print_error(f"Backend error: {response.status_code}")
            return False
        
        # Frontend
        response = session.get(FRONTEND_URL)
        if response.status_code == 200:
            print_success("Frontend conectado")
        else:
            print_error(f"Frontend error: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error de conectividad: {e}")
        return False
    
    # 2. Verificar estado inicial (sin autenticación)
    print_info("2. Verificando estado inicial...")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 403:
            print_success("Estado inicial correcto: usuario no autenticado")
        else:
            print_error(f"Estado inicial inesperado: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error verificando estado inicial: {e}")
        return False
    
    # 3. Probar login
    print_info("3. Probando login...")
    try:
        response = session.post(f"{BASE_URL}/auth/login/", 
                              json={"username": "secretaria1", "password": "changeme123"})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('user'):
                print_success(f"Login exitoso: {data['user']['username']}")
                print_info(f"Rol: {data['user']['groups']}")
            else:
                print_error("Login falló: no hay datos de usuario")
                return False
        else:
            print_error(f"Login falló: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error en login: {e}")
        return False
    
    # 4. Verificar usuario autenticado
    print_info("4. Verificando usuario autenticado...")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 200:
            user_data = response.json()
            print_success(f"Usuario autenticado: {user_data['username']}")
        else:
            print_error(f"Error obteniendo usuario: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error verificando usuario: {e}")
        return False
    
    # 5. Probar carga de datos protegidos
    print_info("5. Probando carga de datos protegidos...")
    
    endpoints = [
        ("Pacientes", "/pacientes/"),
        ("Turnos", "/turnos/"),
        ("Médicos", "/medicos/"),
        ("Especialidades", "/especialidades/")
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

def test_cors_and_csrf():
    """Probar configuración de CORS y CSRF"""
    print_header("PROBANDO CORS Y CSRF")
    
    session = requests.Session()
    
    # 1. Probar OPTIONS request (CORS preflight)
    print_info("1. Probando CORS preflight...")
    try:
        response = session.options(f"{BASE_URL}/auth/login/")
        if response.status_code == 200:
            print_success("CORS preflight exitoso")
        else:
            print_error(f"CORS preflight falló: {response.status_code}")
    except Exception as e:
        print_error(f"Error en CORS preflight: {e}")
    
    # 2. Probar login con headers de origen
    print_info("2. Probando login con headers de origen...")
    try:
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:3000',
            'Referer': 'http://localhost:3000/login'
        }
        
        response = session.post(f"{BASE_URL}/auth/login/", 
                              json={"username": "secretaria1", "password": "changeme123"},
                              headers=headers)
        
        if response.status_code == 200:
            print_success("Login con headers de origen exitoso")
        else:
            print_error(f"Login con headers falló: {response.status_code}")
    except Exception as e:
        print_error(f"Error en login con headers: {e}")

def test_browser_simulation():
    """Simular comportamiento del navegador"""
    print_header("SIMULANDO NAVEGADOR")
    
    session = requests.Session()
    
    # 1. Simular visita inicial al frontend
    print_info("1. Simulando visita al frontend...")
    try:
        response = session.get(FRONTEND_URL)
        if response.status_code == 200:
            print_success("Frontend accesible")
        else:
            print_error(f"Frontend no accesible: {response.status_code}")
    except Exception as e:
        print_error(f"Error accediendo al frontend: {e}")
    
    # 2. Simular intento de obtener usuario actual
    print_info("2. Simulando obtención de usuario actual...")
    try:
        response = session.get(f"{BASE_URL}/auth/current-user/")
        if response.status_code == 403:
            print_success("Comportamiento correcto: usuario no autenticado")
        else:
            print_error(f"Comportamiento inesperado: {response.status_code}")
    except Exception as e:
        print_error(f"Error obteniendo usuario: {e}")
    
    # 3. Simular login desde frontend
    print_info("3. Simulando login desde frontend...")
    try:
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:3000',
            'Referer': 'http://localhost:3000/login'
        }
        
        response = session.post(f"{BASE_URL}/auth/login/", 
                              json={"username": "secretaria1", "password": "changeme123"},
                              headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Login simulado exitoso: {data['user']['username']}")
        else:
            print_error(f"Login simulado falló: {response.status_code}")
    except Exception as e:
        print_error(f"Error en login simulado: {e}")

def main():
    """Función principal"""
    print("🚀 PRUEBA COMPLETA DEL FRONTEND")
    print(f"📅 Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Backend: {BASE_URL}")
    print(f"⚛️  Frontend: {FRONTEND_URL}")
    
    # Probar flujo completo
    success = test_frontend_flow()
    
    if success:
        print_header("RESUMEN")
        print_success("🎉 Frontend funcionando correctamente")
        print_info("📋 El sistema está listo para usar")
        print_info("🔐 Credenciales: secretaria1 / changeme123")
        
        # Probar configuración adicional
        test_cors_and_csrf()
        test_browser_simulation()
    else:
        print_header("ERRORES DETECTADOS")
        print_error("❌ Hay problemas con el frontend")
        print_info("💡 Verifica la configuración")

if __name__ == "__main__":
    main()
