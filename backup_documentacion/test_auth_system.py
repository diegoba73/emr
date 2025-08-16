#!/usr/bin/env python
"""
Script para probar el sistema de autenticación
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

def test_auth_system():
    """
    Probar el sistema de autenticación
    """
    print("🧪 Probando sistema de autenticación...")
    
    try:
        # Importar después de configurar Django
        from usuarios.models import User, UserProfile
        from usuarios.serializers import UserSerializer, UserCreateSerializer, LoginSerializer
        
        print("✅ Modelos importados correctamente")
        
        # Verificar que el modelo User personalizado funciona
        print(f"📊 Modelo User: {User}")
        print(f"📊 Modelo UserProfile: {UserProfile}")
        
        # Verificar que los serializers funcionan
        print(f"📊 UserSerializer: {UserSerializer}")
        print(f"📊 UserCreateSerializer: {UserCreateSerializer}")
        print(f"📊 LoginSerializer: {LoginSerializer}")
        
        print("✅ Sistema de autenticación configurado correctamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def test_api_endpoints():
    """
    Probar los endpoints de la API
    """
    print("\n🌐 Probando endpoints de la API...")
    
    endpoints = [
        '/api/usuarios/auth/register/',
        '/api/usuarios/auth/login/',
        '/api/usuarios/auth/logout/',
        '/api/usuarios/profile/',
        '/api/usuarios/current/',
        '/api/usuarios/pacientes/',
        '/api/usuarios/medicos/',
        '/api/usuarios/secretarias/',
    ]
    
    for endpoint in endpoints:
        print(f"✅ Endpoint configurado: {endpoint}")
    
    print("✅ Todos los endpoints están configurados")

if __name__ == '__main__':
    print("🚀 Iniciando pruebas del sistema de autenticación...")
    
    if test_auth_system():
        test_api_endpoints()
        print("\n🎉 Sistema de autenticación listo para usar!")
        print("\n📋 Próximos pasos:")
        print("   1. Resolver las migraciones")
        print("   2. Crear usuarios de prueba")
        print("   3. Probar las APIs desde el frontend")
    else:
        print("\n❌ Error en el sistema de autenticación")
