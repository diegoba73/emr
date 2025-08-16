#!/usr/bin/env python
import requests
import json

def test_errores_especificos():
    """Probar diferentes tipos de errores para verificar mensajes específicos"""
    
    print("🧪 PROBANDO MENSAJES DE ERROR ESPECÍFICOS")
    print("=" * 50)
    
    url = "http://localhost:8000/api/auth/register/patient/"
    
    # Caso 1: Email duplicado
    print("\n1️⃣ Probando email duplicado...")
    data1 = {
        "username": "test_error_1",
        "email": "paciente.test@email.com",  # Ya existe
        "password": "Test123456",
        "first_name": "Test",
        "last_name": "Error",
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
    print(f"Error esperado: Email ya registrado")
    print(f"Error recibido: {response1.text}")
    
    # Caso 2: Username duplicado
    print("\n2️⃣ Probando username duplicado...")
    data2 = {
        "username": "paciente_test",  # Ya existe
        "email": "test2@email.com",
        "password": "Test123456",
        "first_name": "Test",
        "last_name": "Error",
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
    print(f"Error esperado: Username ya existe")
    print(f"Error recibido: {response2.text}")
    
    # Caso 3: DNI duplicado
    print("\n3️⃣ Probando DNI duplicado...")
    data3 = {
        "username": "test_error_3",
        "email": "test3@email.com",
        "password": "Test123456",
        "first_name": "Test",
        "last_name": "Error",
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
    print(f"Error esperado: DNI ya registrado")
    print(f"Error recibido: {response3.text}")
    
    # Caso 4: Contraseña débil
    print("\n4️⃣ Probando contraseña débil...")
    data4 = {
        "username": "test_error_4",
        "email": "test4@email.com",
        "password": "123",  # Contraseña débil
        "first_name": "Test",
        "last_name": "Error",
        "telefono": "+1234567890",
        "dni": "44444444",
        "fecha_nacimiento": "1990-01-01",
        "genero": "M",
        "direccion": "Test 123",
        "ciudad": "Test",
        "codigo_postal": "1234",
        "contacto_emergencia_nombre": "Test Contact",
        "contacto_emergencia_telefono": "+1234567891",
        "contacto_emergencia_relacion": "Test"
    }
    
    response4 = requests.post(url, json=data4)
    print(f"Status: {response4.status_code}")
    print(f"Error esperado: Contraseña inválida")
    print(f"Error recibido: {response4.text}")
    
    # Caso 5: Campo requerido faltante
    print("\n5️⃣ Probando campo requerido faltante...")
    data5 = {
        "username": "test_error_5",
        "email": "test5@email.com",
        "password": "Test123456",
        "first_name": "",  # Campo vacío
        "last_name": "Error",
        "telefono": "+1234567890",
        "dni": "55555555",
        "fecha_nacimiento": "1990-01-01",
        "genero": "M",
        "direccion": "Test 123",
        "ciudad": "Test",
        "codigo_postal": "1234",
        "contacto_emergencia_nombre": "Test Contact",
        "contacto_emergencia_telefono": "+1234567891",
        "contacto_emergencia_relacion": "Test"
    }
    
    response5 = requests.post(url, json=data5)
    print(f"Status: {response5.status_code}")
    print(f"Error esperado: Campo first_name requerido")
    print(f"Error recibido: {response5.text}")

def test_registro_exitoso():
    """Probar un registro exitoso para comparar"""
    
    print("\n✅ PROBANDO REGISTRO EXITOSO")
    print("-" * 30)
    
    url = "http://localhost:8000/api/auth/register/patient/"
    
    data = {
        "username": "test_exitoso",
        "email": "test.exitoso@email.com",
        "password": "Test123456",
        "first_name": "Test",
        "last_name": "Exitoso",
        "telefono": "+1234567890",
        "dni": "99999999",
        "fecha_nacimiento": "1990-01-01",
        "genero": "M",
        "direccion": "Test 123",
        "ciudad": "Test",
        "codigo_postal": "1234",
        "contacto_emergencia_nombre": "Test Contact",
        "contacto_emergencia_telefono": "+1234567891",
        "contacto_emergencia_relacion": "Test"
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_errores_especificos()
    test_registro_exitoso()
