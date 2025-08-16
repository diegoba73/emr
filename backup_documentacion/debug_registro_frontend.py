#!/usr/bin/env python
import requests
import json

def test_registro_frontend():
    """Probar el registro como lo haría el frontend"""
    
    print("🔍 DEBUGGEANDO REGISTRO DESDE FRONTEND")
    print("=" * 50)
    
    # URL del endpoint
    url = "http://localhost:8000/api/auth/register/patient/"
    
    # Datos que enviaría el frontend (sin password2)
    frontend_data = {
        "username": "paciente_frontend_test",
        "email": "paciente.frontend@email.com",
        "password": "Test123456",
        "first_name": "María",
        "last_name": "González",
        "telefono": "+1234567890",
        "dni": "87654321",
        "fecha_nacimiento": "1985-05-15",
        "genero": "F",
        "direccion": "Av. Principal 456",
        "ciudad": "Buenos Aires",
        "codigo_postal": "1001",
        "grupo_sanguineo": "O+",
        "alergias": "Penicilina",
        "medicamentos_actuales": "Ninguno",
        "contacto_emergencia_nombre": "Carlos González",
        "contacto_emergencia_telefono": "+1234567891",
        "contacto_emergencia_relacion": "Esposo",
        "antecedentes_personales": "Hipertensión leve",
        "antecedentes_familiares": "Diabetes en familia paterna"
    }
    
    print("📤 Enviando datos como frontend...")
    print(f"URL: {url}")
    print(f"Datos: {json.dumps(frontend_data, indent=2)}")
    
    try:
        response = requests.post(
            url, 
            json=frontend_data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        
        print(f"\n📊 Status Code: {response.status_code}")
        print(f"📄 Headers: {dict(response.headers)}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Registro exitoso desde frontend!")
        else:
            print("❌ Error en el registro desde frontend")
            
            # Intentar parsear el error
            try:
                error_data = response.json()
                print(f"🔍 Error detallado: {json.dumps(error_data, indent=2)}")
            except:
                print("🔍 Error no es JSON válido")
                
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se puede conectar al servidor")
        print("   Asegúrate de que Django esté ejecutándose en http://localhost:8000")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def test_cors():
    """Probar si hay problemas de CORS"""
    
    print("\n🌐 PROBANDO CORS")
    print("-" * 30)
    
    url = "http://localhost:8000/api/auth/register/patient/"
    
    # Simular request del frontend (puerto 3000)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': 'http://localhost:3000',
        'Referer': 'http://localhost:3000/register'
    }
    
    test_data = {
        "username": "cors_test",
        "email": "cors@test.com",
        "password": "Test123456",
        "first_name": "Test",
        "last_name": "CORS",
        "telefono": "+1234567890",
        "dni": "11111111",
        "fecha_nacimiento": "1990-01-01",
        "genero": "M",
        "direccion": "Test 123",
        "ciudad": "Test",
        "codigo_postal": "1234",
        "contacto_emergencia_nombre": "Test Contact",
        "contacto_emergencia_telefono": "+1234567891",
        "contacto_emergencia_relacion": "Test"
    }
    
    try:
        response = requests.post(url, json=test_data, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"CORS Headers: {dict(response.headers)}")
        
        if 'Access-Control-Allow-Origin' in response.headers:
            print("✅ CORS configurado correctamente")
        else:
            print("⚠️  CORS no configurado")
            
    except Exception as e:
        print(f"❌ Error en CORS: {str(e)}")

if __name__ == "__main__":
    test_registro_frontend()
    test_cors()
