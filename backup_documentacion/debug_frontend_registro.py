#!/usr/bin/env python
import requests
import json

def test_frontend_exact():
    """Simular exactamente lo que hace el frontend"""
    
    print("🔍 DEBUGGEANDO EXACTAMENTE COMO FRONTEND")
    print("=" * 50)
    
    # URL del endpoint
    url = "http://localhost:8000/api/auth/register/patient/"
    
    # Datos exactos que enviaría el frontend (incluyendo password2)
    frontend_data = {
        "username": "paciente_frontend_exact",
        "email": "paciente.exact@email.com",
        "password": "Test123456",
        "password2": "Test123456",  # El frontend envía esto
        "first_name": "Ana",
        "last_name": "Martínez",
        "telefono": "+1234567890",
        "dni": "99999999",
        "fecha_nacimiento": "1988-12-25",
        "genero": "F",
        "direccion": "Calle Frente 789",
        "ciudad": "Córdoba",
        "codigo_postal": "5000",
        "grupo_sanguineo": "B+",
        "alergias": "Polen",
        "medicamentos_actuales": "Antihistamínico",
        "contacto_emergencia_nombre": "Luis Martínez",
        "contacto_emergencia_telefono": "+1234567892",
        "contacto_emergencia_relacion": "Hermano",
        "rol": "paciente"  # El frontend envía esto también
    }
    
    print("📤 Enviando datos EXACTOS como frontend...")
    print(f"URL: {url}")
    print(f"Datos completos: {json.dumps(frontend_data, indent=2)}")
    
    try:
        response = requests.post(
            url, 
            json=frontend_data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'http://localhost:3000',
                'Referer': 'http://localhost:3000/register'
            }
        )
        
        print(f"\n📊 Status Code: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        print(f"📄 Response Body: {response.text}")
        
        if response.status_code == 201:
            print("✅ Registro exitoso!")
        else:
            print("❌ Error en el registro")
            
            # Intentar parsear el error
            try:
                error_data = response.json()
                print(f"🔍 Error detallado: {json.dumps(error_data, indent=2)}")
                
                # Mostrar errores específicos si existen
                if 'errors' in error_data:
                    print("\n🚨 Errores específicos:")
                    for field, error in error_data['errors'].items():
                        print(f"  - {field}: {error}")
                        
            except:
                print("🔍 Error no es JSON válido")
                
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se puede conectar al servidor")
        print("   Asegúrate de que Django esté ejecutándose en http://localhost:8000")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()

def test_validation_errors():
    """Probar diferentes tipos de errores de validación"""
    
    print("\n🧪 PROBANDO ERRORES DE VALIDACIÓN")
    print("-" * 40)
    
    url = "http://localhost:8000/api/auth/register/patient/"
    
    # Caso 1: Username duplicado
    print("\n1️⃣ Probando username duplicado...")
    data1 = {
        "username": "paciente_test",  # Ya existe
        "email": "test1@email.com",
        "password": "Test123456",
        "first_name": "Test",
        "last_name": "User",
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
    
    response1 = requests.post(url, json=data1)
    print(f"Status: {response1.status_code}")
    print(f"Response: {response1.text}")
    
    # Caso 2: Email duplicado
    print("\n2️⃣ Probando email duplicado...")
    data2 = {
        "username": "nuevo_usuario",
        "email": "paciente.test@email.com",  # Ya existe
        "password": "Test123456",
        "first_name": "Test",
        "last_name": "User",
        "telefono": "+1234567890",
        "dni": "22222222",
        "fecha_nacimiento": "1990-01-01",
        "genero": "M",
        "direccion": "Test 123",
        "ciudad": "Test",
        "codigo_postal": "1234",
        "contacto_emergencia_nombre": "Test Contact",
        "contacto_emergencia_telefono": "+1234567891",
        "contacto_emergencia_relacion": "Test"
    }
    
    response2 = requests.post(url, json=data2)
    print(f"Status: {response2.status_code}")
    print(f"Response: {response2.text}")
    
    # Caso 3: DNI duplicado
    print("\n3️⃣ Probando DNI duplicado...")
    data3 = {
        "username": "otro_usuario",
        "email": "otro@email.com",
        "password": "Test123456",
        "first_name": "Test",
        "last_name": "User",
        "telefono": "+1234567890",
        "dni": "12345678",  # Ya existe
        "fecha_nacimiento": "1990-01-01",
        "genero": "M",
        "direccion": "Test 123",
        "ciudad": "Test",
        "codigo_postal": "1234",
        "contacto_emergencia_nombre": "Test Contact",
        "contacto_emergencia_telefono": "+1234567891",
        "contacto_emergencia_relacion": "Test"
    }
    
    response3 = requests.post(url, json=data3)
    print(f"Status: {response3.status_code}")
    print(f"Response: {response3.text}")

if __name__ == "__main__":
    test_frontend_exact()
    test_validation_errors()
