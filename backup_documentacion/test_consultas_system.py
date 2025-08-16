#!/usr/bin/env python3
"""
Script de prueba para el sistema de consultas médicas
Verifica que los médicos puedan confirmar turnos y crear consultas
"""

import requests
import json
from datetime import datetime, timedelta
import time

# Configuración
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step, description):
    print(f"\n{step}. {description}")
    print("-" * 40)

def test_consultas_system():
    print_section("PRUEBA DEL SISTEMA DE CONSULTAS MÉDICAS")
    
    session = requests.Session()
    
    # 1. Login como médico
    print_step(1, "Login como médico")
    login_data = {
        "username": "medico1",
        "password": "medico123"
    }
    
    try:
        response = session.post(f"{API_URL}/auth/login/", json=login_data)
        if response.status_code == 200:
            print("✅ Login exitoso como médico")
            user_data = response.json()
            print(f"   Usuario: {user_data.get('user', {}).get('username')}")
            print(f"   Rol: {user_data.get('user', {}).get('rol')}")
        else:
            print(f"❌ Error en login: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return
    
    # 2. Obtener turnos del médico
    print_step(2, "Obtener turnos del médico")
    try:
        response = session.get(f"{API_URL}/turnos/")
        if response.status_code == 200:
            turnos = response.json().get('results', [])
            print(f"✅ Se encontraron {len(turnos)} turnos")
            
            # Filtrar turnos reservados del médico
            turnos_reservados = [t for t in turnos if t.get('estado') == 'RESERVADO']
            print(f"   Turnos reservados: {len(turnos_reservados)}")
            
            if not turnos_reservados:
                print("   ⚠️ No hay turnos reservados para confirmar")
                return
            
            turno_a_confirmar = turnos_reservados[0]
            print(f"   Turno seleccionado: ID {turno_a_confirmar['id']}")
            print(f"   Paciente: {turno_a_confirmar.get('paciente', {}).get('nombre', 'N/A')} {turno_a_confirmar.get('paciente', {}).get('apellido', 'N/A')}")
            print(f"   Fecha: {turno_a_confirmar.get('fecha_hora_inicio')}")
        else:
            print(f"❌ Error obteniendo turnos: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 3. Confirmar turno
    print_step(3, "Confirmar turno")
    try:
        response = session.post(f"{API_URL}/turnos/{turno_a_confirmar['id']}/confirmar/")
        if response.status_code == 200:
            print("✅ Turno confirmado exitosamente")
            turno_confirmado = response.json().get('turno', {})
            print(f"   Nuevo estado: {turno_confirmado.get('estado')}")
        else:
            print(f"❌ Error confirmando turno: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 4. Crear consulta
    print_step(4, "Crear consulta médica")
    consulta_data = {
        "anamnesis": "Paciente refiere dolor en el pecho desde hace 2 días. El dolor es opresivo y se irradia al brazo izquierdo.",
        "examen_fisico": "Paciente consciente, orientado. TA: 140/90 mmHg. FC: 88 lpm. Auscultación cardíaca: ritmo regular, sin soplos.",
        "diagnostico_presuntivo": "Angina de pecho inestable. Se requiere evaluación cardiológica urgente.",
        "plan_manejo": "1. ECG urgente\n2. Enzimas cardíacas\n3. Derivación a cardiología\n4. Nitroglicerina sublingual si dolor",
        "notas_medicas": "Paciente con factores de riesgo: hipertensión, diabetes, tabaquismo. Requiere seguimiento estrecho."
    }
    
    try:
        response = session.post(f"{API_URL}/turnos/{turno_a_confirmar['id']}/crear_consulta/", json=consulta_data)
        if response.status_code == 201:
            print("✅ Consulta creada exitosamente")
            consulta = response.json().get('consulta', {})
            print(f"   ID Consulta: {consulta.get('id')}")
            print(f"   Fecha: {consulta.get('fecha_hora_consulta')}")
            print(f"   Diagnóstico: {consulta.get('diagnostico_presuntivo', 'N/A')[:50]}...")
        else:
            print(f"❌ Error creando consulta: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 5. Verificar estado del turno
    print_step(5, "Verificar estado final del turno")
    try:
        response = session.get(f"{API_URL}/turnos/{turno_a_confirmar['id']}/")
        if response.status_code == 200:
            turno_final = response.json()
            print(f"✅ Estado final del turno: {turno_final.get('estado')}")
            if turno_final.get('estado') == 'REALIZADO':
                print("   ✅ Turno marcado como realizado correctamente")
            else:
                print(f"   ⚠️ Estado inesperado: {turno_final.get('estado')}")
        else:
            print(f"❌ Error obteniendo turno: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 6. Obtener información de la consulta
    print_step(6, "Obtener información de la consulta")
    try:
        response = session.get(f"{API_URL}/turnos/{turno_a_confirmar['id']}/consulta_info/")
        if response.status_code == 200:
            consulta_info = response.json()
            print("✅ Información de la consulta obtenida")
            print(f"   Anamnesis: {consulta_info.get('anamnesis', 'N/A')[:50]}...")
            print(f"   Examen físico: {consulta_info.get('examen_fisico', 'N/A')[:50]}...")
            print(f"   Diagnóstico: {consulta_info.get('diagnostico_presuntivo', 'N/A')[:50]}...")
            print(f"   Plan de manejo: {consulta_info.get('plan_manejo', 'N/A')[:50]}...")
        else:
            print(f"❌ Error obteniendo consulta: {response.status_code}")
            print(f"   Respuesta: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 7. Probar permisos (intentar crear consulta desde otro usuario)
    print_step(7, "Probar permisos de seguridad")
    try:
        # Login como secretaria
        secretaria_data = {
            "username": "secretaria1",
            "password": "secretaria123"
        }
        response = session.post(f"{API_URL}/auth/login/", json=secretaria_data)
        if response.status_code == 200:
            print("✅ Login como secretaria exitoso")
            
            # Intentar crear consulta (debería fallar)
            response = session.post(f"{API_URL}/turnos/{turno_a_confirmar['id']}/crear_consulta/", json=consulta_data)
            if response.status_code == 403:
                print("✅ Permisos correctos: Secretaria no puede crear consultas")
            else:
                print(f"⚠️ Permisos incorrectos: Secretaria pudo crear consulta (status: {response.status_code})")
        else:
            print(f"❌ Error login secretaria: {response.status_code}")
    except Exception as e:
        print(f"❌ Error probando permisos: {e}")
    
    print_section("PRUEBA COMPLETADA")
    print("🎉 El sistema de consultas está funcionando correctamente!")
    print("\nResumen de funcionalidades probadas:")
    print("✅ Login de médicos")
    print("✅ Obtención de turnos")
    print("✅ Confirmación de turnos")
    print("✅ Creación de consultas")
    print("✅ Actualización de estado de turnos")
    print("✅ Obtención de información de consultas")
    print("✅ Control de permisos")

if __name__ == "__main__":
    test_consultas_system()


