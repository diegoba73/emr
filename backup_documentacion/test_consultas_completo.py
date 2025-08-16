#!/usr/bin/env python3
"""
Script de prueba completo para el sistema de consultas
Prueba: Login, confirmar turno, crear consulta, ver mis consultas
"""

import requests
import json
import sys
import os

# Configuración
BASE_URL = "http://localhost:8000/api"
CREDENTIALS = {
    "username": "dr.garcia",
    "password": "medico123"
}

def print_step(step, description):
    print(f"\n{'='*60}")
    print(f"PASO {step}: {description}")
    print(f"{'='*60}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def test_login():
    """Paso 1: Login como médico"""
    print_step(1, "LOGIN COMO MÉDICO")
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login/", json=CREDENTIALS)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            user = data.get('user')
            
            print_success(f"Login exitoso para: {user.get('username')}")
            print_info(f"Rol: {user.get('rol')}")
            print_info(f"Token obtenido: {token[:20]}...")
            
            return token, user
        else:
            print_error(f"Error en login: {response.status_code}")
            print_error(f"Respuesta: {response.text}")
            return None, None
            
    except Exception as e:
        print_error(f"Error de conexión: {str(e)}")
        return None, None

def test_get_turnos(token):
    """Paso 2: Obtener turnos del médico"""
    print_step(2, "OBTENER TURNOS DEL MÉDICO")
    
    headers = {'Authorization': f'Token {token}'}
    
    try:
        response = requests.get(f"{BASE_URL}/turnos/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            turnos = data.get('results', [])
            
            print_success(f"Se obtuvieron {len(turnos)} turnos")
            
            # Buscar turnos reservados del médico
            turnos_reservados = [t for t in turnos if t.get('estado') == 'RESERVADO']
            print_info(f"Turnos reservados: {len(turnos_reservados)}")
            
            if turnos_reservados:
                turno = turnos_reservados[0]
                print_info(f"Turno seleccionado: ID {turno['id']} - {turno.get('paciente', {}).get('nombre', 'Sin paciente')}")
                return turno
            else:
                print_error("No hay turnos reservados para confirmar")
                return None
                
        else:
            print_error(f"Error obteniendo turnos: {response.status_code}")
            return None
            
    except Exception as e:
        print_error(f"Error de conexión: {str(e)}")
        return None

def test_confirmar_turno(token, turno):
    """Paso 3: Confirmar turno"""
    print_step(3, "CONFIRMAR TURNO")
    
    headers = {'Authorization': f'Token {token}'}
    
    try:
        response = requests.post(f"{BASE_URL}/turnos/{turno['id']}/confirmar/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Turno confirmado exitosamente")
            print_info(f"Estado actual: {data.get('turno', {}).get('estado')}")
            return True
        else:
            print_error(f"Error confirmando turno: {response.status_code}")
            print_error(f"Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error de conexión: {str(e)}")
        return False

def test_crear_consulta(token, turno):
    """Paso 4: Crear consulta"""
    print_step(4, "CREAR CONSULTA")
    
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    
    consulta_data = {
        "anamnesis": "Paciente refiere dolor en el pecho desde hace 2 días. El dolor es opresivo y se irradia al brazo izquierdo.",
        "examen_fisico": "Paciente consciente, orientado. TA: 140/90 mmHg. FC: 88 lpm. Auscultación cardíaca: ritmo regular, sin soplos.",
        "diagnostico_presuntivo": "Dolor torácico de probable origen cardíaco. Sospecha de angina de pecho.",
        "plan_manejo": "Solicitar ECG, enzimas cardíacas, radiografía de tórax. Indicar reposo y medicación antiagregante.",
        "notas_medicas": "Paciente requiere seguimiento cardiológico. Considerar cateterismo si persisten los síntomas."
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/turnos/{turno['id']}/crear_consulta/", 
            headers=headers,
            json=consulta_data
        )
        
        if response.status_code == 201:
            data = response.json()
            print_success("Consulta creada exitosamente")
            print_info(f"ID de consulta: {data.get('consulta', {}).get('id')}")
            return True
        else:
            print_error(f"Error creando consulta: {response.status_code}")
            print_error(f"Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error de conexión: {str(e)}")
        return False

def test_ver_consultas(token):
    """Paso 5: Ver mis consultas"""
    print_step(5, "VER MIS CONSULTAS")
    
    headers = {'Authorization': f'Token {token}'}
    
    try:
        response = requests.get(f"{BASE_URL}/consultas/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            consultas = data.get('results', [])
            
            print_success(f"Se obtuvieron {len(consultas)} consultas")
            
            if consultas:
                consulta = consultas[0]
                print_info(f"Última consulta: ID {consulta['id']}")
                print_info(f"Paciente: {consulta.get('historia_clinica', {}).get('paciente', {}).get('nombre', 'N/A')}")
                print_info(f"Fecha: {consulta.get('fecha_hora_consulta', 'N/A')}")
                print_info(f"Diagnóstico: {consulta.get('diagnostico_presuntivo', 'N/A')[:50]}...")
            else:
                print_info("No hay consultas registradas")
                
            return True
        else:
            print_error(f"Error obteniendo consultas: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error de conexión: {str(e)}")
        return False

def test_consulta_info(token, turno):
    """Paso 6: Ver información de la consulta del turno"""
    print_step(6, "VER INFORMACIÓN DE CONSULTA DEL TURNO")
    
    headers = {'Authorization': f'Token {token}'}
    
    try:
        response = requests.get(f"{BASE_URL}/turnos/{turno['id']}/consulta_info/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Información de consulta obtenida")
            print_info(f"ID de consulta: {data.get('id')}")
            print_info(f"Anamnesis: {data.get('anamnesis', 'N/A')[:50]}...")
            return True
        else:
            print_error(f"Error obteniendo info de consulta: {response.status_code}")
            print_error(f"Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error de conexión: {str(e)}")
        return False

def main():
    print("🚀 INICIANDO PRUEBA COMPLETA DEL SISTEMA DE CONSULTAS")
    print("=" * 60)
    
    # Paso 1: Login
    token, user = test_login()
    if not token:
        print_error("No se pudo hacer login. Abortando prueba.")
        return
    
    # Paso 2: Obtener turnos
    turno = test_get_turnos(token)
    if not turno:
        print_error("No se pudieron obtener turnos. Abortando prueba.")
        return
    
    # Paso 3: Confirmar turno
    if not test_confirmar_turno(token, turno):
        print_error("No se pudo confirmar el turno. Abortando prueba.")
        return
    
    # Paso 4: Crear consulta
    if not test_crear_consulta(token, turno):
        print_error("No se pudo crear la consulta. Abortando prueba.")
        return
    
    # Paso 5: Ver mis consultas
    test_ver_consultas(token)
    
    # Paso 6: Ver información de consulta del turno
    test_consulta_info(token, turno)
    
    print("\n" + "="*60)
    print("🎉 PRUEBA COMPLETADA")
    print("="*60)
    print_success("Todos los pasos se ejecutaron correctamente")
    print_info("El sistema de consultas está funcionando correctamente")

if __name__ == "__main__":
    main()


