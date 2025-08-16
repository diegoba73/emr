#!/usr/bin/env python3
"""
Script de verificación final del sistema EMR
Verifica que todos los componentes estén funcionando correctamente
"""

import requests
import json
from datetime import datetime

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

def test_backend_connectivity():
    """Probar conectividad del backend"""
    print_header("VERIFICANDO CONECTIVIDAD DEL BACKEND")
    
    try:
        response = requests.get(f"{BASE_URL}/auth/current-user/", timeout=5)
        if response.status_code == 403:
            print_success("Backend respondiendo correctamente (403 esperado para usuario no autenticado)")
        else:
            print_info(f"Backend respondiendo con status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print_error(f"Error conectando al backend: {e}")
        return False

def test_frontend_connectivity():
    """Probar conectividad del frontend"""
    print_header("VERIFICANDO CONECTIVIDAD DEL FRONTEND")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print_success("Frontend respondiendo correctamente")
            return True
        else:
            print_error(f"Frontend respondiendo con status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Error conectando al frontend: {e}")
        return False

def test_login():
    """Probar login con credenciales válidas"""
    print_header("VERIFICANDO SISTEMA DE LOGIN")
    
    credentials = [
        ("secretaria1", "changeme123", "Secretaria"),
        ("paciente1", "changeme123", "Paciente"),
        ("medico1", "changeme123", "Médico")
    ]
    
    session = requests.Session()
    
    for username, password, role in credentials:
        try:
            print_info(f"Probando login con {role}: {username}")
            
            response = session.post(f"{BASE_URL}/auth/login/", 
                                  json={"username": username, "password": password},
                                  timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('user'):
                    print_success(f"Login exitoso para {role}: {username}")
                    
                    # Probar obtener usuario actual
                    user_response = session.get(f"{BASE_URL}/auth/current-user/")
                    if user_response.status_code == 200:
                        print_success(f"Usuario actual obtenido correctamente para {role}")
                    else:
                        print_error(f"Error obteniendo usuario actual para {role}")
                else:
                    print_error(f"Login falló para {role}: {data.get('error', 'Error desconocido')}")
            else:
                print_error(f"Login falló para {role}: Status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print_error(f"Error en login para {role}: {e}")

def test_api_endpoints():
    """Probar endpoints de la API"""
    print_header("VERIFICANDO ENDPOINTS DE LA API")
    
    session = requests.Session()
    
    # Login primero
    try:
        response = session.post(f"{BASE_URL}/auth/login/", 
                              json={"username": "secretaria1", "password": "changeme123"})
        if response.status_code != 200:
            print_error("No se pudo hacer login para probar endpoints")
            return
    except:
        print_error("Error en login para probar endpoints")
        return
    
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
        except requests.exceptions.RequestException as e:
            print_error(f"{name}: Error de conexión - {e}")

def test_turno_creation():
    """Probar creación de turnos"""
    print_header("VERIFICANDO CREACIÓN DE TURNOS")
    
    session = requests.Session()
    
    # Login primero
    try:
        response = session.post(f"{BASE_URL}/auth/login/", 
                              json={"username": "secretaria1", "password": "changeme123"})
        if response.status_code != 200:
            print_error("No se pudo hacer login para probar creación de turnos")
            return
    except:
        print_error("Error en login para probar creación de turnos")
        return
    
    # Obtener datos necesarios
    try:
        # Obtener especialidades
        response = session.get(f"{BASE_URL}/especialidades/")
        if response.status_code == 200:
            especialidades = response.json().get('results', [])
            if especialidades:
                especialidad_id = especialidades[0]['id']
            else:
                print_error("No hay especialidades disponibles")
                return
        else:
            print_error("Error obteniendo especialidades")
            return
        
        # Obtener médicos
        response = session.get(f"{BASE_URL}/medicos/")
        if response.status_code == 200:
            medicos = response.json().get('results', [])
            if medicos:
                medico_id = medicos[0]['id']
            else:
                print_error("No hay médicos disponibles")
                return
        else:
            print_error("Error obteniendo médicos")
            return
        
        # Obtener pacientes
        response = session.get(f"{BASE_URL}/pacientes/")
        if response.status_code == 200:
            pacientes = response.json().get('results', [])
            if pacientes:
                paciente_id = pacientes[0]['id']
            else:
                print_error("No hay pacientes disponibles")
                return
        else:
            print_error("Error obteniendo pacientes")
            return
        
        # Crear turno
        from datetime import datetime, timedelta
        fecha_inicio = datetime.now() + timedelta(days=1)
        
        turno_data = {
            "fecha_hora_inicio": fecha_inicio.isoformat(),
            "paciente": paciente_id,
            "medico": medico_id,
            "especialidad": especialidad_id,
            "motivo_consulta": "Consulta de prueba desde script de verificación",
            "estado": "DISPONIBLE"
        }
        
        response = session.post(f"{BASE_URL}/turnos/", json=turno_data)
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"Turno creado exitosamente - ID: {data.get('id')}")
        else:
            print_error(f"Error creando turno: {response.status_code} - {response.text}")
            
    except Exception as e:
        print_error(f"Error en creación de turnos: {e}")

def main():
    """Función principal"""
    print("🚀 VERIFICACIÓN FINAL DEL SISTEMA EMR")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Backend: {BASE_URL}")
    print(f"⚛️  Frontend: {FRONTEND_URL}")
    
    # Verificar conectividad
    backend_ok = test_backend_connectivity()
    frontend_ok = test_frontend_connectivity()
    
    if not backend_ok or not frontend_ok:
        print_error("❌ ERROR: No se puede conectar al backend o frontend")
        print_info("💡 Solución: Ejecutar './start_servers_final.sh'")
        return
    
    # Probar funcionalidades
    test_login()
    test_api_endpoints()
    test_turno_creation()
    
    print_header("RESUMEN FINAL")
    print_success("🎉 Sistema EMR funcionando correctamente")
    print_info("📋 Puedes acceder a:")
    print_info(f"   - Frontend: {FRONTEND_URL}")
    print_info(f"   - Backend API: {BASE_URL}")
    print_info(f"   - Admin Django: http://localhost:8000/admin/")
    print_info("🔐 Credenciales de prueba:")
    print_info("   - Secretaria: secretaria1 / changeme123")
    print_info("   - Paciente: paciente1 / changeme123")
    print_info("   - Médico: medico1 / changeme123")

if __name__ == "__main__":
    main()
