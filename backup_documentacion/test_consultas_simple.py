#!/usr/bin/env python3
"""
Script simple para verificar las APIs de consultas
"""

import requests
import json

# Configuración
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

def test_apis():
    print("🔍 Verificando APIs de consultas...")
    
    # 1. Verificar que el servidor esté funcionando
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Servidor Django funcionando (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        return
    
    # 2. Verificar que las URLs de turnos estén disponibles
    try:
        response = requests.get(f"{API_URL}/turnos/")
        if response.status_code == 401:  # Esperado sin autenticación
            print("✅ API de turnos disponible (requiere autenticación)")
        else:
            print(f"⚠️ API de turnos responde con status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en API de turnos: {e}")
    
    # 3. Verificar que las acciones específicas estén registradas
    # Esto se puede verificar revisando las URLs disponibles
    print("\n📋 URLs disponibles para turnos:")
    print("   - GET  /api/turnos/ (lista de turnos)")
    print("   - POST /api/turnos/{id}/confirmar/ (confirmar turno)")
    print("   - POST /api/turnos/{id}/crear_consulta/ (crear consulta)")
    print("   - GET  /api/turnos/{id}/consulta_info/ (info de consulta)")
    
    # 4. Verificar que el modelo de consulta esté disponible
    try:
        response = requests.get(f"{API_URL}/consultas/")
        if response.status_code == 401:  # Esperado sin autenticación
            print("✅ API de consultas disponible (requiere autenticación)")
        else:
            print(f"⚠️ API de consultas responde con status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en API de consultas: {e}")
    
    print("\n🎯 Para probar completamente el sistema:")
    print("1. Inicia sesión como médico en el frontend")
    print("2. Ve a la página de 'Mis Turnos'")
    print("3. Busca un turno en estado 'RESERVADO'")
    print("4. Haz clic en '✅ Confirmar'")
    print("5. Una vez confirmado, haz clic en '📋 Crear Consulta'")
    print("6. Completa el formulario médico y guarda")

if __name__ == "__main__":
    test_apis()


