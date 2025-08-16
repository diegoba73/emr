#!/usr/bin/env python3
"""
Script para probar el flujo de login del frontend
"""

import requests
import json
import time

def test_frontend_login_flow():
    print("🧪 Probando flujo de login del frontend...")
    
    session = requests.Session()
    
    # 1. Verificar estado inicial
    print("\n🔍 1. Verificando estado inicial...")
    current_user_response = session.get('http://localhost:8000/api/auth/current-user/')
    print(f"📊 Status: {current_user_response.status_code}")
    
    if current_user_response.status_code == 200:
        current_user = current_user_response.json()
        print(f"✅ Usuario actual: {current_user.get('username', 'N/A')}")
    else:
        print("❌ No hay usuario autenticado")
    
    # 2. Simular login manual
    print("\n🔐 2. Simulando login manual...")
    
    # Obtener CSRF token
    csrf_response = session.get('http://localhost:8000/api/')
    csrf_token = session.cookies.get('csrftoken')
    
    if not csrf_token:
        print("⚠️ No se pudo obtener CSRF token, continuando sin él...")
        headers = {'Content-Type': 'application/json'}
    else:
        print(f"✅ CSRF token obtenido: {csrf_token[:10]}...")
        headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token,
        }
    
    # Login manual
    login_data = {
        'username': 'secretaria1',
        'password': 'changeme123'
    }
    
    login_response = session.post('http://localhost:8000/api/auth/login/', 
                                json=login_data, 
                                headers=headers)
    
    print(f"📊 Login Status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        login_result = login_response.json()
        print("✅ Login manual exitoso!")
        print(f"👤 Usuario: {login_result.get('user', {}).get('username', 'N/A')}")
        print(f"🎭 Rol: {login_result.get('user', {}).get('rol', 'N/A')}")
    else:
        print(f"❌ Login manual falló: {login_response.text}")
        return
    
    # 3. Verificar usuario actual después del login
    print("\n🔍 3. Verificando usuario actual después del login...")
    time.sleep(1)  # Pequeña pausa
    
    current_user_response = session.get('http://localhost:8000/api/auth/current-user/')
    print(f"📊 Status: {current_user_response.status_code}")
    
    if current_user_response.status_code == 200:
        current_user = current_user_response.json()
        print("✅ Usuario actual obtenido después del login!")
        print(f"👤 Usuario: {current_user.get('username', 'N/A')}")
        print(f"🎭 Rol: {current_user.get('rol', 'N/A')}")
    else:
        print(f"❌ Error obteniendo usuario actual: {current_user_response.text}")
    
    # 4. Verificar cookies
    print("\n🍪 4. Verificando cookies...")
    print(f"📊 Número de cookies: {len(session.cookies)}")
    for cookie in session.cookies:
        print(f"🍪 {cookie.name}: {cookie.value[:20]}...")
    
    # 5. Probar acceso a dashboard
    print("\n🏠 5. Probando acceso a dashboard...")
    dashboard_response = session.get('http://localhost:8000/api/dashboard/estadisticas/')
    print(f"📊 Dashboard Status: {dashboard_response.status_code}")
    
    if dashboard_response.status_code == 200:
        print("✅ Dashboard accesible!")
    else:
        print(f"❌ Dashboard no accesible: {dashboard_response.text}")

if __name__ == "__main__":
    test_frontend_login_flow()


