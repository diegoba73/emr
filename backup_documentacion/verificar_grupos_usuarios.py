#!/usr/bin/env python3
"""
Script para verificar los grupos de todos los usuarios
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from django.contrib.auth.models import Group
from usuarios.models import User

def verificar_grupos_usuarios():
    """Verifica los grupos de todos los usuarios"""
    
    print("🔍 Verificando grupos de usuarios...")
    print("=" * 50)
    
    # Obtener todos los grupos
    grupos = Group.objects.all()
    print(f"📋 Grupos disponibles: {[g.name for g in grupos]}")
    print()
    
    # Obtener todos los usuarios
    usuarios = User.objects.all()
    
    for usuario in usuarios:
        print(f"👤 Usuario: {usuario.username}")
        print(f"   📧 Email: {usuario.email}")
        print(f"   👑 Staff: {usuario.is_staff}")
        print(f"   🏆 Superuser: {usuario.is_superuser}")
        print(f"   👥 Grupos: {[g.name for g in usuario.groups.all()]}")
        print(f"   🎭 Rol: {getattr(usuario, 'rol', 'No definido')}")
        print()
    
    print("=" * 50)
    
    # Verificar usuarios específicos
    print("🎯 Verificación de usuarios específicos:")
    print()
    
    usuarios_especificos = ['admin', 'paciente1', 'dr.garcia', 'secretaria1']
    
    for username in usuarios_especificos:
        try:
            usuario = User.objects.get(username=username)
            grupos_usuario = [g.name for g in usuario.groups.all()]
            print(f"👤 {username}:")
            print(f"   👥 Grupos: {grupos_usuario}")
            print(f"   🎭 Rol: {getattr(usuario, 'rol', 'No definido')}")
            print(f"   👑 Staff: {usuario.is_staff}")
            print(f"   🏆 Superuser: {usuario.is_superuser}")
            print()
        except User.DoesNotExist:
            print(f"❌ Usuario {username} no existe")
            print()

if __name__ == "__main__":
    verificar_grupos_usuarios()



