#!/usr/bin/env python3
"""
Script para arreglar el problema de autenticación del frontend
Fuerza un login correcto y verifica que las cookies se establezcan
"""

import requests
import json
import time

# Configuración
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api"

def fix_frontend_auth():
    print("🔧 Arreglando autenticación del frontend...")
    
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    # 1. Hacer login
    print("🔐 Haciendo login...")
    login_response = session.post(f"{API_BASE}/auth/login/", json={
        'username': 'secretaria1',
        'password': 'changeme123'
    })
    
    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.status_code}")
        return False
    
    print("✅ Login exitoso")
    
    # 2. Verificar usuario actual
    print("👤 Verificando usuario actual...")
    user_response = session.get(f"{API_BASE}/auth/current-user/")
    
    if user_response.status_code != 200:
        print(f"❌ Error obteniendo usuario: {user_response.status_code}")
        return False
    
    user_data = user_response.json()
    print(f"✅ Usuario actual: {user_data.get('username')}")
    
    # 3. Probar endpoints protegidos
    print("📊 Probando endpoints protegidos...")
    
    endpoints = [
        ('pacientes', f"{API_BASE}/pacientes/"),
        ('turnos', f"{API_BASE}/turnos/"),
        ('medicos', f"{API_BASE}/medicos/"),
        ('especialidades', f"{API_BASE}/especialidades/")
    ]
    
    for name, url in endpoints:
        response = session.get(url)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('results', []))
            print(f"✅ {name}: {count} registros")
        else:
            print(f"❌ {name}: {response.status_code}")
    
    # 4. Guardar cookies para inspección
    print("🍪 Cookies obtenidas:")
    for cookie in session.cookies:
        print(f"  {cookie.name}: {cookie.value}")
    
    # 5. Crear script de prueba para el navegador
    print("📝 Creando script de prueba para el navegador...")
    
    test_script = """
// Script para probar en la consola del navegador
console.log('🧪 Probando autenticación en el navegador...');

// 1. Hacer login
fetch('http://127.0.0.1:8000/api/auth/login/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
        username: 'secretaria1',
        password: 'changeme123'
    })
})
.then(response => response.json())
.then(data => {
    console.log('✅ Login exitoso:', data);
    
    // 2. Verificar usuario actual
    return fetch('http://127.0.0.1:8000/api/auth/current-user/', {
        credentials: 'include'
    });
})
.then(response => response.json())
.then(user => {
    console.log('✅ Usuario actual:', user);
    
    // 3. Probar endpoints
    const endpoints = ['pacientes', 'turnos', 'medicos', 'especialidades'];
    
    endpoints.forEach(endpoint => {
        fetch(`http://127.0.0.1:8000/api/${endpoint}/`, {
            credentials: 'include'
        })
        .then(response => response.json())
        .then(data => {
            console.log(`✅ ${endpoint}:`, data.results?.length || 0, 'registros');
        })
        .catch(error => {
            console.error(`❌ ${endpoint}:`, error);
        });
    });
})
.catch(error => {
    console.error('❌ Error:', error);
});
"""
    
    with open('test_browser_auth.js', 'w') as f:
        f.write(test_script)
    
    print("✅ Script guardado como 'test_browser_auth.js'")
    print("📋 Instrucciones:")
    print("1. Abre http://localhost:3000 en tu navegador")
    print("2. Abre la consola del navegador (F12)")
    print("3. Copia y pega el contenido de test_browser_auth.js")
    print("4. Verifica que todos los endpoints respondan correctamente")
    
    return True

if __name__ == "__main__":
    fix_frontend_auth()
