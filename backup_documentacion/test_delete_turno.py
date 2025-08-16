#!/usr/bin/env python3
"""
Script para probar la eliminación de turnos con CSRF
"""

import requests
import json

def test_delete_turno():
    print("🧪 Probando eliminación de turno con CSRF...")
    
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
    
    # 3. Obtener turnos existentes
    print("📊 Obteniendo turnos existentes...")
    turnos_response = session.get('http://localhost:8000/api/turnos/')
    
    if not turnos_response.ok:
        print("❌ Error obteniendo turnos")
        return
    
    turnos_data = turnos_response.json()
    turnos = turnos_data.get('results', [])
    
    if not turnos:
        print("❌ No hay turnos para eliminar")
        return
    
    print(f"✅ Encontrados {len(turnos)} turnos")
    
    # 4. Eliminar el primer turno
    turno_a_eliminar = turnos[0]
    turno_id = turno_a_eliminar['id']
    
    print(f"🗑️ Eliminando turno ID: {turno_id}")
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token,
    }
    
    delete_response = session.delete(f'http://localhost:8000/api/turnos/{turno_id}/', 
                                   headers=headers)
    
    print(f"📊 Status: {delete_response.status_code}")
    
    if delete_response.status_code in [200, 204]:
        print("✅ Turno eliminado exitosamente")
        
        # 5. Verificar que se eliminó
        print("🔍 Verificando eliminación...")
        verify_response = session.get(f'http://localhost:8000/api/turnos/{turno_id}/')
        
        if verify_response.status_code == 404:
            print("✅ Confirmado: Turno eliminado correctamente")
        else:
            print("⚠️ El turno aún existe")
    else:
        print("❌ Error eliminando turno")
        print(f"📄 Respuesta: {delete_response.text}")

if __name__ == "__main__":
    test_delete_turno()

