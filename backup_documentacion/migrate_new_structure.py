#!/usr/bin/env python
"""
Script para migrar a la nueva estructura unificada
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection

def run_migrations():
    """Ejecutar migraciones"""
    print("🔄 Ejecutando migraciones...")
    
    try:
        # Crear migraciones
        execute_from_command_line(['manage.py', 'makemigrations', 'usuarios'])
        execute_from_command_line(['manage.py', 'makemigrations', 'pacientes'])
        execute_from_command_line(['manage.py', 'makemigrations', 'medicos'])
        
        # Aplicar migraciones
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ Migraciones completadas exitosamente!")
        
    except Exception as e:
        print(f"❌ Error en las migraciones: {e}")
        return False
    
    return True

def setup_groups():
    """Configurar grupos del sistema"""
    print("🔧 Configurando grupos del sistema...")
    
    from django.contrib.auth.models import Group
    
    grupos = ['Secretarias', 'Médicos', 'Pacientes', 'Laboratorio']
    
    for nombre_grupo in grupos:
        grupo, created = Group.objects.get_or_create(name=nombre_grupo)
        if created:
            print(f"✅ Grupo '{nombre_grupo}' creado")
        else:
            print(f"ℹ️  Grupo '{nombre_grupo}' ya existe")
    
    print("🎉 Grupos configurados!")

def create_superuser():
    """Crear superusuario si no existe"""
    print("👑 Verificando superusuario...")
    
    from usuarios.models import User
    
    if not User.objects.filter(is_superuser=True).exists():
        print("Creando superusuario...")
        User.objects.create_superuser(
            username='admin',
            email='admin@emr.com',
            password='admin123',
            first_name='Administrador',
            last_name='Sistema',
            rol='admin'
        )
        print("✅ Superusuario creado: admin / admin123")
    else:
        print("ℹ️  Superusuario ya existe")

if __name__ == '__main__':
    print("🚀 Iniciando migración a estructura unificada...")
    
    # Ejecutar migraciones
    if run_migrations():
        # Configurar grupos
        setup_groups()
        
        # Crear superusuario
        create_superuser()
        
        print("\n🎉 Migración completada exitosamente!")
        print("\n📋 Próximos pasos:")
        print("   1. Ir al Django Admin: http://127.0.0.1:8000/admin/")
        print("   2. Crear usuarios de prueba")
        print("   3. Probar las APIs de registro")
        print("   4. Implementar frontend de registro")
    else:
        print("\n❌ Error en la migración")
        sys.exit(1)


