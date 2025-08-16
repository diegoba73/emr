#!/usr/bin/env python3
"""
Script para probar la funcionalidad CSRF al crear turnos
"""

import requests
import json

def test_csrf_turno_creation():
    print("🧪 Probando creación de turno con CSRF...")
    
    session = requests.Session()
    
    # 1. Login
    print("🔐 Haciendo login...")
    login_response = session.post('http://localhost:8000/api/auth/login/', json={
        'username': 'secretaria1',
        'password': 'changeme123'
    })
    
    if login_response.status_code != 200:
        print("❌ Login falló")
        return
    
    print("✅ Login exitoso")
    
    # 2. Obtener token CSRF
    print("🔐 Obteniendo token CSRF...")
    csrf_response = session.get('http://localhost:8000/api/')
    csrf_token = session.cookies.get('csrftoken')
    
    if not csrf_token:
        print("❌ No se pudo obtener token CSRF")
        return
    
    print(f"✅ Token CSRF obtenido: {csrf_token[:10]}...")
    
    # 3. Obtener datos necesarios
    print("📊 Obteniendo datos para crear turno...")
    
    pacientes_response = session.get('http://localhost:8000/api/pacientes/')
    medicos_response = session.get('http://localhost:8000/api/medicos/')
    especialidades_response = session.get('http://localhost:8000/api/especialidades/')
    
    if not all([pacientes_response.ok, medicos_response.ok, especialidades_response.ok]):
        print("❌ Error obteniendo datos")
        return
    
    pacientes_data = pacientes_response.json()
    medicos_data = medicos_response.json()
    especialidades_data = especialidades_response.json()
    
    if not pacientes_data['results'] or not medicos_data['results'] or not especialidades_data['results']:
        print("❌ No hay datos suficientes")
        return
    
    # 4. Crear turno con CSRF
    print("📝 Creando turno con CSRF...")
    
    turno_data = {
        'paciente': pacientes_data['results'][0]['id'],
        'medico': medicos_data['results'][0]['id'],
        'especialidad': especialidades_data['results'][0]['id'],
        'fecha_hora_inicio': '2025-08-15T10:00:00Z',
        'motivo_consulta': 'Consulta de prueba con CSRF',
        'estado': 'DISPONIBLE'
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token,
    }
    
    turno_response = session.post('http://localhost:8000/api/turnos/', 
                                 json=turno_data, 
                                 headers=headers)
    
    print(f"📊 Status: {turno_response.status_code}")
    
    if turno_response.status_code in [200, 201]:
        print("✅ Turno creado exitosamente con CSRF")
        turno_data = turno_response.json()
        print(f"📋 Turno ID: {turno_data.get('id')}")
    else:
        print("❌ Error creando turno")
        print(f"📄 Respuesta: {turno_response.text}")

if __name__ == "__main__":
    test_csrf_turno_creation()

