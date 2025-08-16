#!/usr/bin/env python3
"""
Script de debug completo para el sistema de turnos
Prueba todos los endpoints de la API y verifica la carga de datos
"""

import requests
import json
import sys
from datetime import datetime

# Configuración
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api"

# Credenciales de prueba
CREDENTIALS = {
    'secretaria1': 'changeme123',
    'paciente1': 'changeme123',
    'medico1': 'changeme123',
    'admin': 'admin123'
}

class TurnosDebugger:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        })
        self.current_user = None
        self.test_results = {}

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def test_connectivity(self):
        """Prueba la conectividad básica del servidor"""
        self.log("🔍 Probando conectividad del servidor...")
        try:
            response = self.session.get(f"{API_BASE}/")
            if response.status_code == 200:
                self.log("✅ Servidor Django respondiendo correctamente")
                return True
            else:
                self.log(f"❌ Servidor respondió con status {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error de conectividad: {e}", "ERROR")
            return False

    def test_api_base(self):
        """Prueba el endpoint base de la API"""
        self.log("🔍 Probando endpoint base de la API...")
        try:
            response = self.session.get(f"{API_BASE}/")
            self.log(f"📊 API Base Status: {response.status_code}")
            if response.status_code in [200, 403]:  # 403 es esperado para usuario no autenticado
                self.log("✅ Endpoint base de API accesible")
                return True
            else:
                self.log(f"❌ API Base respondió con status inesperado: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error en API Base: {e}", "ERROR")
            return False

    def login_user(self, username, password):
        """Inicia sesión con un usuario"""
        self.log(f"🔐 Intentando login con usuario: {username}")
        try:
            response = self.session.post(f"{API_BASE}/auth/login/", json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.current_user = data.get('user')
                self.log(f"✅ Login exitoso para {username}")
                self.log(f"👤 Usuario: {self.current_user.get('username')} - Rol: {self.current_user.get('rol')}")
                return True
            else:
                self.log(f"❌ Login falló para {username}: {response.status_code}", "ERROR")
                self.log(f"📄 Respuesta: {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Error en login: {e}", "ERROR")
            return False

    def test_current_user(self):
        """Prueba el endpoint de usuario actual"""
        self.log("🔍 Probando endpoint de usuario actual...")
        try:
            response = self.session.get(f"{API_BASE}/auth/current-user/")
            if response.status_code == 200:
                user_data = response.json()
                self.log(f"✅ Usuario actual obtenido: {user_data.get('username')}")
                return user_data
            else:
                self.log(f"❌ Error obteniendo usuario actual: {response.status_code}", "ERROR")
                return None
        except Exception as e:
            self.log(f"❌ Error en current-user: {e}", "ERROR")
            return None

    def test_pacientes_endpoint(self):
        """Prueba el endpoint de pacientes"""
        self.log("🔍 Probando endpoint de pacientes...")
        try:
            response = self.session.get(f"{API_BASE}/pacientes/")
            self.log(f"📊 Pacientes Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                self.log(f"✅ Pacientes cargados: {count} registros")
                if count > 0:
                    self.log(f"📋 Primer paciente: {data['results'][0].get('nombre')} {data['results'][0].get('apellido')}")
                return data
            else:
                self.log(f"❌ Error en pacientes: {response.status_code}", "ERROR")
                self.log(f"📄 Respuesta: {response.text}")
                return None
        except Exception as e:
            self.log(f"❌ Error en pacientes endpoint: {e}", "ERROR")
            return None

    def test_medicos_endpoint(self):
        """Prueba el endpoint de médicos"""
        self.log("🔍 Probando endpoint de médicos...")
        try:
            response = self.session.get(f"{API_BASE}/medicos/")
            self.log(f"📊 Médicos Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                self.log(f"✅ Médicos cargados: {count} registros")
                if count > 0:
                    self.log(f"📋 Primer médico: Dr. {data['results'][0].get('apellido')}")
                return data
            else:
                self.log(f"❌ Error en médicos: {response.status_code}", "ERROR")
                self.log(f"📄 Respuesta: {response.text}")
                return None
        except Exception as e:
            self.log(f"❌ Error en médicos endpoint: {e}", "ERROR")
            return None

    def test_especialidades_endpoint(self):
        """Prueba el endpoint de especialidades"""
        self.log("🔍 Probando endpoint de especialidades...")
        try:
            response = self.session.get(f"{API_BASE}/especialidades/")
            self.log(f"📊 Especialidades Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                self.log(f"✅ Especialidades cargadas: {count} registros")
                if count > 0:
                    self.log(f"📋 Primera especialidad: {data['results'][0].get('nombre')}")
                return data
            else:
                self.log(f"❌ Error en especialidades: {response.status_code}", "ERROR")
                self.log(f"📄 Respuesta: {response.text}")
                return None
        except Exception as e:
            self.log(f"❌ Error en especialidades endpoint: {e}", "ERROR")
            return None

    def test_turnos_endpoint(self):
        """Prueba el endpoint de turnos"""
        self.log("🔍 Probando endpoint de turnos...")
        try:
            response = self.session.get(f"{API_BASE}/turnos/")
            self.log(f"📊 Turnos Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                self.log(f"✅ Turnos cargados: {count} registros")
                if count > 0:
                    turno = data['results'][0]
                    self.log(f"📋 Primer turno: {turno.get('fecha_hora_inicio')} - {turno.get('estado')}")
                return data
            else:
                self.log(f"❌ Error en turnos: {response.status_code}", "ERROR")
                self.log(f"📄 Respuesta: {response.text}")
                return None
        except Exception as e:
            self.log(f"❌ Error en turnos endpoint: {e}", "ERROR")
            return None

    def test_create_turno(self):
        """Prueba crear un turno"""
        self.log("🔍 Probando creación de turno...")
        try:
            # Obtener datos necesarios
            pacientes_response = self.session.get(f"{API_BASE}/pacientes/")
            medicos_response = self.session.get(f"{API_BASE}/medicos/")
            especialidades_response = self.session.get(f"{API_BASE}/especialidades/")
            
            if not all([pacientes_response.ok, medicos_response.ok, especialidades_response.ok]):
                self.log("❌ No se pueden obtener datos para crear turno", "ERROR")
                return False
            
            pacientes_data = pacientes_response.json()
            medicos_data = medicos_response.json()
            especialidades_data = especialidades_response.json()
            
            if not pacientes_data.get('results') or not medicos_data.get('results') or not especialidades_data.get('results'):
                self.log("❌ No hay datos suficientes para crear turno", "ERROR")
                return False
            
            # Crear turno de prueba
            turno_data = {
                'paciente': pacientes_data['results'][0]['id'],
                'medico': medicos_data['results'][0]['id'],
                'especialidad': especialidades_data['results'][0]['id'],
                'fecha_hora_inicio': '2025-08-15T10:00:00Z',
                'motivo_consulta': 'Consulta de prueba desde debug script',
                'estado': 'DISPONIBLE'
            }
            
            response = self.session.post(f"{API_BASE}/turnos/", json=turno_data)
            self.log(f"📊 Crear Turno Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                self.log("✅ Turno creado exitosamente")
                return True
            else:
                self.log(f"❌ Error creando turno: {response.status_code}", "ERROR")
                self.log(f"📄 Respuesta: {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Error en creación de turno: {e}", "ERROR")
            return False

    def run_complete_test(self):
        """Ejecuta todas las pruebas"""
        self.log("🚀 Iniciando pruebas completas del sistema de turnos...")
        self.log("=" * 60)
        
        # Test 1: Conectividad
        if not self.test_connectivity():
            self.log("❌ FALLO: No se puede conectar al servidor", "ERROR")
            return False
        
        # Test 2: API Base
        if not self.test_api_base():
            self.log("❌ FALLO: API base no accesible", "ERROR")
            return False
        
        # Test 3: Login con secretaria
        if not self.login_user('secretaria1', 'changeme123'):
            self.log("❌ FALLO: No se pudo hacer login", "ERROR")
            return False
        
        # Test 4: Usuario actual
        current_user = self.test_current_user()
        if not current_user:
            self.log("❌ FALLO: No se pudo obtener usuario actual", "ERROR")
            return False
        
        # Test 5: Endpoints de datos
        self.log("=" * 60)
        self.log("📊 Probando endpoints de datos...")
        
        pacientes_data = self.test_pacientes_endpoint()
        medicos_data = self.test_medicos_endpoint()
        especialidades_data = self.test_especialidades_endpoint()
        turnos_data = self.test_turnos_endpoint()
        
        # Test 6: Crear turno
        self.log("=" * 60)
        self.log("📝 Probando creación de turno...")
        create_success = self.test_create_turno()
        
        # Resumen final
        self.log("=" * 60)
        self.log("📋 RESUMEN DE PRUEBAS:")
        self.log(f"✅ Conectividad: OK")
        self.log(f"✅ API Base: OK")
        self.log(f"✅ Login: OK")
        self.log(f"✅ Usuario Actual: OK")
        self.log(f"✅ Pacientes: {'OK' if pacientes_data else 'FALLO'}")
        self.log(f"✅ Médicos: {'OK' if medicos_data else 'FALLO'}")
        self.log(f"✅ Especialidades: {'OK' if especialidades_data else 'FALLO'}")
        self.log(f"✅ Turnos: {'OK' if turnos_data else 'FALLO'}")
        self.log(f"✅ Crear Turno: {'OK' if create_success else 'FALLO'}")
        
        # Guardar resultados
        self.test_results = {
            'connectivity': True,
            'api_base': True,
            'login': True,
            'current_user': current_user is not None,
            'pacientes': pacientes_data is not None,
            'medicos': medicos_data is not None,
            'especialidades': especialidades_data is not None,
            'turnos': turnos_data is not None,
            'create_turno': create_success,
            'data_counts': {
                'pacientes': len(pacientes_data.get('results', [])) if pacientes_data else 0,
                'medicos': len(medicos_data.get('results', [])) if medicos_data else 0,
                'especialidades': len(especialidades_data.get('results', [])) if especialidades_data else 0,
                'turnos': len(turnos_data.get('results', [])) if turnos_data else 0
            }
        }
        
        return True

def main():
    debugger = TurnosDebugger()
    success = debugger.run_complete_test()
    
    if success:
        print("\n🎉 Todas las pruebas completadas. Revisa los logs para detalles.")
        print(f"📊 Resultados guardados en debugger.test_results")
    else:
        print("\n❌ Algunas pruebas fallaron. Revisa los logs para detalles.")
        sys.exit(1)

if __name__ == "__main__":
    main()
