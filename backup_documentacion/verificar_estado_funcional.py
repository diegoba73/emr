#!/usr/bin/env python3
"""
Script de verificación rápida del estado funcional del sistema EMR
Usar para confirmar que todo sigue funcionando después de cambios
"""

import requests
import json
import time
import sys

def verificar_estado_funcional():
    print("🔍 VERIFICACIÓN DEL ESTADO FUNCIONAL - Sistema EMR")
    print("=" * 60)
    
    session = requests.Session()
    errores = []
    
    # 1. Verificar conectividad de servidores
    print("\n🌐 1. Verificando conectividad de servidores...")
    
    try:
        # Backend
        backend_response = session.get('http://localhost:8000/api/')
        if backend_response.status_code == 200:
            print("✅ Backend Django: Funcionando")
        else:
            print(f"❌ Backend Django: Error {backend_response.status_code}")
            errores.append("Backend no responde correctamente")
    except Exception as e:
        print(f"❌ Backend Django: No accesible - {e}")
        errores.append("Backend no accesible")
    
    try:
        # Frontend
        frontend_response = session.get('http://localhost:3000')
        if frontend_response.status_code == 200:
            print("✅ Frontend React: Funcionando")
        else:
            print(f"❌ Frontend React: Error {frontend_response.status_code}")
            errores.append("Frontend no responde correctamente")
    except Exception as e:
        print(f"❌ Frontend React: No accesible - {e}")
        errores.append("Frontend no accesible")
    
    # 2. Verificar autenticación
    print("\n🔐 2. Verificando sistema de autenticación...")
    
    try:
        # Obtener CSRF token
        csrf_response = session.get('http://localhost:8000/api/')
        csrf_token = session.cookies.get('csrftoken')
        
        if not csrf_token:
            print("⚠️ No se pudo obtener CSRF token")
            headers = {'Content-Type': 'application/json'}
        else:
            print("✅ CSRF token obtenido")
            headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token,
            }
        
        # Login de prueba
        login_data = {
            'username': 'secretaria1',
            'password': 'changeme123'
        }
        
        login_response = session.post('http://localhost:8000/api/auth/login/', 
                                    json=login_data, 
                                    headers=headers)
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            print("✅ Login exitoso")
            print(f"   👤 Usuario: {login_result.get('user', {}).get('username', 'N/A')}")
            print(f"   🎭 Rol: {login_result.get('user', {}).get('rol', 'N/A')}")
        else:
            print(f"❌ Login falló: {login_response.status_code}")
            errores.append("Login no funciona")
            
    except Exception as e:
        print(f"❌ Error en autenticación: {e}")
        errores.append("Error en autenticación")
    
    # 3. Verificar endpoints críticos
    print("\n📡 3. Verificando endpoints críticos...")
    
    endpoints = [
        ('/api/auth/current-user/', 'Usuario actual'),
        ('/api/turnos/', 'Turnos'),
        ('/api/pacientes/', 'Pacientes'),
        ('/api/medicos/', 'Médicos'),
        ('/api/especialidades/', 'Especialidades'),
    ]
    
    for endpoint, nombre in endpoints:
        try:
            response = session.get(f'http://localhost:8000{endpoint}')
            if response.status_code == 200:
                data = response.json()
                if 'results' in data:
                    count = len(data['results'])
                    print(f"✅ {nombre}: {count} registros")
                else:
                    print(f"✅ {nombre}: OK")
            else:
                print(f"❌ {nombre}: Error {response.status_code}")
                errores.append(f"{nombre} no accesible")
        except Exception as e:
            print(f"❌ {nombre}: Error - {e}")
            errores.append(f"Error en {nombre}")
    
    # 4. Verificar cookies
    print("\n🍪 4. Verificando cookies...")
    cookie_count = len(session.cookies)
    print(f"📊 Cookies activas: {cookie_count}")
    
    for cookie in session.cookies:
        print(f"   🍪 {cookie.name}: {cookie.value[:20]}...")
    
    # 5. Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 60)
    
    if not errores:
        print("🎉 ¡ESTADO FUNCIONAL PERFECTO!")
        print("✅ Todos los sistemas funcionando correctamente")
        print("✅ Autenticación operativa")
        print("✅ API endpoints accesibles")
        print("✅ Cookies configuradas correctamente")
        print("\n🚀 El sistema EMR está listo para usar")
        return True
    else:
        print("⚠️ PROBLEMAS DETECTADOS:")
        for i, error in enumerate(errores, 1):
            print(f"   {i}. {error}")
        print(f"\n❌ Total de problemas: {len(errores)}")
        print("🔧 Revisar configuración antes de continuar")
        return False

def main():
    print("🧪 Iniciando verificación del estado funcional...")
    print("⏰ Fecha/Hora:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        resultado = verificar_estado_funcional()
        if resultado:
            print("\n✅ VERIFICACIÓN EXITOSA - Sistema en estado funcional")
            sys.exit(0)
        else:
            print("\n❌ VERIFICACIÓN FALLIDA - Revisar problemas")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Verificación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


