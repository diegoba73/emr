#!/usr/bin/env python3
"""
Script para probar las optimizaciones de rendimiento
"""

import requests
import json
import time
from datetime import datetime, timedelta

def test_optimization():
    print("🧪 Probando optimizaciones de rendimiento...")
    
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
    csrf_response = session.get('http://localhost:8000/api/')
    csrf_token = session.cookies.get('csrftoken')
    
    if not csrf_token:
        print("❌ No se pudo obtener token CSRF")
        return
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token,
    }
    
    # 3. Obtener datos necesarios
    pacientes_response = session.get('http://localhost:8000/api/pacientes/')
    medicos_response = session.get('http://localhost:8000/api/medicos/')
    especialidades_response = session.get('http://localhost:8000/api/especialidades/')
    
    pacientes_data = pacientes_response.json()
    medicos_data = medicos_response.json()
    especialidades_data = especialidades_response.json()
    
    # 4. Crear múltiples turnos para probar eliminación
    print("📝 Creando turnos de prueba...")
    turnos_creados = []
    
    for i in range(3):
        fecha_futura = (datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        turno_data = {
            'paciente': pacientes_data['results'][0]['id'],
            'medico': medicos_data['results'][0]['id'],
            'especialidad': especialidades_data['results'][0]['id'],
            'fecha_hora_inicio': fecha_futura,
            'motivo_consulta': f'Turno de prueba {i+1}',
            'estado': 'DISPONIBLE'
        }
        
        create_response = session.post('http://localhost:8000/api/turnos/', 
                                     json=turno_data, 
                                     headers=headers)
        
        if create_response.status_code in [200, 201]:
            turno_creado = create_response.json()
            turnos_creados.append(turno_creado['id'])
            print(f"✅ Turno {i+1} creado: ID {turno_creado['id']}")
        else:
            print(f"❌ Error creando turno {i+1}")
    
    # 5. Probar eliminación rápida
    print("\n🗑️ Probando eliminación rápida...")
    start_time = time.time()
    
    for turno_id in turnos_creados:
        delete_response = session.delete(f'http://localhost:8000/api/turnos/{turno_id}/', 
                                       headers=headers)
        
        if delete_response.status_code in [200, 204]:
            print(f"✅ Turno {turno_id} eliminado")
        else:
            print(f"❌ Error eliminando turno {turno_id}")
    
    end_time = time.time()
    tiempo_total = end_time - start_time
    
    print(f"\n⏱️ Tiempo total de eliminación: {tiempo_total:.2f} segundos")
    print(f"📊 Promedio por eliminación: {tiempo_total/len(turnos_creados):.2f} segundos")
    
    # 6. Verificar que todos fueron eliminados
    print("\n🔍 Verificando eliminación...")
    for turno_id in turnos_creados:
        verify_response = session.get(f'http://localhost:8000/api/turnos/{turno_id}/')
        
        if verify_response.status_code == 404:
            print(f"✅ Turno {turno_id} confirmado eliminado")
        else:
            print(f"⚠️ Turno {turno_id} aún existe")
    
    print("\n🎉 Pruebas de optimización completadas")

if __name__ == "__main__":
    test_optimization()

