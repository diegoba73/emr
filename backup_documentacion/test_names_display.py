#!/usr/bin/env python3
"""
Script para verificar cómo se muestran los nombres en las respuestas de la API
"""

import requests
import json

def test_names_display():
    print("🧪 Verificando formato de nombres en la API...")
    
    session = requests.Session()
    
    # Login
    print("🔐 Haciendo login...")
    login_response = session.post('http://localhost:8000/api/auth/login/', json={
        'username': 'secretaria1',
        'password': 'changeme123'
    })
    
    if login_response.status_code != 200:
        print("❌ Login falló")
        return
    
    print("✅ Login exitoso")
    
    # Test pacientes
    print("\n👥 Verificando pacientes:")
    pacientes_response = session.get('http://localhost:8000/api/pacientes/')
    if pacientes_response.status_code == 200:
        pacientes_data = pacientes_response.json()
        for i, paciente in enumerate(pacientes_data['results'][:3]):  # Solo los primeros 3
            print(f"  {i+1}. ID: {paciente['id']}")
            print(f"     Nombre: '{paciente.get('nombre', 'N/A')}'")
            print(f"     Apellido: '{paciente.get('apellido', 'N/A')}'")
            print(f"     Formato correcto: {paciente.get('nombre', '')} {paciente.get('apellido', '')}")
            print()
    else:
        print("❌ Error obteniendo pacientes")
    
    # Test médicos
    print("👨‍⚕️ Verificando médicos:")
    medicos_response = session.get('http://localhost:8000/api/medicos/')
    if medicos_response.status_code == 200:
        medicos_data = medicos_response.json()
        for i, medico in enumerate(medicos_data['results'][:3]):  # Solo los primeros 3
            print(f"  {i+1}. ID: {medico['id']}")
            print(f"     Nombre: '{medico.get('nombre', 'N/A')}'")
            print(f"     Apellido: '{medico.get('apellido', 'N/A')}'")
            print(f"     Formato correcto: Dr. {medico.get('nombre', '')} {medico.get('apellido', '')}")
            print()
    else:
        print("❌ Error obteniendo médicos")
    
    # Test turnos
    print("📅 Verificando turnos:")
    turnos_response = session.get('http://localhost:8000/api/turnos/')
    if turnos_response.status_code == 200:
        turnos_data = turnos_response.json()
        for i, turno in enumerate(turnos_data['results']):
            print(f"  {i+1}. ID: {turno['id']}")
            if turno.get('paciente'):
                paciente = turno['paciente']
                print(f"     Paciente: {paciente.get('nombre', '')} {paciente.get('apellido', '')}")
            if turno.get('medico'):
                medico = turno['medico']
                print(f"     Médico: Dr. {medico.get('nombre', '')} {medico.get('apellido', '')}")
            print()
    else:
        print("❌ Error obteniendo turnos")

if __name__ == "__main__":
    test_names_display()
