#!/usr/bin/env python3
"""
Script para verificar las contraseñas de los usuarios médicos
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from usuarios.models import User
from django.contrib.auth import authenticate

def verificar_passwords():
    print("🔍 Verificando contraseñas de usuarios médicos...")
    print("=" * 50)
    
    # Lista de contraseñas comunes para probar
    passwords_to_test = [
        'medico123',
        'password',
        '123456',
        'admin',
        'test',
        'medico',
        'dr.garcia',
        'dra.rodriguez',
        'dr.lopez',
        'dra.martinez',
        'dr.gonzalez'
    ]
    
    medicos = User.objects.filter(rol='medico')
    
    for medico in medicos:
        print(f"\n👨‍⚕️ Probando usuario: {medico.username}")
        print(f"   Nombre: {medico.first_name} {medico.last_name}")
        
        for password in passwords_to_test:
            user = authenticate(username=medico.username, password=password)
            if user:
                print(f"   ✅ Contraseña encontrada: '{password}'")
                break
        else:
            print(f"   ❌ No se encontró contraseña válida")
            print(f"   💡 Prueba con: {medico.username}")

if __name__ == "__main__":
    verificar_passwords()


