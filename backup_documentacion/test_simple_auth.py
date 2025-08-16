#!/usr/bin/env python3
"""
Script simple para probar la autenticación
"""

import requests
import json

def test_auth():
    print("🧪 Probando autenticación simple...")
    
    session = requests.Session()
    
    # Login
    print("🔐 Haciendo login...")
    login_response = session.post('http://localhost:8000/api/auth/login/', json={
        'username': 'secretaria1',
        'password': 'changeme123'
    })
    
    print(f"Login status: {login_response.status_code}")
    if login_response.status_code == 200:
        print("✅ Login exitoso")
    else:
        print("❌ Login falló")
        return
    
    # Test endpoints
    endpoints = [
        'http://localhost:8000/api/auth/current-user/',
        'http://localhost:8000/api/pacientes/',
        'http://localhost:8000/api/turnos/',
        'http://localhost:8000/api/medicos/',
        'http://localhost:8000/api/especialidades/'
    ]
    
    for url in endpoints:
        response = session.get(url)
        print(f"{url}: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                print(f"  ✅ {len(data['results'])} registros")
            else:
                print(f"  ✅ OK")
        else:
            print(f"  ❌ Error")

if __name__ == "__main__":
    test_auth()
