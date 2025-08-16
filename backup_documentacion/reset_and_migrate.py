#!/usr/bin/env python
"""
Script para resetear la base de datos y aplicar las nuevas migraciones
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection

def reset_database():
    """Resetear la base de datos"""
    print("🔄 Reseteando base de datos...")
    
    try:
        # Eliminar todas las tablas
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            # Obtener todas las tablas
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")
                print(f"   🗑️  Eliminada tabla: {table_name}")
            
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        
        print("✅ Base de datos reseteada exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error reseteando base de datos: {e}")
        return False

def run_migrations():
    """Ejecutar migraciones"""
    print("🔄 Ejecutando migraciones...")
    
    try:
        # Crear migraciones con --empty para evitar problemas
        execute_from_command_line(['manage.py', 'makemigrations', 'usuarios', '--empty'])
        execute_from_command_line(['manage.py', 'makemigrations', 'pacientes', '--empty'])
        execute_from_command_line(['manage.py', 'makemigrations', 'medicos', '--empty'])
        execute_from_command_line(['manage.py', 'makemigrations', 'historias_clinicas', '--empty'])
        execute_from_command_line(['manage.py', 'makemigrations', 'turnos', '--empty'])
        execute_from_command_line(['manage.py', 'makemigrations', 'laboratorio', '--empty'])
        execute_from_command_line(['manage.py', 'makemigrations', 'catalogos', '--empty'])
        
        # Aplicar migraciones
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ Migraciones completadas exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error en las migraciones: {e}")
        return False

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
    print("🚀 Iniciando reset y migración a estructura unificada...")
    
    # Resetear base de datos
    if reset_database():
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
            print("\n❌ Error en las migraciones")
            sys.exit(1)
    else:
        print("\n❌ Error reseteando base de datos")
        sys.exit(1)
