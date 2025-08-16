#!/usr/bin/env python3
"""
Script completo para probar todas las operaciones de turnos
"""

import requests
import json
from datetime import datetime, timedelta

def test_turnos_complete():
    print("🧪 Probando operaciones completas de turnos...")
    
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
    print("📊 Obteniendo datos...")
    
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
    
    print(f"✅ Datos obtenidos: {len(pacientes_data['results'])} pacientes, {len(medicos_data['results'])} médicos, {len(especialidades_data['results'])} especialidades")
    
    # 4. Crear turno
    print("📝 Creando turno...")
    
    # Usar una fecha futura
    fecha_futura = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    turno_data = {
        'paciente': pacientes_data['results'][0]['id'],
        'medico': medicos_data['results'][0]['id'],
        'especialidad': especialidades_data['results'][0]['id'],
        'fecha_hora_inicio': fecha_futura,
        'motivo_consulta': 'Prueba completa de operaciones',
        'estado': 'DISPONIBLE'
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token,
    }
    
    create_response = session.post('http://localhost:8000/api/turnos/', 
                                 json=turno_data, 
                                 headers=headers)
    
    if create_response.status_code not in [200, 201]:
        print(f"❌ Error creando turno: {create_response.status_code}")
        print(f"📄 Respuesta: {create_response.text}")
        return
    
    turno_creado = create_response.json()
    turno_id = turno_creado['id']
    print(f"✅ Turno creado exitosamente! ID: {turno_id}")
    
    # 5. Obtener turno específico
    print(f"📖 Obteniendo turno {turno_id}...")
    get_response = session.get(f'http://localhost:8000/api/turnos/{turno_id}/')
    
    if get_response.status_code == 200:
        print("✅ Turno obtenido correctamente")
    else:
        print(f"❌ Error obteniendo turno: {get_response.status_code}")
    
    # 6. Actualizar turno
    print(f"✏️ Actualizando turno {turno_id}...")
    
    update_data = {
        'motivo_consulta': 'Motivo actualizado',
        'estado': 'CONFIRMADO'
    }
    
    update_response = session.put(f'http://localhost:8000/api/turnos/{turno_id}/', 
                                json=update_data, 
                                headers=headers)
    
    if update_response.status_code == 200:
        print("✅ Turno actualizado correctamente")
    else:
        print(f"❌ Error actualizando turno: {update_response.status_code}")
    
    # 7. Eliminar turno
    print(f"🗑️ Eliminando turno {turno_id}...")
    
    delete_response = session.delete(f'http://localhost:8000/api/turnos/{turno_id}/', 
                                   headers=headers)
    
    if delete_response.status_code in [200, 204]:
        print("✅ Turno eliminado correctamente")
        
        # 8. Verificar eliminación
        verify_response = session.get(f'http://localhost:8000/api/turnos/{turno_id}/')
        
        if verify_response.status_code == 404:
            print("✅ Confirmado: Turno eliminado correctamente")
        else:
            print("⚠️ El turno aún existe")
    else:
        print(f"❌ Error eliminando turno: {delete_response.status_code}")
    
    print("\n🎉 Pruebas completas finalizadas")

if __name__ == "__main__":
    test_turnos_complete()

