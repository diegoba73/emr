#!/usr/bin/env python3
"""
Script para probar qué datos devuelve la creación de turnos
"""

import requests
import json
from datetime import datetime, timedelta

def test_turno_creation_data():
    print("🧪 Probando datos de creación de turnos...")
    
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
    
    # 4. Crear turno
    print("📝 Creando turno...")
    fecha_futura = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    turno_data = {
        'paciente_id': pacientes_data['results'][0]['id'],
        'medico_id': medicos_data['results'][0]['id'],
        'especialidad_id': especialidades_data['results'][0]['id'],
        'fecha_hora_inicio': fecha_futura,
        'motivo_consulta': 'Prueba de datos de creación',
        'estado': 'DISPONIBLE'
    }
    
    create_response = session.post('http://localhost:8000/api/turnos/', 
                                 json=turno_data, 
                                 headers=headers)
    
    if create_response.status_code in [200, 201]:
        turno_creado = create_response.json()
        print("✅ Turno creado exitosamente!")
        print("\n📊 DATOS DEVUELTOS POR LA CREACIÓN:")
        print("=" * 50)
        print(json.dumps(turno_creado, indent=2, ensure_ascii=False))
        print("=" * 50)
        
        # 5. Obtener el turno recién creado para comparar
        print(f"\n🔍 Obteniendo turno {turno_creado['id']}...")
        get_response = session.get(f'http://localhost:8000/api/turnos/{turno_creado["id"]}/')
        
        if get_response.status_code == 200:
            turno_obtenido = get_response.json()
            print("\n📊 DATOS DEVUELTOS POR GET:")
            print("=" * 50)
            print(json.dumps(turno_obtenido, indent=2, ensure_ascii=False))
            print("=" * 50)
            
            # 6. Comparar datos
            print("\n🔍 COMPARACIÓN:")
            print("=" * 50)
            
            # Verificar paciente
            if 'paciente' in turno_creado and 'paciente' in turno_obtenido:
                print(f"PACIENTE - Creación: {type(turno_creado['paciente'])} | GET: {type(turno_obtenido['paciente'])}")
                if isinstance(turno_creado['paciente'], int):
                    print(f"  Creación: ID {turno_creado['paciente']}")
                else:
                    print(f"  Creación: {turno_creado['paciente']}")
                
                if isinstance(turno_obtenido['paciente'], dict):
                    print(f"  GET: {turno_obtenido['paciente'].get('nombre', 'N/A')} {turno_obtenido['paciente'].get('apellido', 'N/A')}")
                else:
                    print(f"  GET: {turno_obtenido['paciente']}")
            
            # Verificar médico
            if 'medico' in turno_creado and 'medico' in turno_obtenido:
                print(f"MÉDICO - Creación: {type(turno_creado['medico'])} | GET: {type(turno_obtenido['medico'])}")
                if isinstance(turno_creado['medico'], int):
                    print(f"  Creación: ID {turno_creado['medico']}")
                else:
                    print(f"  Creación: {turno_creado['medico']}")
                
                if isinstance(turno_obtenido['medico'], dict):
                    print(f"  GET: {turno_obtenido['medico'].get('nombre', 'N/A')} {turno_obtenido['medico'].get('apellido', 'N/A')}")
                else:
                    print(f"  GET: {turno_obtenido['medico']}")
            
            # Verificar especialidad
            if 'especialidad' in turno_creado and 'especialidad' in turno_obtenido:
                print(f"ESPECIALIDAD - Creación: {type(turno_creado['especialidad'])} | GET: {type(turno_obtenido['especialidad'])}")
                if isinstance(turno_creado['especialidad'], int):
                    print(f"  Creación: ID {turno_creado['especialidad']}")
                else:
                    print(f"  Creación: {turno_creado['especialidad']}")
                
                if isinstance(turno_obtenido['especialidad'], dict):
                    print(f"  GET: {turno_obtenido['especialidad'].get('nombre', 'N/A')}")
                else:
                    print(f"  GET: {turno_obtenido['especialidad']}")
        
        # 7. Limpiar - eliminar el turno de prueba
        print(f"\n🗑️ Eliminando turno de prueba {turno_creado['id']}...")
        delete_response = session.delete(f'http://localhost:8000/api/turnos/{turno_creado["id"]}/', 
                                       headers=headers)
        if delete_response.status_code in [200, 204]:
            print("✅ Turno de prueba eliminado")
        
    else:
        print(f"❌ Error creando turno: {create_response.status_code}")
        print(f"📄 Respuesta: {create_response.text}")

if __name__ == "__main__":
    test_turno_creation_data()
