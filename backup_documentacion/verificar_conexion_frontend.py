#!/usr/bin/env python
import requests
import json

def verificar_conexion_frontend():
    """Verificar que el frontend puede conectarse al backend"""
    
    print("🔍 VERIFICANDO CONEXIÓN FRONTEND-BACKEND")
    print("=" * 50)
    
    # URLs a verificar
    urls = [
        "http://localhost:8000/api/",
        "http://localhost:8000/api/auth/login/",
        "http://localhost:8000/api/auth/register/patient/",
        "http://localhost:3000"
    ]
    
    for url in urls:
        try:
            print(f"\n📡 Probando: {url}")
            response = requests.get(url, timeout=5)
            print(f"✅ Status: {response.status_code}")
            
            if "api/auth/register" in url:
                # Para el endpoint de registro, probar POST
                test_data = {
                    "username": "test_connection",
                    "email": "test.connection@email.com",
                    "password": "Test123456",
                    "first_name": "Test",
                    "last_name": "Connection",
                    "telefono": "+1234567890",
                    "dni": "88888888",
                    "fecha_nacimiento": "1990-01-01",
                    "genero": "M",
                    "direccion": "Test 123",
                    "ciudad": "Test",
                    "codigo_postal": "1234",
                    "contacto_emergencia_nombre": "Test Contact",
                    "contacto_emergencia_telefono": "+1234567891",
                    "contacto_emergencia_relacion": "Test"
                }
                
                post_response = requests.post(url, json=test_data, timeout=5)
                print(f"✅ POST Status: {post_response.status_code}")
                
                if post_response.status_code == 400:
                    # Esperado si el usuario ya existe
                    print("✅ POST funciona (error esperado por datos duplicados)")
                elif post_response.status_code == 201:
                    print("✅ POST funciona (registro exitoso)")
                else:
                    print(f"⚠️  POST inesperado: {post_response.text}")
                    
        except requests.exceptions.ConnectionError:
            print(f"❌ Error de conexión: No se puede conectar a {url}")
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout: {url} no responde")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def verificar_cors():
    """Verificar configuración CORS"""
    
    print("\n🌐 VERIFICANDO CORS")
    print("-" * 30)
    
    url = "http://localhost:8000/api/auth/register/patient/"
    
    headers = {
        'Origin': 'http://localhost:3000',
        'Referer': 'http://localhost:3000/register'
    }
    
    try:
        response = requests.options(url, headers=headers, timeout=5)
        print(f"OPTIONS Status: {response.status_code}")
        print(f"CORS Headers: {dict(response.headers)}")
        
        if 'access-control-allow-origin' in response.headers:
            print("✅ CORS configurado correctamente")
        else:
            print("⚠️  CORS no configurado")
            
    except Exception as e:
        print(f"❌ Error verificando CORS: {str(e)}")

if __name__ == "__main__":
    verificar_conexion_frontend()
    verificar_cors()
