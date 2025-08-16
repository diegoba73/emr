#!/usr/bin/env python
"""
Script para migrar usuarios existentes al nuevo modelo de usuario personalizado
"""
import os
import sys
import django
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synesis.settings')
django.setup()

from django.contrib.auth.models import User as OldUser
from django.db import connection

def migrate_users():
    """
    Migra los usuarios existentes al nuevo modelo
    """
    print("🔄 Iniciando migración de usuarios...")
    
    # Obtener todos los usuarios existentes
    old_users = OldUser.objects.all()
    print(f"📊 Encontrados {old_users.count()} usuarios existentes")
    
    # Crear tabla temporal para el nuevo modelo
    with connection.cursor() as cursor:
        # Crear tabla temporal para usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios_user (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                password VARCHAR(128) NOT NULL,
                last_login DATETIME(6) NULL,
                is_superuser BOOLEAN NOT NULL,
                username VARCHAR(150) UNIQUE NOT NULL,
                first_name VARCHAR(150) NOT NULL,
                last_name VARCHAR(150) NOT NULL,
                email VARCHAR(254) NOT NULL,
                is_staff BOOLEAN NOT NULL,
                is_active BOOLEAN NOT NULL,
                date_joined DATETIME(6) NOT NULL,
                rol VARCHAR(20) NOT NULL DEFAULT 'paciente',
                telefono VARCHAR(17) NULL,
                email_verificado BOOLEAN NOT NULL DEFAULT FALSE,
                telefono_verificado BOOLEAN NOT NULL DEFAULT FALSE,
                fecha_registro DATETIME(6) NOT NULL,
                ultima_actividad DATETIME(6) NOT NULL
            )
        """)
        
        # Crear tabla temporal para perfiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios_profile (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                fecha_nacimiento DATE NULL,
                genero VARCHAR(10) NULL,
                direccion LONGTEXT NULL,
                ciudad VARCHAR(100) NULL,
                codigo_postal VARCHAR(10) NULL,
                grupo_sanguineo VARCHAR(5) NULL,
                alergias LONGTEXT NULL,
                medicamentos_actuales LONGTEXT NULL,
                contacto_emergencia_nombre VARCHAR(100) NULL,
                contacto_emergencia_telefono VARCHAR(17) NULL,
                contacto_emergencia_relacion VARCHAR(50) NULL,
                fecha_creacion DATETIME(6) NOT NULL,
                fecha_actualizacion DATETIME(6) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES usuarios_user(id)
            )
        """)
        
        print("✅ Tablas temporales creadas")
    
    # Migrar datos de usuarios
    for old_user in old_users:
        with connection.cursor() as cursor:
            # Determinar rol basado en permisos
            rol = 'admin' if old_user.is_superuser else 'paciente'
            
            # Insertar en nueva tabla
            cursor.execute("""
                INSERT INTO usuarios_user (
                    id, password, last_login, is_superuser, username, 
                    first_name, last_name, email, is_staff, is_active, 
                    date_joined, rol, telefono, email_verificado, 
                    telefono_verificado, fecha_registro, ultima_actividad
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                old_user.id, old_user.password, old_user.last_login, 
                old_user.is_superuser, old_user.username, old_user.first_name, 
                old_user.last_name, old_user.email, old_user.is_staff, 
                old_user.is_active, old_user.date_joined, rol, None, 
                True, False, old_user.date_joined, old_user.date_joined
            ))
            
            # Crear perfil vacío
            cursor.execute("""
                INSERT INTO usuarios_profile (
                    user_id, fecha_creacion, fecha_actualizacion
                ) VALUES (%s, %s, %s)
            """, (old_user.id, old_user.date_joined, old_user.date_joined))
    
    print(f"✅ Migrados {old_users.count()} usuarios")
    print("🎉 Migración completada exitosamente!")

if __name__ == '__main__':
    migrate_users()
