#!/usr/bin/env python3
"""
Script para probar el frontend de turnos
Simula las peticiones que hace el frontend para verificar que los datos se cargan correctamente
"""

import requests
import json
import time
from datetime import datetime

# Configuración
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api"
FRONTEND_URL = "http://localhost:3000"

class FrontendTurnosTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        })
        self.current_user = None

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def test_frontend_connectivity(self):
        """Prueba que el frontend esté respondiendo"""
        self.log("🔍 Probando conectividad del frontend...")
        try:
            response = self.session.get(FRONTEND_URL, timeout=10)
            if response.status_code == 200:
                self.log("✅ Frontend respondiendo correctamente")
                return True
            else:
                self.log(f"❌ Frontend respondió con status {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error conectando al frontend: {e}", "ERROR")
            return False

    def login_and_test_data_loading(self):
        """Simula el proceso completo de login y carga de datos del frontend"""
        self.log("🔐 Simulando proceso de login del frontend...")
        
        # 1. Login
        try:
            login_response = self.session.post(f"{API_BASE}/auth/login/", json={
                'username': 'secretaria1',
                'password': 'changeme123'
            })
            
            if login_response.status_code != 200:
                self.log(f"❌ Login falló: {login_response.status_code}", "ERROR")
                return False
            
            login_data = login_response.json()
            self.current_user = login_data.get('user')
            self.log(f"✅ Login exitoso: {self.current_user.get('username')}")
            
        except Exception as e:
            self.log(f"❌ Error en login: {e}", "ERROR")
            return False

        # 2. Obtener usuario actual (como hace el frontend)
        try:
            user_response = self.session.get(f"{API_BASE}/auth/current-user/")
            if user_response.status_code == 200:
                user_data = user_response.json()
                self.log(f"✅ Usuario actual obtenido: {user_data.get('username')}")
            else:
                self.log(f"❌ Error obteniendo usuario actual: {user_response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error obteniendo usuario actual: {e}", "ERROR")
            return False

        # 3. Cargar datos (como hace el DataContext)
        self.log("📊 Cargando datos como lo hace el frontend...")
        
        # Pacientes
        try:
            pacientes_response = self.session.get(f"{API_BASE}/pacientes/")
            if pacientes_response.status_code == 200:
                pacientes_data = pacientes_response.json()
                pacientes_count = len(pacientes_data.get('results', []))
                self.log(f"✅ Pacientes cargados: {pacientes_count} registros")
            else:
                self.log(f"❌ Error cargando pacientes: {pacientes_response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error cargando pacientes: {e}", "ERROR")
            return False

        # Médicos
        try:
            medicos_response = self.session.get(f"{API_BASE}/medicos/")
            if medicos_response.status_code == 200:
                medicos_data = medicos_response.json()
                medicos_count = len(medicos_data.get('results', []))
                self.log(f"✅ Médicos cargados: {medicos_count} registros")
            else:
                self.log(f"❌ Error cargando médicos: {medicos_response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error cargando médicos: {e}", "ERROR")
            return False

        # Especialidades
        try:
            especialidades_response = self.session.get(f"{API_BASE}/especialidades/")
            if especialidades_response.status_code == 200:
                especialidades_data = especialidades_response.json()
                especialidades_count = len(especialidades_data.get('results', []))
                self.log(f"✅ Especialidades cargadas: {especialidades_count} registros")
            else:
                self.log(f"❌ Error cargando especialidades: {especialidades_response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error cargando especialidades: {e}", "ERROR")
            return False

        # Turnos
        try:
            turnos_response = self.session.get(f"{API_BASE}/turnos/")
            if turnos_response.status_code == 200:
                turnos_data = turnos_response.json()
                turnos_count = len(turnos_data.get('results', []))
                self.log(f"✅ Turnos cargados: {turnos_count} registros")
            else:
                self.log(f"❌ Error cargando turnos: {turnos_response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error cargando turnos: {e}", "ERROR")
            return False

        return True

    def test_csrf_token(self):
        """Prueba obtener un token CSRF"""
        self.log("🔐 Probando obtención de token CSRF...")
        try:
            # Intentar obtener el token CSRF
            csrf_response = self.session.get(f"{BASE_URL}/api/")
            csrf_token = csrf_response.cookies.get('csrftoken')
            
            if csrf_token:
                self.log(f"✅ Token CSRF obtenido: {csrf_token[:10]}...")
                return csrf_token
            else:
                self.log("❌ No se pudo obtener token CSRF", "ERROR")
                return None
        except Exception as e:
            self.log(f"❌ Error obteniendo CSRF token: {e}", "ERROR")
            return None

    def run_complete_test(self):
        """Ejecuta todas las pruebas del frontend"""
        self.log("🚀 Iniciando pruebas del frontend de turnos...")
        self.log("=" * 60)
        
        # Test 1: Conectividad del frontend
        if not self.test_frontend_connectivity():
            self.log("❌ FALLO: Frontend no accesible", "ERROR")
            return False
        
        # Test 2: Login y carga de datos
        if not self.login_and_test_data_loading():
            self.log("❌ FALLO: Error en login o carga de datos", "ERROR")
            return False
        
        # Test 3: CSRF Token
        csrf_token = self.test_csrf_token()
        
        # Resumen final
        self.log("=" * 60)
        self.log("📋 RESUMEN DE PRUEBAS DEL FRONTEND:")
        self.log(f"✅ Frontend Conectividad: OK")
        self.log(f"✅ Login: OK")
        self.log(f"✅ Carga de Datos: OK")
        self.log(f"✅ CSRF Token: {'OK' if csrf_token else 'FALLO'}")
        
        self.log("=" * 60)
        self.log("🎯 DIAGNÓSTICO:")
        self.log("Si todas las pruebas pasan pero el frontend no muestra datos:")
        self.log("1. Verificar que el navegador tenga JavaScript habilitado")
        self.log("2. Verificar la consola del navegador para errores")
        self.log("3. Verificar que no haya problemas de CORS")
        self.log("4. Verificar que el DataContext esté funcionando correctamente")
        
        return True

def main():
    tester = FrontendTurnosTester()
    success = tester.run_complete_test()
    
    if success:
        print("\n🎉 Pruebas del frontend completadas exitosamente.")
        print("📊 Si el frontend no muestra datos, revisa la consola del navegador.")
    else:
        print("\n❌ Algunas pruebas del frontend fallaron.")
        print("🔍 Revisa los logs para identificar el problema.")

if __name__ == "__main__":
    main()
